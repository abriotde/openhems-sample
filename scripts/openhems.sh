#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

source openhems.inc.sh
if [[ $DOCKER_OPENHEMS == 1 ]]; then
	source openhems.docker.inc.sh
else
	source openhems.standalone.inc.sh
fi

if [[ $1 == "start" ]]; then
	echo "Start $DOCKER_NAME"
	startOpenHEMS
else if [[ $1 == "update" ]]; then
	echo "Update $DOCKER_NAME docker"
	echo " It will take a long time"
	updateOpenHEMS
else if [[ $1 == "stop" ]]; then
	echo "Stop $DOCKER_NAME"
	stopOpenHEMS
else if [[ $1 == "install" ]]; then
	echo "Install $DOCKER_NAME docker"
	installOpenHemsPrerequisites
	# installVPN
	# installLogrotate
	# installAutoupdate
	installOpenHems
	installOpenHemsService
else
	echo "ERROR : Ivalid argument '$1' (install|start|stop|update)"
	exit  1
fi
fi
fi
fi
