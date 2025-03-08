
source config.sh
source functions.sh
OPENHEMS_LOGPATH=/var/log/openhems

# Useless ?
function installMosquitto {
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
}

# https://hub.docker.com/r/linuxserver/wireguard
function installVPN {
	echo "Install VPN"
	sudo apt install -y wireguard
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
}

function installLogrotate {
	sudo apt install -y logrotate
	sudo mkdir -p $OPENHEMS_LOGPATH
	echo "Configure logrotate"
	cat >openhems <<EOF
$OPENHEMS_LOGPATH/openhems.log {
  rotate 6
  daily
  compress
  missingok
  notifempty
  delaycompress
  create 644 root $USER
}
$OPENHEMS_LOGPATH/service.log {
  rotate 6
  daily
  compress
  missingok
  notifempty
  delaycompress
  create 644 root $USER
}
$OPENHEMS_LOGPATH/service.error.log {
  rotate 6
  daily
  compress
  missingok
  delaycompress
  create 644 root $USER
}
EOF
	sudo mv openhems /etc/logrotate.d/openhems
	activate_service logrotate.service
}

function installAutoupdate {
	cat >openhems-update <<EOF
#!/bin/bash
cd /home/olimex/openhems-sample/scripts
/home/olimex/openhems-sample/scripts/openhems.sh update
EOF
	chmod +x openhems-update
	sudo mv openhems-update /etc/cron.weekly/openhems-update
}
