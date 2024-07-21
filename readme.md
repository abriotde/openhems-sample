# Presentation

This software is an Open-Source Home Energy Management System based on [Home-Assistant](https://www.home-assistant.io/) installation. It all run locally witch is good for privacy and is customizable.

This software is usefull to get an as smart as possible management of power consumption and production. This should lead to cost reduction. 

- If you have a solar panel with battery, it will allow you to have smaller battery (witch is the most expensive part).

- If you have a public power grid source with variable cost, it will allow you to consume when it's lower cost.

Warning : This software is under activ developpment but not functionally.
All contribution to the software are welcome. Please contact alberic.delacrochais@protonmail.com for all questions.

# Prerequisites

* Controlable power consuption: 
 - devices witch start on plug like electrique car
 - connected devices like washing-machine.

* A server we named "homeassistant" installed with debian based Linux OS connected to local lan. The script scripts/home-assistant.sh let you to install Home-Assistant. But if you have already a Home-Assistant install use it
 - Python3 tested on 3.9
 - Systemd older than v240

* In your internet box
 - Create a domain name that we named $DOMAINNAME.
 - Redirect ports 80 and 443 to your homeassistant server.
 - See configuration of your DHCP and choose a free IP outside it range (and free from other static local IP). Default is 192.168.1.202. Maybe is it free too for you.

# Install

* git clone https://github.com/abriotde/openhems-sample.git
* cd openhems-sample/scripts/
* Edit config.sh and adapt DOMAINNAME and HOMEASSISTANT_IP to your choices.
* ./home-assistant.sh
* Check in a browser "http://192.168.1.202/" after replacing 192.168.1.202 with your IP. If ok, home-assistant is correctly installed.
* Check in a browser "https://192.168.1.202/" after replacing 192.168.1.202 with your IP. If ok, HTTPS is correctly installed
* Check in a browser "https://your.domain.com/" If ok, all the base is ok.
* You can continue and configure your home in a browser.
* HACS
 - Parametre/Ajouter une intégration/HACS... Must add a hacs menu
* Tempo
 - Menu HACS/Menu parametre (top right)/Dépot personalisé (Dépot:https://github.com/hekmon/rtetempo, Catégorie:Intégration)
 - Menu HACS/search "Rte Tempo"/Rte Tempo/Télécharger
 - Parametre/Ajouter une intégration/Rte Tempo...
 
* Get "long_lived_token": Home-Assistant => User profile / Security / long lived token / Create token

- EMHASS :
	- Version Add-on: https://github.com/davidusb-geek/emhass-add-on
	- https://github.com/davidusb-geek/emhass
- HACS (Tempo) : Need Github account + RTE API account
	- https://www.antoineguilbert.fr/installer-configurer-hacs-sur-home-assistant/
	- https://www.domo-blog.fr/comment-installer-hacs-home-assistant-store-integrations-custom-ha/
- API Tempo
	- https://www.antoineguilbert.fr/afficher-infos-abonnement-tempo-edf-home-assistant/
	- wget "https://api-commerce.edf.fr/commerce/activet/v1/calendrier-jours-effacement?option=TEMPO&dateApplicationBorneInf=2023-5-18&dateApplicationBorneSup=2024-5-18&identifiantConsommateur=src"
- reverse-proxy HTTPS: https://www.scaleway.com/en/docs/tutorials/nginx-reverse-proxy/

# Post-install

* In your internet box stop redirect 80 port to your homeassistant server.

# MQTT

https://www.home-assistant.io/integrations/python_script/

$ sudo apt install python3-paho-mqtt

# Banana Pi M2 Berry
- Install: https://sd-card-images.johang.se/boards/banana_pi_m2_berry.html

# EMHASS
- docker run -it --restart always -p 5000:5000 -e LOCAL_COSTFUN="profit" -v $(pwd)/config_emhass.yaml:/app/config_emhass.yaml -v $(pwd)/secrets_emhass.yaml:/app/secrets_emhass.yaml --name DockerEMHASS <REPOSITORY:TAG>
- docker run -it --restart always -p 5000:5000 -e LOCAL_COSTFUN="profit" -v $(pwd)/config_emhass.yaml:/app/config_emhass.yaml -v $(pwd)/data:/app/data  -v $(pwd)/secrets_emhass.yaml:/app/secrets_emhass.yaml --name DockerEMHASS <REPOSITORY:TAG>

# usefull documntations

- https://developers.home-assistant.io/docs/development_environment
- https://www.home-assistant.io/installation/linux


