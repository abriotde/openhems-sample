#!/bin/bash

HOMEASSISTANT_EMHASS_DIR=/home/alberic/Documents/OpenHomeSystem/emhassenv
DOCKER_NAME=homeassistant_emhass

ACTION=$#

DO_INSTALL=0
DO_START=0

if [ `docker ps --format '{{.Names}}'|grep $DOCKER_NAME|wc -l` -ge 1 ]; then
	echo "Docker container '$DOCKER_NAME' is running."
else if [ `docker ps -a --format '{{.Names}}'|grep $DOCKER_NAME|wc -l` -ge 1 ]; then
	echo "Docker container '$DOCKER_NAME' exist but is down."
	DO_START=1
else
	echo "No docker container '$DOCKER_NAME'."
	DO_INSTALL=1
fi
fi

if [ $# -eq 1 ] && [ $1 == "--init" ]; then
	DO_INSTALL=1
else if [ $# -eq 1 ] && [ $1 == "--start" ]; then
	DO_START=1
fi
fi

if [ $DO_INSTALL -eq 1 ]; then
	echo "Create docker '$DOCKER_NAME'"
	docker run --restart=unless-stopped \
		-p 5000:5000 \
		-e LOCAL_COSTFUN="profit" \
		-v $HOMEASSISTANT_EMHASS_DIR/config_emhass.yaml:/app/config_emhass.yaml \
		-v $HOMEASSISTANT_EMHASS_DIR/data:/app/data  \
		-v $HOMEASSISTANT_EMHASS_DIR/secrets_emhass.yaml:/app/secrets_emhass.yaml \
		--name $DOCKER_NAME \
		davidusb/emhass-docker-standalone
else if [ $DO_START -eq 1 ]; then
	echo "Start docker '$DOCKER_NAME'"
	docker start $DOCKER_NAME
fi
fi

echo "Update scripts"
docker cp ./deferrable.py homeassistant_emhass:/app/
docker cp ./test_emhass.py homeassistant_emhass:/app/
echo "Run scripts"
docker exec -it homeassistant_emhass ./test_emhass.py --docker

