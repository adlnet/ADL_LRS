#!/bin/bash
docker stop $(docker ps -a -q) --force
docker rm $(docker ps -a -q) --force
docker rmi $(docker images -a -q) --force
