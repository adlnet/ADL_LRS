#!/bin/bash

mkdir -p ./certbot/etc/live/$1

echo "[SSL] Ensured Certbot SSL Directory" 

cp ./certbot/local/fullchain.pem  ./certbot/etc/live/$1/fullchain.pem

echo "[SSL] Copied temporary SSL Cert to ./certbot/etc/live/$1/fullchain.pem" 

cp ./certbot/local/privkey.pem  ./certbot/etc/live/$1/privkey.pem

echo "[SSL] Copied temporary SSL Key to ./certbot/etc/live/$1/privkey.pem" 
echo "" 
