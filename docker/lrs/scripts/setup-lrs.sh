#!/bin/bash

# Move to the LRS directory
cd /opt/lrs/ADL_LRS

# Set up the environment
fab setup_env

# Activate the virtualenv
source ../env/bin/activate
pip install uwsgi==2.0.20

# Setup the LRS itself
fab setup_lrs

# Make everything here readable
echo "Changing file permissions ..."
chmod -R 775 /opt/lrs
chmod -R 775 /etc/uwsgi/vassals
chmod -R 775 /lib/systemd/system
echo "... file permissions set!  Starting container."

# Start uwsgi
/opt/lrs/env/bin/uwsgi --emperor /etc/uwsgi/vassals
