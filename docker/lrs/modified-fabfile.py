import os
import sys
from fabric.api import local

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"
ADMIN_EMAILADR = "admin@example.com"


def setup_env():
    INSTALL_STEPS = [
        'virtualenv ../env;. ../env/bin/activate;pip install -r requirements.txt;deactivate']
    for step in INSTALL_STEPS:
        local(step)

def setup_lrs():
    # Media folder names
    agent_profile = 'agent_profile'
    activity_profile = 'activity_profile'
    activity_state = 'activity_state'
    statement_attachments = 'attachment_payloads'

    # Add env packages and project to the path
    cwd = os.path.dirname(os.path.abspath(__file__))

    if cwd not in sys.path:
        sys.path.append(cwd)

    env_dir = '/opt/lrs/env/lib/python3.9/site-packages'
    if env_dir not in sys.path:
        sys.path.append(env_dir)

    log_dir = '/opt/lrs/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    celery_log_dir = os.path.join(log_dir, 'celery')
    if not os.path.exists(celery_log_dir):
        os.makedirs(celery_log_dir)

    supervisord_log_dir = os.path.join(log_dir, 'supervisord')
    if not os.path.exists(supervisord_log_dir):
        os.makedirs(supervisord_log_dir)

    uwsgi_log_dir = os.path.join(log_dir, 'uwsgi')
    if not os.path.exists(uwsgi_log_dir):
        os.makedirs(uwsgi_log_dir)

    nginx_log_dir = os.path.join(log_dir, 'nginx')
    if not os.path.exists(nginx_log_dir):
        os.makedirs(nginx_log_dir)

    # Add settings module so fab file can see it
    os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
    from django.conf import settings
    adldir = settings.MEDIA_ROOT

    # Create media directories
    if not os.path.exists(os.path.join(adldir, activity_profile)):
        os.makedirs(os.path.join(adldir, activity_profile))

    if not os.path.exists(os.path.join(adldir, activity_state)):
        os.makedirs(os.path.join(adldir, activity_state))

    if not os.path.exists(os.path.join(adldir, agent_profile)):
        os.makedirs(os.path.join(adldir, agent_profile))

    if not os.path.exists(os.path.join(adldir, statement_attachments)):
        os.makedirs(os.path.join(adldir, statement_attachments))

    # Create cache tables and sync the db
    local('./manage.py createcachetable')
    local('./manage.py migrate')
    local('./manage.py makemigrations adl_lrs lrs oauth_provider')
    local('./manage.py migrate')
    # createsuperuser has been moved to a script to ignore the default values

# def create_admin():
#     local('./manage.py createsuperuser')

def test_lrs():
    local('./manage.py test lrs.tests')
