slack-bot
=========

Assumptions
-----------

* You have already signed up with [Beep Boop](https://beepboophq.com) and have a local fork of this project.

* You have sufficient rights in your Slack team to configure a bot and generate/access a Slack API token.

Deploy on BeepBoop
------------------

1. In BeepBoop, click "My Teams" and authorize it to your Slack team.

2. In BeepBoop, click "My Projects" and add a bot (specify github repo)

3. In Slack, add a bot user to your team and copy API token: https://my.slack.com/services/new/bot

4. In BeepBoop bot Settings page, save API token

5. In BeepBoop bot Status page, click "Start Bot"

6. In Slack, click Settings (gear icon) -> "Invite bot to a channel" to make it available in `#general` or other channels.

Run locally (for debug)
-----------------------

Please note that you should stop BeepBoop-hosted bot first.

Install dependencies ([virtualenv](http://virtualenv.readthedocs.org/en/latest/) is recommended)

	pip install -r requirements.txt
	export SLACK_TOKEN=<YOUR SLACK TOKEN>
	python rtmbot.py

Things are looking good if the console prints something like:

	Connected <your bot name> to <your slack team> team at https://<your slack team>.slack.com.

If you want change the logging level, prepend `export LOG_LEVEL=<your level>; ` to the `python rtmbot.py` command.
