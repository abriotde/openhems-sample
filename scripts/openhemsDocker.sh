#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2
# https://wiki.crowncloud.net/index.php?How_to_Install_Python_3_11_on_Debian_11 (3.11.10)
# virtualenv --python="/usr/bin/python2.6" "/path/to/new/virtualenv/"
# https://www.tderflinger.com/using-systemd-to-start-a-python-application-with-virtualenv
# https://hub.docker.com/r/linuxserver/wireguard

source config.sh
source functions.sh
OPENHEMS_LOGPATH=/var/log/openhems

echo "Install OpenHEMS server"
sudo apt install -y anacron wireguard logrotate incron
sudo mkdir -p $OPENHEMS_LOGPATH

sudo docker run -d \
  --name $DOCKER_NAME \
  --privileged \
  --restart=unless-stopped \
  -v $OPENHEMS_PATH/config:/app/config \
  -v $OPENHEMS_LOGPATH:/log \
  -v /data:/opt
  -e TZ=$MY_TIME_ZONE \
  -p 8000:8000 \
  openhomesystem22/openhems:openhems

exit


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

echo "Install VPN"
wg genkey | sudo tee /etc/wireguard/private.key
sudo chmod go= /etc/wireguard/private.key
sudo cat /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key

PRIV_KEY=$(sudo cat /etc/wireguard/client_private_key)
cat >wg0.conf <<EOF
[Interface]
Address = $VPN_IP/24
PrivateKey = $PRIV_KEY
ListenPort = 51820
[Peer]
PublicKey = ok6S9qPigd0Yk1lL+x5sYrGLx6tX2rFiGpzNx+Uo12s=
Endpoint = openproduct.freeboxos.fr:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
sudo mv wg0.conf /etc/wireguard/wg0.conf

exit

echo "Configure logrotate"
cat >openhems <<EOF
/var/log/openhems/openhems.log {
  rotate 6
  daily
  compress
  missingok
  notifempty
  delaycompress
  create 644 root $USER
}
/var/log/openhems/service.log {
  rotate 6
  daily
  compress
  missingok
  notifempty
  delaycompress
  create 644 root $USER
}
/var/log/openhems/service.error.log {
  rotate 6
  daily
  compress
  missingok
  delaycompress
  create 644 root $USER
}
EOF
sudo mv openhems /etc/logrotate.d/openhems
sudo ln -s /lib/systemd/system/logrotate.service /etc/systemd/system/multi-user.target.wants/
activate_service logrotate

# Venv
sudo apt install libffi-dev


