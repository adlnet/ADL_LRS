#!/bin/bash
# Automate part of the process of installing an LRS on an ubuntu 12.04+ system.
#
# Prior to running this script, please reference the README and follow the
# instructions for creating an adllrs user
#
# Copyright 2014 Advanced Distributed Learning
# Apache License, Version 2.0

# Make sure the script is being run by a superuser (root or sudo)
if [[ $(/usr/bin/id -u) -ne 0 ]]; then echo "This script must be run as root"; exit; fi

echo ">>> Installing dependencies..."
apt-get install fabric postgresql-9.1 python-setuptools postgresql-server-dev-9.1 python-dev libxml2-dev libxslt-dev

echo ">>> Installing pip with easy_install..."
easy_install pip

echo ">>> Installing virtualenv with pip..."
pip install virtualenv

echo ">>> Setting up postgres user and database. When prompted, enter a password for this database user."
sudo -u postgres createuser -s -P -e root
sudo -u postgres psql -c 'CREATE DATABASE lrs OWNER root TEMPLATE template1'

echo -e "Dependencies installed and database prepared. Finish installation as adllrs user: \n\n"
echo "su - adllrs"
echo "fab setup_env"
echo "source ../env/bin/activate"
echo "fab setup_lrs"

echo -e "\n\nTo run your LRS locally using django type the following command:\n python manage.py runserver"
