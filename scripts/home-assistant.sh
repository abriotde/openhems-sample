#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

source config.sh
source functions.sh


function installHomeAsssistant {
	echo "Run Home-Assistant"
	mkdir -p $HOMEASSISTANT_DIR
	mkdir -p $HOMEASSISTANT_CONFIG_PATH
	launchDocker $DOCKER_HA_NAME
	wait_homeassistant_container_up

	cp $OPENHEMS_PATH/config/dashboards.yaml $OPENHEMS_PATH/config/configuration.yaml $HOMEASSISTANT_CONFIG_PATH

	# Systemd
	# ExecStart=/usr/local/bin/systemd-docker --cgroups name=systemd run --rm --name %n redis
	# go install github.com/ibuildthecloud/systemd-docker@latest
	# https://blog.container-solutions.com/running-docker-containers-with-systemd
	cat >homeassistant.service <<EOF
[Unit]
Description = Home-Assistant server.
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop $DOCKER_HA_NAME
ExecStartPre=-/usr/bin/docker rm $DOCKER_HA_NAME
ExecStartPre=/usr/bin/docker pull $DOCKER_HA_NAME
ExecStart=/usr/bin/docker run --rm --privileged --name $DOCKER_HA_NAME -v $HOMEASSISTANT_DIR/config:/config -v /run/dbus:/run/dbus:ro --network=host ghcr.io/home-assistant/home-assistant:stable
StandardOutput=append:$OPENHEMS_LOGPATH/homeassistant.service.log
StandardError=append:$OPENHEMS_LOGPATH/homeassistant.service.error.log
SyslogIdentifier=HomeAssistant

[Install]
WantedBy = multi-user.target
EOF
	sudo mv homeassistant.service /lib/systemd/system/
	ln -s /lib/systemd/system/homeassistant.service /etc/systemd/system/multi-user.target.wants



	echo "Install HACS"
	# https://hacs.xyz/docs/setup/download/
	mkdir -p $HOMEASSISTANT_CONFIG_PATH/custom_components
	cd $HOMEASSISTANT_CONFIG_PATH
	wget -O - https://get.hacs.xyz | bash -

	docker stop homeassistant
	sleep 3
	docker start homeassistant
	wait_homeassistant_container_up
}

function installHttps {
	echo "Install HTTPS : reverse-proxy NginX"
	# sudo add-apt-repository ppa:certbot/certbot
	# sudo apt update
	sudo apt install -y nginx software-properties-common python3-certbot-nginx
	sudo certbot --nginx
	cat >reverse-proxy-ssl.conf <<EOF
map \$http_upgrade \$connection_upgrade {
	default upgrade;
	''      close;
}
server {
	listen 443 ssl;
	server_name         $DOMAINNAME;
	ssl_certificate     /etc/letsencrypt/live/$DOMAINNAME/cert.pem;
	ssl_certificate_key /etc/letsencrypt/live/$DOMAINNAME/privkey.pem;
	access_log /var/log/nginx/reverse-access.log;
	error_log /var/log/nginx/reverse-error.log;
	location / {
		proxy_pass http://127.0.0.1:8123;
		proxy_set_header Host \$host;
		proxy_redirect http:// https://;
		proxy_http_version 1.1;
		proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
		proxy_set_header Upgrade \$http_upgrade;
		proxy_set_header Connection \$connection_upgrade;
		#   proxy_set_header X-Forwarded-Port  443;
	}
}
EOF
	sudo cp reverse-proxy-ssl.conf /etc/nginx/sites-available/
	sudo ln -s /etc/nginx/sites-available/reverse-proxy-ssl.conf /etc/nginx/sites-enabled/reverse-proxy-ssl.conf
	sudo unlink /etc/nginx/sites-enabled/default
	sudo nginx -t
	sudo service nginx reload
}
function updateHomeAsssistant {
	# https://www.home-assistant.io/integrations/backup/
	# http://192.168.1.202:8123/developer-tools/service?service=backup.create
	docker pull ghcr.io/home-assistant/home-assistant:stable
	# TODO : Backup home-assistant...
	docker stop $DOCKER_HA_NAME
	docker container rm $DOCKER_HA_NAME
	# docker rmi ghcr.io/home-assistant/home-assistant:stable
	# tar -xOf <backup_tar_file> "./homeassistant.tar.gz" | tar --strip-components=1 -zxf - -C <restore_directory>
	launchDocker $DOCKER_HA_NAME
	wait_homeassistant_container_up
}

if [[ $# != 1 ]] ; then
	echo "ERROR : Missing argument (install|start|stop|update)"
	exit  1
fi

if [[ $1 == "start" ]]; then
	echo "Start $DOCKER_HA_NAME"
	launchDocker $DOCKER_HA_NAME
else if [[ $1 == "stop" ]]; then
	echo "Stop $DOCKER_HA_NAME"
	docker stop $DOCKER_HA_NAME
	docker ps
else if [[ $1 == "install" ]]; then
	echo "Install $DOCKER_HA_NAME docker"
	installDocker
	installHomeAsssistant
	installHttps
else if [[ $1 == "update" ]]; then
	echo "Update $DOCKER_HA_NAME docker"
	echo " It will take a long time"
	updateHomeAsssistant
else
	echo "ERROR : Ivalid argument '$1' (install|start|stop|update)"
	exit  1
fi
fi
fi
fi
