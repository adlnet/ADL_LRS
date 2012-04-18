from fabric.api import local,run
INSTALL_STEPS = ['yes | sudo apt-get install python-dev python-mysqldb python-virtualenv','virtualenv --no-site-packages env','source env/bin/activate;pip install -r requirements.txt']
def deps_local():
    for step in INSTALL_STEPS:
    	local(step)
def deps_remote():
    for step in INSTALL_STEPS:
    	run(step)	
