#!/bin/bash

# Move to the LRS directory
cd /opt/lrs/ADL_LRS

# Activate the virtualenv
source ../env/bin/activate

# Setup the LRS itself
fab test_lrs