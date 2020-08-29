FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install git fabric python-setuptools python-dev\
    libxml2-dev libxslt1-dev gcc

