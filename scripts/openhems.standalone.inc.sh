
function installOpenHemsPrerequisites {
	echo "Install OpenHEMS server"
	sudo apt install -y python3-pandas python3-yaml python3-pyramid python3-pyramid-jinja2 python3-astral python3-virtualenv
}

function installOpenHemsService {
cat >openhems.service <<EOF
[Unit]
Description = OpenHEMS server (core and web).
After = docker.target

[Service]
# User=openhems
ExecStart = $OPENHEMS_PATH/src/openhems/main.py
StandardOutput=append:$OPENHEMS_LOGPATH/openhems.service.log
StandardError=append:$OPENHEMS_LOGPATH/openhems.service.error.log
SyslogIdentifier=OpenHEMS
Restart=always

[Install]
WantedBy = multi-user.target
EOF
	sudo mv openhems.service /lib/systemd/system/
	ln -s /lib/systemd/system/openhems.service /etc/systemd/system/multi-user.target.wants
	activate_service openhems.service
}

function updateOpenHEMS {
	cd $OPENHEMS_PATH/scripts
	./autoupdate.sh
}

# TODO : Install custom Python + venv ?

# Venv
# sudo apt install libffi-dev
