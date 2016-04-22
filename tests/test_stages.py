from datetime import datetime
from io import StringIO
import os
import sys

import pytz

import pytest

PROJECT_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.append(os.path.join(PROJECT_PATH, 'plugins'))

import stages
from stages import Stages, EventNotFound, _parse_datetime, _format_times


def test_parse_datetime_today(mocker):
    datetime_mock = mocker.patch('stages.datetime')
    datetime_mock.utcnow = lambda: datetime(2016, 4, 8, 4, 30, 55)
    datetime_mock.strptime = datetime.strptime
    mocker.patch('stages.TIMEZONE', 'US/Pacific')
    assert _parse_datetime('11:40') == datetime(2016, 4, 7, 11, 40)
    mocker.patch('stages.TIMEZONE', 'Asia/Jerusalem')
    assert _parse_datetime('11:40') == datetime(2016, 4, 8, 11, 40)


@pytest.fixture
def datetime_mock(mocker):
    datetime_mock = mocker.patch('stages.datetime')
    datetime_mock.utcnow = lambda: datetime(2016, 4, 8, 4, 30, 55)
    datetime_mock.strptime = datetime.strptime
    mocker.patch('stages.TIMEZONE', 'Asia/Jerusalem')


def test_from_txt(datetime_mock):
    stages = Stages.from_txt(StringIO(
        u'Stage 1\n'
        u'Some Event 9:30-11:30\n'
        u'Another Event 11:30 - 13:00\n'
        u'Stage Two\n'
        u'Event at Stage 2 9:30-11:00\n'
    ))
    assert len(set(stages.stages)) == 2
    assert sorted(stages._aliases.keys()) == ['1', 'stage 1', 'stage two']
    # Check Stage 1
    with pytest.raises(EventNotFound):
        stages.get_event('Stage 1', datetime(2016, 4, 8, 9, 29))
    assert stages.get_event('Stage 1', datetime(2016, 4, 8, 9, 30)).name == 'Some Event'
    assert stages.get_event('Stage 1', datetime(2016, 4, 8, 11, 0)).name == 'Some Event'
    assert stages.get_event('Stage 1', datetime(2016, 4, 8, 11, 29)).name == 'Some Event'
    assert stages.get_event('Stage 1', datetime(2016, 4, 8, 11, 31)).name == 'Another Event'
    assert stages.get_event('Stage 1', datetime(2016, 4, 8, 13, 00)).name == 'Another Event'
    with pytest.raises(EventNotFound):
        stages.get_event('Stage 1', datetime(2016, 4, 8, 13, 31))
    # Stage 1, wrong date
    with pytest.raises(EventNotFound):
        stages.get_event('Stage 1', datetime(2016, 4, 9, 12, 0))
    # Check Stage 2
    with pytest.raises(EventNotFound):
        stages.get_event('Stage Two', datetime(2016, 4, 8, 9, 29))
    assert stages.get_event('Stage Two', datetime(2016, 4, 8, 9, 30)).name == 'Event at Stage 2'
    assert stages.get_event('Stage Two', datetime(2016, 4, 8, 10, 30)).name == 'Event at Stage 2'
    assert stages.get_event('Stage Two', datetime(2016, 4, 8, 11, 0)).name == 'Event at Stage 2'
    with pytest.raises(EventNotFound):
        stages.get_event('Stage Two', datetime(2016, 4, 8, 11, 1))
    # Check alias
    with pytest.raises(EventNotFound):
        stages.get_event('1', datetime(2016, 4, 8, 9, 29))
    assert stages.get_event('1', datetime(2016, 4, 8, 9, 30)).name == 'Some Event'


def test_from_txt_invalid(datetime_mock):
    with pytest.raises_regexp(ValueError, r'Invalid syntax at line 1: invalid x:y'):
        Stages.from_txt(StringIO(u'invalid x:y'))
    with pytest.raises_regexp(ValueError, r"Undefined stage at line 1: u'Some Event 9:30-11:30'"):
        Stages.from_txt(StringIO(u'Some Event 9:30-11:30\n'))
    with pytest.raises_regexp(ValueError, r"Invalid datetime at line 2: u'Some Event 9:30-25:30'"):
        Stages.from_txt(StringIO(
            u'Stage 1\n'
            u'Some Event 9:30-25:30\n'
        ))


def test_setup():
    assert stages._stages is None
    stages.setup('bot-name')
    assert isinstance(stages._stages, Stages)


def test_format_times():
    f = _format_times
    assert f(datetime(2016, 4, 7, 11, 0), datetime(2016, 4, 7, 11, 30)) == '11:00-11:30am'
    assert f(datetime(2016, 4, 7, 11, 30), datetime(2016, 4, 7, 12, 30)) == '11:30-12:30pm'
