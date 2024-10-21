#!/bin/bash

HOMEASSISTANT_EMHASS_DIR=/home/alberic/Documents/OpenHomeSystem/emhassenv
DOCKER_NAME=homeassistant_emhass

ACTION=$#

if [ $# -eq 1 ] && [ $1 == "--init" ]; then
	echo "Init docker"
	docker run --restart=unless-stopped \
		-p 5000:5000 \
		-e LOCAL_COSTFUN="profit" \
		-v $HOMEASSISTANT_EMHASS_DIR/config_emhass.yaml:/app/config_emhass.yaml \
		-v $HOMEASSISTANT_EMHASS_DIR/data:/app/data  \
		-v $HOMEASSISTANT_EMHASS_DIR/secrets_emhass.yaml:/app/secrets_emhass.yaml \
		--name $DOCKER_NAME \
		davidusb/emhass-docker-standalone
fi

docker cp ./deferrable.py homeassistant_emhass:/app/
docker cp ./test_emhass.py homeassistant_emhass:/app/
docker exec -it homeassistant_emhass ./test_emhass.py

