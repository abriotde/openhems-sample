#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2
# https://wiki.crowncloud.net/index.php?How_to_Install_Python_3_11_on_Debian_11 (3.11.10)
# virtualenv --python="/usr/bin/python2.6" "/path/to/new/virtualenv/"
# https://www.tderflinger.com/using-systemd-to-start-a-python-application-with-virtualenv
# https://hub.docker.com/r/linuxserver/wireguard



if [[ DOCKER_OPENHEMS == 1 ]]; then
	source openhems.inc.docker.sh
else
	source openhems.inc.standalone.sh
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
	installVPN
	installLogrotate
	installOpenHems
	installOpenHemsService
else
	echo "ERROR : Ivalid argument '$1' (install|start|stop|update)"
	exit  1
fi
fi
fi
fi
