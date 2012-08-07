from fabric.api import local,run
import os
from os import path

#Add settings module so fab file can see it
os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
from django.conf import settings

adldir = settings.MEDIA_ROOT
actor_profile = 'actor_profile'
activity_profile = 'activity_profile'
activity_state = 'activity_state'

INSTALL_STEPS = ['yes | sudo apt-get install libmysqlclient-dev	 python-dev python-mysqldb python-virtualenv',
                 'virtualenv --no-site-packages env',
                 '. env/bin/activate;pip install -r requirements.txt']
def deps_local():
    for step in INSTALL_STEPS:
    	local(step)

    #Create media directories and give them open permissions
	if not os.path.exists(path.join(adldir,activity_profile)):
		os.makedirs(path.join(adldir,activity_profile))
		os.chmod(path.join(adldir,activity_profile), 0777)

	if not os.path.exists(path.join(adldir,activity_state)):
		os.makedirs(path.join(adldir,activity_state))
		os.chmod(path.join(adldir,activity_state), 0777)

	if not os.path.exists(path.join(adldir,actor_profile)):
		os.makedirs(path.join(adldir,actor_profile))
		os.chmod(path.join(adldir,actor_profile), 0777)

def deps_remote():
    for step in INSTALL_STEPS:
    	run(step)	
