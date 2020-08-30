FROM ubuntu:20.04

ENV TZ=Europe/Dublin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update
RUN apt-get install -y git vim fabric python-setuptools python-dev\
    libxml2-dev libxslt1-dev gcc python2 curl

RUN curl https://bootstrap.pypa.io/get-pip.py --output get-pip.py
RUN python2 get-pip.py

WORKDIR /app
COPY requirements.txt /app

RUN apt-get install -y libmysqlclient-dev default-libmysqlclient-dev mysql-client
RUN pip install -r requirements.txt

COPY ./src /app

EXPOSE 8000
CMD ["scripts/setup_lrs.sh"]