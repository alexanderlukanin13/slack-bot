from collections import namedtuple
from datetime import datetime
import io
import os
import re

import pytz


# All input and output datetimes use the following timezone
TIMEZONE = 'Asia/Yekaterinburg'


class NothingFound(Exception):
    """
    This exception is raised when nothing is planned for the given datetime.
    """
    pass


Event = namedtuple('Event', ['name', 'dt1', 'dt2'])


class StageInfo(object):
    """
    Info about events at one particular stage.
    """

    def __init__(self, name):
        self.name = name
        self.aliases = []
        self._items = []

    def add_alias(self, alias):
        self.aliases.append(alias)

    def add_event(self, dt1, dt2, event_name):
        self._items.append(Event(event_name, dt1, dt2))

    def get_event(self, dt):
        """
        Returns the event planned for the given datetime.

        Raises NothingFound if nothing is planned.
        :param dt: datetime
        :return type: str
        """
        for event in self._items:
            if event.dt1 <= dt <= event.dt2:
                return event
        raise NothingFound


class Stages(object):
    """
    Collection of all stages.
    """

    def __init__(self):
        self.stages = []
        self._aliases = {}

    def add_stage(self, stage):
        self.stages.append(stage)
        self.stages.sort(key=lambda x: x.name.lower())
        for alias in [stage.name.lower()] + [x.lower() for x in stage.aliases]:
            self._aliases[alias] = stage

    def get_event(self, stage_name, dt):
        try:
            stage = self._aliases[stage_name.lower()]
        except KeyError:
            raise NothingFound('No such stage: {}'.format(stage_name))
        return stage.get_event(dt)

    @staticmethod
    def from_txt(stream):
        """
        Parses txt file, returns Stages instance.

        :param stream: File-like object
        :return: Stages instance.
        :raises: ValueError if input is invalid.
        """
        stages = Stages()
        stage = None
        for line_number, line in enumerate(stream, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r'^STAGE (\d+)$', line, re.U|re.I)
            if match:
                if stage is not None:
                    stages.add_stage(stage)
                stage = StageInfo(line)
                stage.add_alias(match.group(1))
                continue
            match = re.match(r'^(\S.*\S)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$',
                             line, re.U|re.I)
            if match:
                name, dt1, dt2 = match.groups()
                try:
                    dt1 = _parse_datetime(dt1)
                    dt2 = _parse_datetime(dt2)
                except ValueError:
                    raise ValueError('Invalid datetime at line {}: {!r}'
                                     .format(line_number, line))
                if stage is None:
                    raise ValueError('Undefined stage at line {}: {!r}'
                                     .format(line_number, line))
                stage.add_event(dt1, dt2, name)
                continue
            raise ValueError('Invalid syntax at line {}: {}'
                             .format(line_number, line))
        # Add last stage
        if stage is not None:
            stages.add_stage(stage)
        return stages


def get_now():
    """Get current datetime for the current timezone."""
    return (pytz.utc.localize(datetime.utcnow())
            .astimezone(pytz.timezone(TIMEZONE))
            .replace(tzinfo=None))


def _parse_datetime(dt_str):
    """
    Parses event time and returns naive datetime in UTC.

    For time only (without date), it is assumed that date=UTC today.
    """
    time = datetime.strptime(dt_str, '%H:%M')
    return get_now().replace(hour=time.hour, minute=time.minute,
                             second=0, microsecond=0)


def _format_times(dt1, dt2):
    return '{}-{}'.format(dt1.strftime('%-I:%M'), dt2.strftime('%-I:%M%p').lower())


def setup(bot_user_name):
    """
    rtmbot.py plugin setup
    """
    global _bot_mention, _stages
    _bot_mention = '@' + bot_user_name
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stages.txt')
    with io.open(file_path) as file:
        _stages = Stages.from_txt(file)


# Global variable for bot mentions
_bot_mention = None
# Global variable for stages (read from file)
_stages = None

# rtmbot.py uses global variable for output
outputs = []


def _is_direct_message(data):
    return data['channel'].startswith("D")


def _get_normalized_text(data):
    text = data['text'].replace(_bot_mention, '')
    text = re.sub('\s+', ' ', text)
    return text.strip()


def process_message(data):
    """
    Process Slack message (any channel bot is subscribed to, including direct messages)
    """
    if _is_direct_message(data) or data['text'].strip().startswith('!'):
        _process(data)


def process_mention(data):
    """
    Process Slack message which mentions the bot.
    """
    text = _get_normalized_text(data)
    if not text:
        _print_help(data)
        return
    if _process(data):
        return
    else:
        _print_help(data)


def _process_now(text, match):
    now = get_now()
    stream = io.StringIO()
    found = False
    for stage in _stages.stages:
        stream.write(u'{}\n'.format(stage.name))
        try:
            event = stage.get_event(now)
            stream.write(u'{} {}\n'
                         .format(event.name, _format_times(event.dt1, event.dt2)))
            found = True
        except NothingFound:
            stream.write(u'n/a\n')
    if not found:
        return _NO_ONE_IS_PLAYING
    return stream.getvalue()


def _process_times(text, match):
    return 'time1\ntime2'


_NO_ONE_IS_PLAYING = '''
Sorry, but no one is playing right now.
'''.strip()


_USAGE = '''You can use one of the following commands:
`now` - who is playing right now
`times Stage 1` - schedule for particular stage (1, 2, 3...)
'''.strip()


def _print_help(data):
    outputs.append([data['channel'], _USAGE])


# Bot commands
_REGEXES = {
    r'^!?now$': _process_now,
    r'^!?times$': _process_times,
}
_REGEXES = [(re.compile(x, re.U|re.I), y) for x, y in _REGEXES.items()]


def _process(data):
    """
    Main function for message processing.
    """
    text = _get_normalized_text(data)
    for regex, function in _REGEXES:
        match = regex.match(text)
        if match is not None:
            outputs.append([data['channel'], function(text, match)])
            return True
    return False
