#!/bin/bash


 # Simple script to install and run ESlint
        echo ""
	echo "#====================================================#"
	echo "#        Installing and Configuring ESlint"
	echo "#====================================================#"
	echo ""

# Install npm if not already intsalled
	sudo apt-get install npm
# Install eslint if not already intsalled
	npm install --save-dev eslint
	#sudo apt install eslint -g
	
	#chmod -R a+x node_modules
	sudo rm -rf node_modules
# Initialize config file if not already done
	npm init
	npm init @eslint/config

       
	echo ""
	echo "#====================================================#"
	echo "#        ESlint Installation Complete"
	echo "#====================================================#"
	echo ""
 
# Check ESlint version to make sure it is installed
	eslint -v

	echo ""
	echo "#====================================================#"
	echo "#       Now Running ESlint"
	echo "#====================================================#"
	echo ""
 
 # Run ESlint on NodeJS files
	eslint ./
 
	echo ""
	echo "#====================================================#"
	echo "#      NodeJS Linting Complete (Comments Above) "
	echo "#====================================================#"
	echo ""
