#!/bin/bash

mkdir -p ./docker/certbot/etc/live/$1

echo "[SSL] Ensured Certbot SSL Directory" 

cp ./docker/certbot/local/fullchain.pem  ./docker/certbot/etc/live/$1/fullchain.pem

echo "[SSL] Copied temporary SSL Cert to ./docker/certbot/etc/live/$1/fullchain.pem" 

cp ./docker/certbot/local/privkey.pem  ./docker/certbot/etc/live/$1/privkey.pem

echo "[SSL] Copied temporary SSL Key to ./docker/certbot/etc/live/$1/privkey.pem" 
echo "" 
