#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

source config.sh

# sudo hwclock --hctosys
# sudo date --set "15 Jul 2024 22:55:00"
sudo apt install ntp ntpdate
sudo dpkg-reconfigure tzdata
sudo ntpdate ntp.ubuntu.com
sudo apt update
sudo apt upgrade -y

echo "Change default password"
passwd
hostname -I

echo "Change hostname"
sudo echo "openhems" > /etc/hostname

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

