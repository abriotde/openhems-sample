
https://developers.home-assistant.io/docs/development_environment

https://hacs.xyz/docs/setup/download/


# Install
- https://www.home-assistant.io/installation/linux
- SystemD :  /usr/lib/systemd/system/homeassistant.service
- Get long_lived_token: Home-Assistant => User profile / Security / long lived token / Create token
- EMHASS : 
	- Version Add-on: https://github.com/davidusb-geek/emhass-add-on
	- https://github.com/davidusb-geek/emhass
- HACS (Tempo) : Need Github account + RTE API account
	- https://hacs.xyz/docs/setup/download/
	- https://www.antoineguilbert.fr/installer-configurer-hacs-sur-home-assistant/
	- https://www.domo-blog.fr/comment-installer-hacs-home-assistant-store-integrations-custom-ha/
- API Tempo
	- https://www.antoineguilbert.fr/afficher-infos-abonnement-tempo-edf-home-assistant/
	- wget "https://api-commerce.edf.fr/commerce/activet/v1/calendrier-jours-effacement?option=TEMPO&dateApplicationBorneInf=2023-5-18&dateApplicationBorneSup=2024-5-18&identifiantConsommateur=src"
- reverse-proxy HTTPS: https://www.scaleway.com/en/docs/tutorials/nginx-reverse-proxy/
	- 

# MQTT

https://www.home-assistant.io/integrations/python_script/

$ sudo apt install python3-paho-mqtt

# Banana Pi M2 Berry
- Install: https://sd-card-images.johang.se/boards/banana_pi_m2_berry.html

# EMHASS
- docker run -it --restart always -p 5000:5000 -e LOCAL_COSTFUN="profit" -v $(pwd)/config_emhass.yaml:/app/config_emhass.yaml -v $(pwd)/secrets_emhass.yaml:/app/secrets_emhass.yaml --name DockerEMHASS <REPOSITORY:TAG>
- docker run -it --restart always -p 5000:5000 -e LOCAL_COSTFUN="profit" -v $(pwd)/config_emhass.yaml:/app/config_emhass.yaml -v $(pwd)/data:/app/data  -v $(pwd)/secrets_emhass.yaml:/app/secrets_emhass.yaml --name DockerEMHASS <REPOSITORY:TAG>
