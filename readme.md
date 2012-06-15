# ADL LRS

## Installiation
Clone the git repository

    git clone https://github.com/adlnet/ADL_LRS.git
    

Install fabric at the machine level

    sudo apt-get install fabric

Then run our fabric file to install all local dependencies

    cd ADL_LRS

    fab deps_local

Be sure to change your username and password to match your DB credentials on your machine in the adl_lrs/settings.py file

## Starting

    cd ADL_LRS

    supervisord

To verify it's running

     supervisorctl

you should see a task named web running


This will host the application using gunicorn with 2 worker processes