# ADL LRS

## Installation on Linux machine

If python is not installed, run

    sudo apt-get install python

If you're running Ubuntu 12.XX you'll have to install django manually

    wget "http://www.djangoproject.com/download/1.4/tarball/" -O Django-1.4.tar.gz
    tar xzvf Django-1.4.tar.gz
    cd Django-1.4
    sudo python setup.py install

Install Git
    
    sudo apt-get install git

Install Fabric

    sudo apt-get install fabric

Install virtual environment

    sudo apt-get install python-virtualenv

Create python virtual environment and activate

    mkdir ~/virtualenv
    virtualenv ~/virtualenv/lrs
    source ./virtualenv/lrs/bin/activate

Navigate to desired repository directory and clone LRS repository

    git clone https://github.com/adlnet/ADL_LRS.git
    cd ADL_LRS
    
Run fabric file to install all local dependencies and create needed directories    

    fab deps_local
    sudo fab create_dirs

## Starting
While still in the ADL_LRS directory, run

    supervisord

To verify it's running

    supervisorctl

You should see a task named web running. This will host the application using gunicorn with 2 worker processes

While still in the ADL_LRS directory, create/update the database
    
    python manage.py syncdb
        