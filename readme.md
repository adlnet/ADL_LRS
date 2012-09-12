# ADL LRS

## Installation on Linux machine

If python is not installed, run

    sudo apt-get install python
    
Install pip

    sudo easy_install pip
    
Install virtual environment

    sudo easy_install virtualenv
    
Create python virtual environment and activate

    mkdir ~/virtualenv
    virtualenv ~/virtualenv/lrs
    source ./virtualenv/lrs/bin/activate
    
Navigate to desired repository directory

Clone the git repository

    git clone https://github.com/adlnet/ADL_LRS.git
    
Install fabric at the machine level

    sudo apt-get install fabric

Then navigate to the ADL_LRS directory and run our fabric file to install all local dependencies and create needed directories

    cd ADL_LRS
    sudo fab deps_local

## Starting
While still in the ADL_LRS directory, run

    supervisord

To verify it's running

    supervisorctl

You should see a task named web running. This will host the application using gunicorn with 2 worker processes

While still in the ADL_LRS directory, create/update the database
    
    python manage.py syncdb
    