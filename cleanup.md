# ADL LRS 

## Running the cleanup command for older logs and setting up cronjob

If you do not wish to keep storing all of the logs, or 'system actions' that are happening, there is a custom Django command you can run to remove them after a certain number of days.

    python manage.py system_action_cleanup

That command looks for the DAYS_TO_LOG_DELETE setting in settings.py and removes any logs after that amount of days. If you wish to run a cronjob, edit your crontab file with this

	DJANGO_CONF=conf.dev
	0 0 * * 7 /home/lou/gitrepos/ADL_LRS/env/bin/python /home/lou/gitrepos/ADL_LRS/manage.py system_action_cleanup > /dev/null 2>&1

This job runs cleanup every Sunday at midnight. You can edit it for any time you wish (checkout the cron help pages online) and also write any output/errors to any file you wish by replacing '/dev/null' with the file path. Also, make sure the two lines above are own their own separate lines, and they don't exceed one line. The job might be broken up after 'manage.py' here but be sure that it all on one line and it must end with a line feed (press ENTER) 