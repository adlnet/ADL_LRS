from fabric.api import local,run
import os
from os import path

#Add settings module so fab file can see it
os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
from django.conf import settings

adldir = settings.MEDIA_ROOT
agent_profile = 'agent_profile'
activity_profile = 'activity_profile'
activity_state = 'activity_state'
statement_attachments = 'attachment_payloads'

INSTALL_STEPS = ['sudo easy_install pip',
                 'sudo pip install virtualenv',
                 'virtualenv env;. env/bin/activate;pip install -r requirements.txt;deactivate']
                 
def deps_local():
    for step in INSTALL_STEPS:
        local(step)

    #Create media directories and give them open permissions
    if not os.path.exists(path.join(adldir,activity_profile)):
        os.makedirs(path.join(adldir,activity_profile))

    if not os.path.exists(path.join(adldir,activity_state)):
        os.makedirs(path.join(adldir,activity_state))

    if not os.path.exists(path.join(adldir,agent_profile)):
        os.makedirs(path.join(adldir,agent_profile))

    if not os.path.exists(path.join(adldir,statement_attachments)):
        os.makedirs(path.join(adldir,statement_attachments))

def deps_remote():
    for step in INSTALL_STEPS:
        run(step)
    
def test_lrs():
    local('./manage.py test lrs')	
