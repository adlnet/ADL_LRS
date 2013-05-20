from fabric.api import local,run
import os
from os import path
import pdb
import sys

def create_media():
    agent_profile = 'agent_profile'
    activity_profile = 'activity_profile'
    activity_state = 'activity_state'
    statement_attachments = 'attachment_payloads'
    pdb.set_trace()
    # Add settings module so fab file can see it
    cwd = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(cwd)
    env_dir = os.path.join(cwd, '../env/lib/python2.7/site-packages')
    # sys.path.append('/home/lou/gitrepos/env/lib/python2.7/site-packages')
    sys.path.append(env_dir)

    os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
    from django.conf import settings

    adldir = settings.MEDIA_ROOT
    #Create media directories
    if not os.path.exists(path.join(adldir,activity_profile)):
        os.makedirs(path.join(adldir,activity_profile))

    if not os.path.exists(path.join(adldir,activity_state)):
        os.makedirs(path.join(adldir,activity_state))

    if not os.path.exists(path.join(adldir,agent_profile)):
        os.makedirs(path.join(adldir,agent_profile))

    if not os.path.exists(path.join(adldir,statement_attachments)):
        os.makedirs(path.join(adldir,statement_attachments))

def setup_env():
    INSTALL_STEPS = ['virtualenv ../env;. ../env/bin/activate;pip install -r requirements.txt;deactivate']
    for step in INSTALL_STEPS:
        local(step)
