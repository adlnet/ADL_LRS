AGENT_PROFILE='agent_profile'
ACTIVITY_PROFILE='activity_profile'
ACTIVITY_STATE='activity_state'
STATEMENT_ATTACHMENTS='attachment_payloads'

mkdir logs # mount at ../logs
mkdir logs/celery
mkdir logs/supervisord
mkdir logs/uwsgi
mkdir logs/nginx

mkdir media
mkdir media/$AGENT_PROFILE
mkdir media/$ACTIVITY_PROFILE
mkdir media/$ACTIVITY_STATE
mkdir media/$STATEMENT_ATTACHMENTS
