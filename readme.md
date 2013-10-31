# ADL LRS 

#### Installation tested on Ubuntu 12.10 machine with Python 2.7.3. Should be good with Ubuntu 10.04 LTS - 13.04 releases. This is still in the development stage and NOT ready for production

## Installation

Software Installation

    sudo apt-get install git fabric postgresql-9.1 python-setuptools postgresql-server-dev-9.1 python-dev libxml2-dev libxslt-dev
    sudo easy_install pip
    sudo pip install virtualenv

Setup Postgres

    sudo passwd postgres (set password for postgres system user)
    sudo -u postgres createuser -P <db_owner> (create postgres user that will be owner of the db - make superuser)
    su postgres
    psql template1
    
Create database inside of postgres shell

    CREATE DATABASE lrs OWNER <db_owner>;
    \q (exits shell)
    exit (logout as system postgres user)
    
Create ADL LRS system user

    sudo useradd -c "ADL Learning Record Store System" -m -s "/bin/bash" adllrs
    sudo passwd adllrs (set password)
    su adllrs
    cd ~
    
Create desired directory to keep LRS

    mkdir <dir_name>
    cd <dir_name>
    
Clone the LRS repository

    git clone https://github.com/adlnet/ADL_LRS.git
    cd ADL_LRS
    
Note: Under ADL_LRS/adl_lrs/settings.py, make sure the database USER and PASSWORD are the same as the db_owner created
earlier. Also, be sure to replace the current SECRET_KEY flag with a secret string of your own, and be sure not to share it.

Setup the environment

    fab setup_env
    source ../env/bin/activate 
    
Setup the LRS (creates media directories and cache tables, then syncs database)

    fab setup_lrs (when prompted make adllrs a Django superuser)

## Starting
While still in the ADL_LRS directory, run

    supervisord

To verify it's running

    supervisorctl

You should see a task named web running. This will host the application using gunicorn with 2 worker processes.
If you open a browser and visit http://localhost:8000/xapi you will hit the LRS. Gunicorn does not serve static files
so no CSS will be present. This is fine if you're doing testing/development but if you want to host a production-ready
LRS, Nginx needs to be setup to serve static files. For more production-like environments, we also recommend using uWSGI instead of Gunicorn. Please read [these](https://github.com/adlnet/ADL_LRS/wiki/Using-Nginx-for-Production) instructions for including
Nginx and using uWSGI intead of Gunicorn. For a more detailed description of the tools being used in general, visit [here](https://github.com/adlnet/ADL_LRS/wiki/Putting-the-Pieces-Together).

## Test LRS
    
    fab test_lrs

## Helpful Information
    
* [Test Coverage](https://github.com/adlnet/ADL_LRS/wiki/Code-Coverage)
* [Code Profiling](https://github.com/adlnet/ADL_LRS/wiki/Code-Profiling-with-cProfile)
* [Sending Attachments](https://github.com/adlnet/ADL_LRS/wiki/Sending-Statements-with-Attachments)
* [Setting up Nginx](https://github.com/adlnet/ADL_LRS/wiki/Using-Nginx-for-Production)
* [OAuth Help](https://github.com/adlnet/ADL_LRS/wiki/Using-OAuth)

## License
   Copyright 2012 Advanced Distributed Learning

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
