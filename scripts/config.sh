

RSYNC_CMD="rsync -avpzh"

DOMAINNAME=openproduct.freeboxos.fr # Change to your domainname
HOMEASSISTANT_IP=192.168.1.202 # Set a static IP not in your DHCP
HOMEASSISTANT_DIR=$HOME/bin/home-assistant
HOMEASSISTANT_CONFIG_PATH=$HOMEASSISTANT_DIR/config
DOCKER_NAME=homeassistant

HOMEASSISTANT_EMHASS_DIR=$HOMEASSISTANT_DIR/emhass
DOCKER_EMHASS_NAME=homeassistant_emhass

OPENHEMS_PATH=$(dirname $PWD)
TMP_DIR=/tmp
VPN_IP=10.0.0.2

