#!/bin/bash

docker stop homeassistant_surget
docker start homeassistant_surget

exit

sudo docker run -d \
  --name homeassistant_surget \
  --privileged \
  --restart=unless-stopped \
  -e TZ=MY_TIME_ZONE \
  -v $HOME/bin/home-assistant/config:/config \
  -v /run/dbus:/run/dbus:ro \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable

docker exec -it homeassistant_surget  bash
