#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

function wait_homeassistant_container_up {
	docker container ls -a
	docker container ps
	echo "Waiting Home-Assistant server is ready"
	while [ `wget -O - http://127.0.0.1:8123 2>/dev/null|wc -c` -lt 1000 ]; do
		echo -n .
		sleep 1
	done
	echo "Ok, waiting 30 more seconds"
	sleep 30
}

function activate_service {
	service = $1
	if [ -f $service ]; then
		sudo cp $service /etc/systemd/system/
		sudo mv $service /lib/systemd/system/
	fi
	ln -s /lib/systemd/system/$service /etc/systemd/system/multi-user.target.wants
	systemctl daemon-reload
    systemctl enable $service
    systemctl start $service
    ok=`systemctl is-active --quiet $service`
    if [ $ok != 0 ]; then
        echo "ERROR : Fail activate '$service'. Something goes wrong. Cancel installation."
        exit 1
    fi
}

function installDocker {
	if docker run hello-world 2>&1 >/dev/null; then
		echo "Docker is ever installed"
		return
	fi

	echo "Install docker"
	# https://docs.docker.com/engine/install/debian/
	for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt remove $pkg; done

	# Add Docker's official GPG key:
	sudo apt update
	sudo apt install -y ca-certificates curl
	sudo install -m 0755 -d /etc/apt/keyrings
	sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
	sudo chmod a+r /etc/apt/keyrings/docker.asc
	# Add the repository to Apt sources:
	echo \
	  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
	  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
	  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
	sudo apt update
	# Add $USER to docker group
	sudo groupadd docker
	sudo usermod -aG docker $OPENHEMS_USER
	sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

function launchDocker {
	dockerName=$1
	DO_START=0
	if [[ `docker ps --format '{{.Names}}'|grep $dockerName|wc -l` -ge 1 ]]; then
		echo "Docker container '$dockerName' is running."
	else if [ `docker ps -a --format '{{.Names}}'|grep $dockerName|wc -l` -ge 1 ]; then
		echo "Docker container '$dockerName' exist but is down."
		DO_START=1
	else
		echo "No docker container '$dockerName'."
		DO_INSTALL=1
	fi
	fi

	if [[ $# -eq 1 ]] && [[ $1 == "--init" ]]; then
		DO_INSTALL=1
	else if [[ $# -eq 1 ]] && [[ $1 == "--start" ]]; then
		DO_START=1
	fi
	fi

	if [[ $DO_INSTALL -eq 1 ]]; then
		echo "Create docker '$dockerName'"
		if [[ $dockerName == "homeassistant" ]]; then
			/usr/bin/docker run \
			  --name $dockerName \
			  --privileged \
			  -v $HOMEASSISTANT_DIR/config:/config \
			  -v /run/dbus:/run/dbus:ro \
			  -e TZ=$MY_TIME_ZONE \
			  --network=host --rm \
			  ghcr.io/home-assistant/home-assistant:stable
		else if [[ $dockerName == "openhems" ]]; then
			/usr/bin/docker run \
			  --name $dockerName \
			  --privileged \
			  -v $OPENHEMS_PATH/config:/app/config \
			  -v $OPENHEMS_LOGPATH:/log \
			  -v /data:/opt \
			  -e TZ=$MY_TIME_ZONE \
			  -p 8000:8000 --rm \
			  ghcr.io/abriotde/openhems-sample:$OPENHEMS_DOCKER_VERSION
		else
			echo "ERROR : unknown docker name $dockerName"
			exit 1
		fi
		fi
	else if [ $DO_START -eq 1 ]; then
		echo "Start docker '$dockerName'"
		sudo docker start $dockerName
	fi
	fi
}
