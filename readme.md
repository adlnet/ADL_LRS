# ADL LRS 

## Installation on Ubuntu machine (Note: This is still in the development stage and NOT ready for production)

If python is not installed, run

    sudo apt-get install python

Install django

    wget "http://www.djangoproject.com/download/1.4/tarball/" -O Django-1.4.tar.gz
    tar xzvf Django-1.4.tar.gz
    cd Django-1.4
    sudo python setup.py install

Install Git
    
    sudo apt-get install git

Install Fabric

    sudo apt-get install fabric

Install other dependencies

    sudo apt-get install python-setuptools libmysqlclient-dev python-dev python-mysqldb python-libxml2 python-libxslt1 libxml2-dev libxslt1-dev

Currently the LRS supports both Postgres and MySQL backends. Depending on which you want to use, comment out the backend you don't want and follow the instructions below for the one you chose. When xAPI 1.0 is released we will be moving to Postgres full time

**MySQL**

Install MySQL

    sudo apt-get install mysql-server

Create LRS database

    mysqladmin -h localhost -u {username} -p create lrs

**End MySQL**

**Postgres**

Install Postgres

    sudo apt-get install postgresql-9.1

Set postgres user password

    sudo passwd postgres

Create user for postgres that will own LRS database
    
    sudo -u postgres createuser -P {username}

Switch to postgres user

    su postgres

Enter Postgres shell

    psql template1

Create DB and owner

    CREATE DATABASE lrs OWNER {username} ENCODING 'UTF8';
    (To exit shell - '\q', then switch back to your normal Linux user)

Download python-psycopg2 and libpq-dev

    sudo apt-get install python-psycopg2 libpq-dev

**End Postgres**

Navigate to desired repository directory and clone LRS repository

    git clone https://github.com/adlnet/ADL_LRS.git
    cd ADL_LRS
    
NOTE: Be sure in your settings file (ADL_LRS/adl_lrs/settings.py) your USER and PASSWORD entries are correct for your DB)

Run fabric file to install all local dependencies and create needed directories    

    sudo fab deps_local

Activate your virtual environment (while still in ADL_LRS)

    . env/bin/activate

Create LRS cache table

    python manage.py createcachetable cache_statement_list

While still in the ADL_LRS directory, update the database
    
    python manage.py syncdb

When prompted to create a superuser, say yes

## Starting
While still in the ADL_LRS directory, run

    supervisord

To verify it's running

    supervisorctl

You should see a task named web running. This will host the application using gunicorn with 2 worker processes

## Test LRS
    
    fab test_lrs

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