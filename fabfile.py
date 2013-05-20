import os
import sys
from fabric.api import local,run

def setup_env():
    INSTALL_STEPS = ['virtualenv ../env;. ../env/bin/activate;pip install -r requirements.txt;deactivate']
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
    sys.path.append(cwd)
    env_dir = os.path.join(cwd, '../env/lib/python2.7/site-packages')
    sys.path.append(env_dir)

    # Add settings module so fab file can see it
    os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
    from django.conf import settings
    adldir = settings.MEDIA_ROOT

    # Create media directories
    if not os.path.exists(os.path.join(adldir,activity_profile)):
        os.makedirs(os.path.join(adldir,activity_profile))

    if not os.path.exists(os.path.join(adldir,activity_state)):
        os.makedirs(os.path.join(adldir,activity_state))

    if not os.path.exists(os.path.join(adldir,agent_profile)):
        os.makedirs(os.path.join(adldir,agent_profile))

    if not os.path.exists(os.path.join(adldir,statement_attachments)):
        os.makedirs(os.path.join(adldir,statement_attachments))

    # Create cache tables and sync the db
    local('./manage.py createcachetable cache_statement_list')
    local('./manage.py createcachetable attachment_cache')
    local('./manage.py syncdb')

def test_lrs():
    local('./manage.py test lrs')