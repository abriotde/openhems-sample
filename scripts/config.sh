

RSYNC_CMD="rsync -avpzh"

DOMAINNAME=openproduct.freeboxos.fr # Change to your domainname
HOMEASSISTANT_IP=192.168.1.202 # Set a static IP not in your DHCP
HOMEASSISTANT_DIR=/home/olimex/openhems-sample
HOMEASSISTANT_CONFIG_PATH=$HOMEASSISTANT_DIR/config
DOCKER_HA_NAME=homeassistant

HOMEASSISTANT_EMHASS_DIR=$HOMEASSISTANT_DIR/emhass
DOCKER_EMHASS_NAME=homeassistant_emhass

DOCKER_NAME=openhems
OPENHEMS_USER=olimex
OPENHEMS_PATH=/home/olimex/openhems-sample
OPENHEMS_BRANCH=main
OPENHEMS_DOCKER_VERSION=latest
TMP_DIR=/tmp
VPN_IP=10.0.0.2
MY_TIME_ZONE=`cat /etc/timezone`
DOCKER_OPENHEMS=0

source ../config/config.inc.sh

