#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

source config.sh
source functions.sh

echo "Install OpenHEMS server"
sudo apt install -y python3-pandas python3-yaml python3-pyramid python3-pyramid-jinja2 python3-astral
OPENHEMS_LOGPATH=/var/log/openhems
sudo mkdir -p $OPENHEMS_LOGPATH
cat >openhems.service <<EOF
[Unit]
Description = OpenHEMS server (core and web).
After = docker.target

[Service]
# User=openhems
ExecStart = $OPENHEMS_PATH/src/main.py
StandardOutput=append:$OPENHEMS_LOGPATH/openhems.service.log
StandardError=append:$OPENHEMS_LOGPATH/openhems.service.error.log
SyslogIdentifier=OpenHEMS
Restart=always

[Install]
WantedBy = multi-user.target
EOF
sudo mv openhems.service /lib/systemd/system/
ln -s /lib/systemd/system/openhems.service /etc/systemd/system/multi-user.target.wants

systemctl enable openhems.service
systemctl start openhems.service

echo "Install Mosquitto : MQTT server" # https://shape.host/resources/mosquitto-mqtt-installation-guide-for-debian-11-easy-setup
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl is-enabled mosquitto
sudo systemctl status mosquitto
sudo mosquitto_passwd -c /etc/mosquitto/.passwd shapehost
cat >auth.conf <<EOF
listener 1883
allow_anonymous false
password_file /etc/mosquitto/.passwd
EOF
sudo mv auth.conf /etc/mosquitto/conf.d/auth.conf
sudo systemctl restart mosquitto

sudo openssl dhparam -out /etc/mosquitto/certs/dhparam.pem 2048
sudo chown -R mosquitto: /etc/mosquitto/certs

cat >ssl.conf <<EOF
listener 8883
certfile /etc/letsencrypt/live/$DOMAINNAME/fullchain.pem
cafile /etc/letsencrypt/live/$DOMAINNAME/chain.pem
keyfile /etc/letsencrypt/live/$DOMAINNAME/privkey.pem
dhparamfile /etc/mosquitto/certs/dhparam.pem
EOF
sudo mv ssl.conf /etc/mosquitto/conf.d/ssl.conf
sudo systemctl restart mosquitto

exit

echo "Set logrotate but not working with Python.logging so use TimedRotatingFileHandler"
cat >openhems <<EOF
/var/log/openhems.log {
  rotate 6
  daily
  compress
  missingok
  notifempty
  delaycompress
  create 640 root $USER
}
/var/log/openhems.error.log {
  rotate 6
  daily
  compress
  missingok
  delaycompress
  create 640 root $USER
}
EOF
sudo mv openhems /etc/logrotate.d/openhems

