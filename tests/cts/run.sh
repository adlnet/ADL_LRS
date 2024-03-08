#!/bin/bash

export NODE_TLS_REJECT_UNAUTHORIZED=0

source ../.env
cd suite
node ./bin/console_runner.js \
    --basicAuth \
    --authUser $LRS_ADMIN_USER \
    --authPassword $LRS_ADMIN_PASS \
    --endpoint "$LRS_ENDPOINT/xAPI"

unset NODE_TLS_REJECT_UNAUTHORIZED
