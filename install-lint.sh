#!/bin/bash

# Simple script to install and run Hadolint
        echo ""
	echo "#====================================================#"
	echo "#        Installing Hadolint"
	echo "#====================================================#"
	echo ""

# Install Hadolint
	wget -O hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64
# Move to appropriate directory
	mv hadolint /usr/local/bin/hadolint
# Make file executable
	chmod +x /usr/local/bin/hadolint

	echo ""
	echo "#====================================================#"
	echo "#        Hadolint Installation Complete"
	echo "#====================================================#"
	echo ""
 
# Check hadolint version to make sure it is installed
	hadolint -v

	echo ""
	echo "#====================================================#"
	echo "#       Now Running Hadolint on Dockerfile"
	echo "#====================================================#"
	echo ""
 # Run Hadolint on Dockerfile
														       
	docker run --rm -i hadolint/hadolint < Dockerfile

	echo ""
	echo "#====================================================#"
	echo "#      Dockerfile Linting Complete (Comments Above)"
	echo "#====================================================#"
	echo ""

 # Simple script to install and run Pylint
        echo ""
	echo "#====================================================#"
	echo "#        Installing Pylint"
	echo "#====================================================#"
	echo ""

# Install Pylint
	apt install pylint

	echo ""
	echo "#====================================================#"
	echo "#        Pylint Installation Complete"
	echo "#====================================================#"
	echo ""
 
# Check pylint version to make sure it is installed
	pylint --version

	echo ""
	echo "#====================================================#"
	echo "#       Now Running Pylint"
	echo "#====================================================#"
	echo ""
 
 # Run Pylint on Dockerfile
	pylint *.py
 
	echo ""
	echo "#====================================================#"
	echo "#      Python Linting Complete (Comments Above)"
	echo "#====================================================#"
	echo ""
