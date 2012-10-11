# ADL LRS

## Installation on Ubuntu machine

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

Install MySQL

    sudo apt-get install mysql-server

Create LRS database

    mysqladmin -h localhost -u {username} -p create lrs

Navigate to desired repository directory and clone LRS repository

    git clone https://github.com/adlnet/ADL_LRS.git
    cd ADL_LRS
    git checkout 0.9
    
NOTE: Be sure in your settings file (ADL_LRS/adl_lrs/settings.py) your USER and PASSWORD entries are correct for your MySQL DB)

Run fabric file to install all local dependencies and create needed directories    

    sudo fab deps_local

Create LRS cache table

    python manage.py createcachetable cache_statement_list

Activate your virtual environment (while still in ADL_LRS)

    . env/bin/activate

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

        