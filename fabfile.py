from fabric.api import local

def deps_local():
    local('yes | sudo apt-get install python-dev python-mysqldb')
    local('virtualenv --no-site-packages env')
    local('source env/bin/activate;pip install -r requirements.txt')
