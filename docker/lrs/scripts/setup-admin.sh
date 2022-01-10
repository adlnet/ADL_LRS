#!/bin/bash

# Bash into the LRS container and run the createsuperuser django CLI call
cd /opt/lrs/ADL_LRS
source ../env/bin/activate

python ./manage.py createsuperuser


