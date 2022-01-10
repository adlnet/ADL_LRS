#!/bin/bash

# Add the script into our docker container and then run it
docker cp ./lrs/setup-admin.sh docker_lrs:/bin/setup-admin.sh
docker exec -it docker_lrs /bin/setup-admin.sh
