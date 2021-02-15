#!/bin/sh

docker run --rm \
           --device=/dev/ttyUSB0 \
           --log-driver json-file --log-opt max-size=2m --log-opt max-file=10 \
           --name=aiozigbee_coordinator_test \
           aioxbee_base