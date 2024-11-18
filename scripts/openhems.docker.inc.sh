
function installOpenHemsPrerequisites {
	echo "Install OpenHEMS dependancies"
	sudo apt install -y anacron wireguard logrotate incron
	sudo mkdir -p $OPENHEMS_LOGPATH

	echo "Set incrontab for VPN"
	grep root /etc/incron.allow
	if [ $? != 0 ]; then
		echo root >> /etc/incron.allow
	fi
	mkdir -p /data/vpn/
	touch /data/vpn/request
	touch /data/vpn/response
	cat >incrontab.root <<EOF
/data/vpn/request       IN_ATTRIB,IN_CLOSE_WRITE        $OPENHEMS_PATH/scripts/vpn_server.py
EOF
	incrontab incrontab.root
}

function installOpenHemsService {
	# ExecStart=/usr/local/bin/systemd-docker --cgroups name=systemd run --rm --name %n redis
	# https://blog.container-solutions.com/running-docker-containers-with-systemd
	cat >openhems.service <<EOF
[Unit]
Description = OpenHEMS server (core and web).
After=docker.service
Requires=docker.service
After=homeassisatant.service
Requires=homeassisatant.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop $DOCKER_NAME
ExecStartPre=-/usr/bin/docker rm $DOCKER_NAME
ExecStartPre=/usr/bin/docker pull $DOCKER_NAME
ExecStart=/usr/bin/docker run --rm --name $DOCKER_NAME -v $OPENHEMS_PATH/config:/app/config -v $OPENHEMS_LOGPATH:/log -p 8000:8000 --link homeassistant.service:homeassistant openhomesystem22/openhems:openhems
StandardOutput=append:$OPENHEMS_LOGPATH/openhems.service.log
StandardError=append:$OPENHEMS_LOGPATH/openhems.service.error.log
SyslogIdentifier=OpenHEMS

[Install]
WantedBy = multi-user.target
EOF
	sudo mv openhems.service /lib/systemd/system/
	ln -s /lib/systemd/system/openhems.service /etc/systemd/system/multi-user.target.wants

	activate_service openhems.service
}

function installOpenHems {
	launchDocker $DOCKER_NAME
}

function updateOpenHEMS {
	docker pull ghcr.io/abriotde/openhems-sample:main
	# TODO : Backup
	docker stop $DOCKER_NAME
	docker container rm $DOCKER_NAME
	docker rmi $DOCKER_NAME
	launchDocker $DOCKER_NAME
}

function startOpenHEMS {
	launchDocker $DOCKER_NAME
}

function stopOpenHEMS {
	docker stop $DOCKER_NAME
	docker ps
}
