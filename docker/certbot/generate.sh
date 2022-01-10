#!/bin/bash

rm -rf ./certbot/etc/live

docker-compose run certbot \
	certonly --webroot \
	--register-unsafely-without-email --agree-tos \
	--webroot-path=/data/letsencrypt \
	-d $1

docker-compose restart nginx
