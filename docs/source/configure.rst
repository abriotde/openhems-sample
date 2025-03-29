
Configuration
=============

Prerequisites
-------------

* A HomeAssistant server accessible on a web browser (usually on port 8123).

* An OpenHEMS server accessible on a web browser (usually on port 8000).

In this page, we will consider OpenHEMS url to be http://192.168.1.202:8000/. But the IP address can be different in your case. In Home-AssistantOS, it's displayed in url bar of the web browser when you click on "web interface" button on OpenHEMS add-on (in the store).

If you bought the [OpenHEMS server on OpenHomeSystem](https://openhomesystem.com/product/openhems-server/)  and plug it, it should be available from local network on http://192.168.1.202:8123/ and http://192.168.1.202:8000/.

Configure HomeAssistant
-----------------------

Open HomeAssistant on a web browser. If it's first time it will ask you some informations about your house and will create an admin account. Please keep preciously the login/password.
You can find many tutorial on the web, but let's resume it as :


In `Parameters`/`Devices and services` click `Add an integration` and add all the devices you want.


In `Parameters`/`Dashboards`, you can click `Add a Dashboard` to add 2 dashboard.

* `Default Dashboard` to have a complete dashboard with all your devices watever you configured.

* `Dashboard` witch will be the main. In it add a component `web page` and set the url to "http://192.168.1.202:8000/?n=1". This is the OpenHEMS component to schedule devices.

If OpenHEMS is not installed as add-on of Home-AssistantOS, you will need to generate an Home-Assistant long_lived_token in Menu: User profile / Security / long lived token / Create token. Save it preciously, it's like a password for OpenHEMS access.


Configure OpenHEMS with web interface
-------------------------------------

Open the web interface of OpenHEMS (http://192.168.1.202:8000/) and click on "params" menu.  Should be on http://192.168.1.202:8000/params. You will see a form with many fields to fill. Default are usually good enough. To have more informations about fields, see below at paragraph "Configure OpenHEMS with YAML file".
"Strategies" and ""network" must be set and are quite difficult to set. Click on "+" button to see the popup with choices. See paragraph bellow "Configure OpenHEMS with YAML file" to have more informations.


Configure OpenHEMS with YAML file
---------------------------------

OpenHEMS configuration is saved in [YAML](https://en.wikipedia.org/wiki/YAML) file : "config/openhems.yaml". 

You can edit it directly on the server if you have access and you know what you do. Before editing it, think to backup it. In that case, you can use Default YAML configuration, on default/node, there is all available node types and theire configurations.

If you do not set a configuration field on the YAML file or you let it empty on the web UI, it will be fill with default value. Usually it's the best choice. But some must be set. If you set an incorrect value, in can crash OpenHEMS. It's why we recommand to use Web editor, it avoid most errors and did a backup automaticaly.

Default YAML configuration file can be seen on [Github](https://github.com/abriotde/openhems-sample/blob/main/data/openhems_default.yaml).

After editing the configuration, save it and restart OpenHEMS server. 

To restart the server, the easiest way is to unplug/plug the server. Overwise, an advanced way , is to run `systemctl restart openhems.service` on the terminal, or `docker restrat openhems`.

Api
~~~

This section is used to configure access to Home-Assistant API. It's is very important to feel-in it correctly but on Home-AssistantOS, do not fill it.

* *url* : HTTP url for Home-Assistant API. usually it should be http://127.0.0.1:8123/api

* *long_lived_token*: It's a Home-Assistant token (a long password) to generate on Home-Assistant web page : Menu: User profile / Security / long lived token / Create token.

* *ssl_certificate* : A file path to the SSL certificate. For the moment it's not corectly managed

Server
~~~~~~

This informations are very technical. Let it empty if you don't know what to set. Default should be good enough for most.

* *htmlRoot* : "Root location of web server."

* *inDocker* : "True if OpenHEMS run in docker."

* *port* : Web server port for listening.

* *logformat* : Format for log on OpenHEMS # for custom configuration see https://docs.python.org/3/library/logging.html#logrecord-attributes

* *logfile* : "Log file path"

* *loglevel* : "Log level, (critical, error, warning, info, debug)"

* *loopDelay* : Interval beetween 2 OpenHEMS loop in seconds. Less is better for reaction, but use more power.

* *network* : Should be `homeassistant` as it is the only available untill now. There is to `fake` but it's for very special purposes.

* *strategies* : This is a very important choice as it will the way we choice to consume power.Availables are:


Strategies
~~~~~~~~~~

1. *offpeak* : Use it if you want to switch on devices on specific rank hours during the day/night.

2. *swithoff* : Use it if you want to swith on/off some devices at precise time each day.

3. *emhass* : Use it if you have solar-panels. There is lots of optionnal parameters. A limitation is that it can have only two differents price range in the day.

Those parameters are those from config_emhass.yaml from EMHASS project, please refer to the [documentation](https://emhass.readthedocs.io/en/latest/differences.html) incase of doubt.

* *freq* : Frequency when emhass analyzis is done. Must be greater than 'loopDelay' parameter

* *days_to_retrieve* : How many days in history, emhass analyze to guess furur roduction/consumption.

* *method_ts_round* : Method to arroud values

* *delta_forecast* : Delta forecast

* *weather_forecast_method* : Wether forecast method

* *prod_sell_price* : "Price yousell your electricity to public power grid"

* *set_total_pv_sell* : ""

* *lp_solver* : "Algorythm used to solve"

* *lp_solver_path* : "path for the algorythm witch is used to solve"

* *set_nocharge_from_grid* : ""

* *set_nodischarge_to_grid* : ""

* *set_battery_dynamic* : ""

* *battery_dynamic_max* : ""

* *battery_dynamic_min* : ""


Network
~~~~~~~

Here you set your network. This is very important you  update it when you have new devices.

This is a list of "nodes"

For this part, value can be a `recoverable value` notice with an asterisk, in that case the value can be:

* A number if it is a static value that will never change. It can be so if value really never change or it can be a solution if you have no sensor for it.

* A Home-Assistant complete `entity ID` witch you can get on Home-Assistant dashboard. To do so, click on the device line you want to get on the dashboard. You will get a popup window, on top right, click on parameter buttons and copy complete `entity ID` (Click on the icon, will copy it).

Add as many line like bellow for all electrical source. Usually there is the public grid and/or solar panel

* *id* : A name witch can be what you want without special caracters.

* *class* : It is sensor type. 

* *currentPower* * : This is the currrent power delivered

* *maxPower* * : This is the maximum power we can get from that source.

* *minPower* * : This is the minimal power we can get. Usually 0, but it can be negative if it can act as a battery.

* *powerMargin* : This is the margin to maxPower and minPower we should not go above as a security.

* *currentPower* * : This is the currrent power delivered

* *maxPower* * : This is the maximum power we can get from that source.

* *isOn* * : This is the "switch" button that we can test and use.

Localization
~~~~~~~~~~~~

This section contains sensitive informations. We suggest you to set apprioximative informations (Few miles margin should be enough).


* *latitude* : The home lattitude (usefull for solar-panel and wether predictions)

* *longitude* : The home longitude (usefull for solar-panel and wether predictions)

* *altitude* : The home altitude (usefull for solar-panel)

* *timeZone* : Time-Zone : "Your TZ identifier in https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List

* *language* : Language abbreviation ('fr' for french, 'en' to english)



NB: In default YAML configuration file, witch can be seen on [Github](https://github.com/abriotde/openhems-sample/blob/main/data/openhems_default.yaml), there is a default section witch define what can be set precisely under network and strategy field. It can be used sometime but it's difficult 
