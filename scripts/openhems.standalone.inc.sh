
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
	mkdir -p $TMP_DIR/openhems-sample
	TMP_DIR=$TMP_DIR/openhems-sample
	export OPENHEMS_PATH
	export OPENHEMS_USER
	export OPENHEMS_BRANCH
	export TMP_DIR
	$OPENHEMS_PATH/scripts/autoupdate.py
}

# TODO : Install custom Python + venv ?
# https://wiki.crowncloud.net/index.php?How_to_Install_Python_3_11_on_Debian_11 (3.11.10)
# virtualenv --python="/usr/bin/python2.6" "/path/to/new/virtualenv/"
# https://www.tderflinger.com/using-systemd-to-start-a-python-application-with-virtualenv

# Venv
# sudo apt install libffi-dev
