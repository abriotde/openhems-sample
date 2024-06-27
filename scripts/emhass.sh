#!/bin/bash

HOMEASSISTANT_DIR=/home/alberic/bin/home-assistant
HOMEASSISTANT_EMHASS_DIR=$HOMEASSISTANT_DIR/emhass
DOCKER_NAME=homeassistant_emhass

docker stop homeassistant_emhass
docker start homeassistant_emhass

exit


docker run --restart=unless-stopped \
	-p 5000:5000 \
	-e LOCAL_COSTFUN="profit" \
	-v $HOMEASSISTANT_EMHASS_DIR/config_emhass.yaml:/app/config_emhass.yaml \
	-v $HOMEASSISTANT_EMHASS_DIR/data:/app/data  \
	-v $HOMEASSISTANT_EMHASS_DIR/secrets_emhass.yaml:/app/secrets_emhass.yaml \
	--name $DOCKER_NAME \
	davidusb/emhass-docker-standalone


emhass --config=/home/alberic/bin/home-assistant/emhass/config_emhass.yaml --data=/home/alberic/bin/home-assistant/emhass/data --root=/home/alberic/Documents/OpenHouseEnergyManager/emhass

