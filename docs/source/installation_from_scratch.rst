
Installation from scratch
=========================

Prerequisites
-------------

We need:

* A server we named "homeassistant" installed with debian based Linux OS (Or HomeAssistantOS) connected to local lan. The script scripts/home-assistant.sh let you to install Home-Assistant. But if you have already a Home-Assistant installed use it.

 * Python3, tested on 3.9, 3.10 for Emhass
 * Systemd older than v240

* In your internet box

 * Create a domain name that we named $DOMAINNAME.
 * Redirect ports 80 and 443 to your homeassistant server.
 * See configuration of your DHCP and choose a free IP outside it range (and free from other static local IP). Default is 192.168.1.202. Maybe is it free too for you.

Installation
------------

* Run `git clone https://github.com/abriotde/openhems-sample.git`
* Run `cd openhems-sample/scripts/`
* Edit config.sh and adapt it:

 * DOMAINNAME : The domain name you have from internet to access your server. It is usually configurable in the internet box.
 * HOMEASSISTANT_IP : This is the local IP (If ever one set static, keep it). You must check it's a free IP in your internet box not in DHCP rank.
 * HOMEASSISTANT_DIR : An empty directory where you will install HomeAssistant. If you run HomeAssistantOS, it is the place where it is install but it should be useless
 * HOMEASSISTANT_CONFIG_PATH : The Home-Assistant path for configuration (You probably do not need to change it)
 * DOCKER_NAME : The name of the docker HomeAssistant. I do not think you need to change it.
 * OPENHEMS_PATH : The place you did the "git clone"
 
* Run `./installFromScratch.sh` or just `./openhems.sh` if you have ever HomeAssistant installed with HACS
* Check in a web browser "http://$HOMEASSISTANT_IP:8123/" after replacing $HOMEASSISTANT_IP with your IP. If ok, home-assistant is correctly installed.
* Check in a web browser "https://$HOMEASSISTANT_IP/" after replacing $HOMEASSISTANT_IP with your IP. If ok, HTTPS is correctly installed
* Check in a web browser "https://your.domain.com/" If ok, all the base is ok.
* Check in a browser "https://$HOMEASSISTANT_IP:8000/" to check if OpenHEMS server run well

If something went wrong, you will need to search where in the script and to correct it. Then run the script from the place it went wrong. You can send us a mail to contribute or send a merge-request.
Else, you can continue and configure your home in a web browser.

* In HACS menu

 * Parametres/Add a integration/HACS... Must add a hacs menu

* Tempo

 * Menu HACS/Menu parametre (top right)/Dépot personalisé (Dépot:https://github.com/hekmon/rtetempo, Catégorie:Intégration)
 * Menu HACS/search "Rte Tempo"/Rte Tempo/Télécharger
 * Parametre/Ajouter une intégration/Rte Tempo...

* Get `long_lived_token`: Home-Assistant => User profile / Security / long lived token / Create token. Copy it and save it, we will need it.

# Configure

Now you installed HomeAssistant and OpenHEMS but they do not comunicate each over. You have to configure OpenHEMS to give it access to HomeAssistant.

* Edit the `$OPENHEMS_PATH/configi/openhems.yaml` file. You will change `api` block for the moment:

 * url : The url for OpenHEMS to access to HomeAssistant. You probably have to change the IP, but as it's from localhost, 127.0.0.1 should be ok.
 * long_lived_token : The `long_lived_token` you get the step before. It's like a password to give access to HomeAssistant for OpenHEMS
 * ssl_certificate : It seam not working for the moment.

* Run `sudo systemctl restart openhems.service` to restart OpenHEMS. You should see a notification in HomeAssistant that tell you OpenHEMS started.

Now you can follow `doc/configure.md` to really configure your network.

# Plugin installation documentations

* EMHASS

 * Version Add-on: https://github.com/davidusb-geek/emhass-add-on
 * https://github.com/davidusb-geek/emhass

* HACS (Tempo) : Need Github account + RTE API account

 * https://www.antoineguilbert.fr/installer-configurer-hacs-sur-home-assistant/
 * https://www.domo-blog.fr/comment-installer-hacs-home-assistant-store-integrations-custom-ha/

* Tempo API

 * https://www.antoineguilbert.fr/afficher-infos-abonnement-tempo-edf-home-assistant/
 * wget "https://api-commerce.edf.fr/commerce/activet/v1/calendrier-jours-effacement?option=TEMPO&dateApplicationBorneInf=2023-5-18&dateApplicationBorneSup=2024-5-18&identifiantConsommateur=src"

* reverse-proxy HTTPS: https://www.scaleway.com/en/docs/tutorials/nginx-reverse-proxy/

Post-installation
-----------------

* In your internet box stop redirect 80 port to your homeassistant server.

1. MQTT

https://www.home-assistant.io/integrations/python_script/

$ sudo apt install python3-paho-mqtt

2. Banana Pi M2 Berry

* Install: https://sd-card-images.johang.se/boards/banana_pi_m2_berry.html

3. EMHASS

Usefull documentations
----------------------

* https://developers.home-assistant.io/docs/development_environment
* https://www.home-assistant.io/installation/linux


