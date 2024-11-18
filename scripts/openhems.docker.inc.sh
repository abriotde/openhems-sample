
function installOpenHemsPrerequisites {
	echo "Install OpenHEMS dependancies"
	installDocker

	echo "Set incrontab for VPN"
	sudo chmod -R 777 /data/vpn/
	mkdir -p /data/vpn/
	touch /data/vpn/request
	touch /data/vpn/response

	sudo apt install -y incron
	if [[ $? == 0 ]]; then
		grep root /etc/incron.allow
		if [ $? != 0 ]; then
			echo root >> /etc/incron.allow
		fi
		cat >incrontab.root <<EOF
	/data/vpn/request       IN_ATTRIB,IN_CLOSE_WRITE        $OPENHEMS_PATH/scripts/vpn_server.py
	EOF
		incrontab incrontab.root
	else # set incron as server...
		cat >openhems_vpn.service <<EOF
[Unit]
Description = OpenHEMS server (core and web).
After = docker.target

[Service]
# User=openhems
ExecStart = $OPENHEMS_PATH/src/openhems/main.py
StandardOutput=append:$OPENHEMS_LOGPATH/openhems_vpn.service.log
StandardError=append:$OPENHEMS_LOGPATH/openhems_vpn.service.error.log
SyslogIdentifier=OpenHEMS
Restart=always

[Install]
WantedBy = multi-user.target
EOF
			sudo mv openhems_vpn.service /lib/systemd/system/
			ln -s /lib/systemd/system/openhems_vpn.service /etc/systemd/system/multi-user.target.wants
			activate_service openhems_vpn.service
	fi
}

function installOpenHemsService {
	# ExecStart=/usr/local/bin/systemd-docker --cgroups name=systemd run --rm --name %n redis
	# https://blog.container-solutions.com/running-docker-containers-with-systemd
	echo "installOpenHemsService"
}

function installOpenHems {
	launchDocker $DOCKER_NAME
}

function updateOpenHEMS {
	docker pull ghcr.io/abriotde/openhems-sample:main
	# TODO : Backup
	docker stop $DOCKER_NAME
	docker container rm $DOCKER_NAME
	# docker rmi ghcr.io/abriotde/openhems-sample:main
	launchDocker $DOCKER_NAME
}

function startOpenHEMS {
	launchDocker $DOCKER_NAME
}

function stopOpenHEMS {
	docker stop $DOCKER_NAME
	docker ps
}
