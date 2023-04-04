#!/bin/bash

# Simple function to announce what we're doing
function announce() {
	echo ""
	echo "#===============================================================#"
	echo "#            Installing $1"
	echo "#===============================================================#"
}


announce "Git"

if ! [ -x "$(command -v git)" ]; then
	
	# Curl is easy
	apt install -y curl
	
else
	echo "Skipping, Git already installed!"
fi

announce "Curl"

if ! [ -x "$(command -v curl)" ]; then
	
	# Curl is easy
	apt-get install -y curl
	
else
	echo "Skipping, Curl already installed!"
fi

announce "Docker"

if ! [ -x "$(command -v docker)" ]; then
	
	# Docker is a bit complicated
	#
	# Add the GPG Key
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	
	# Add the Docker repository to our APT sources
	add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
	
	# With those added, update our packages
	apt-get update

	# Since we're up to date, get docker
	apt-get install -y docker-ce
else
	echo "Skipping, docker already installed!"
fi


announce "Docker-Compose"

if ! [ -x "$(command -v docker-compose)" ]; then
	
	# Docker-Compose is also complicated
	#
	# Add the GPG Key
	curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
	
	# Make sure it's executable
	chmod +x /usr/local/bin/docker-compose

else
	echo "Skipping, docker-compose already installed!"
fi
