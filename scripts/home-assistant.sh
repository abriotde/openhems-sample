#!/bin/bash

source config.sh


sudo apt update
sudo apt upgrade -y

echo "Change default password"
passwd
hostname -I

echo "Set static IP"
cat >eth0  <<EOF
auto eth0
iface eth0 inet static
  address $HOMEASSISTANT_IP
  netmask 255.255.255.0
  gateway `ip route|head -1|awk '{print $3}'`
  dns-nameservers 4.4.4.4
  dns-nameservers 8.8.8.8
EOF
sudo mv /etc/network/interfaces.d/eth0 /etc/network/eth0.old
sudo mv eth0 /etc/network/interfaces.d/eth0

echo "Install docker"
# https://docs.docker.com/engine/install/ubuntu/
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
# Add $USER to docker group
sudo groupadd docker
sudo usermod -aG docker $USER
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Run Home-Assistant"
mkdir -p $HOMEASSISTANT_DIR
mkdir -p $HOMEASSISTANT_CONFIG_PATH
sudo docker run -d \
  --name $DOCKER_NAME \
  --privileged \
  --restart=unless-stopped \
  -e TZ=MY_TIME_ZONE \
  -v $HOMEASSISTANT_DIR/config:/config \
  -v /run/dbus:/run/dbus:ro \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable

cp ../config/dashboards.yaml ../config/configuration.yaml $HOMEASSISTANT_CONFIG_PATH


echo "Install HACS"
# https://hacs.xyz/docs/setup/download/
mkdir -p $HOMEASSISTANT_CONFIG_PATH/custom_components
cd $HOMEASSISTANT_CONFIG_PATH
wget -O - https://get.hacs.xyz | bash -

docker stop homeassistant
docker start homeassistant

echo "Install HTTPS : reverse-proxy NginX"
# sudo add-apt-repository ppa:certbot/certbot
# sudo apt update
sudo apt install -y nginx software-properties-common python3-certbot-nginx
sudo certbot --nginx
cat >reverse-proxy-ssl.conf <<EOF
map $http_upgrade $connection_upgrade {  
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

exit

docker exec -it $DOCKER_NAME  bash

exit

echo "Set static IP"
cat >01-network-manager-all.yaml  <<EOF
network:
 version: 2
 renderer: NetworkManager
 ethernets:
   eth0:
     dhcp4: no
     addresses: [$HOMEASSISTANT_IP/20]
     gateway4: `ip route|head -1|awk '{print $3}'`
     nameservers:
         addresses: [8.8.8.8,8.8.8.4]
EOF
sudo mv 01-network-manager-all.yaml /etc/netplan/01-network-manager-all.yaml

