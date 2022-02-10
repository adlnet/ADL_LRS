FROM python:3.9

ENV UWSGI_PIP_VERSION 2.0.20

RUN mkdir /opt/lrs /opt/lrs/logs

# Install our reqs
RUN apt-get update && \
	apt-get install -y && \
	pip3 install fabric3 virtualenv

RUN echo "Cloning LRS Branch" && \
	git clone https://github.com/adlnet/ADL_LRS /opt/lrs/ADL_LRS		

WORKDIR /opt/lrs/ADL_LRS

ENV DJANGO_ENV=prod
ENV DOCKER_CONTAINER=1

# Prepare the configuration
COPY uwsgi/lrs_uwsgi.ini /etc/uwsgi/vassals/lrs_uwsgi.ini
COPY uwsgi/lrs.service /lib/systemd/system/lrs.service

COPY settings.ini /opt/lrs/ADL_LRS/adl_lrs/settings.ini
COPY modified-fabfile.py /opt/lrs/ADL_LRS/fabfile.py

# We'll need to run the setup
COPY scripts/setup-lrs.sh /bin/setup-lrs.sh
COPY scripts/test-lrs.sh /bin/test-lrs.sh
COPY scripts/setup-admin.sh /bin/setup-admin.sh

CMD ["/bin/setup-lrs.sh"]
