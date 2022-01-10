#!/bin/bash

# Stop the existing docker containers we made with Compose
docker-compose stop

# Rebuild the containers and detatch from this terminal
docker-compose build
docker-compose up -d
