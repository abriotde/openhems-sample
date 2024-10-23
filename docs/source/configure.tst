# Prerequisites

* HomeAssistant server accessible on a web browser. If you bought the [OpenHEMS server on OpenHomeSystem](https://openhomesystem.com/product/openhems-server/)  and plug it, it should be available from local network on http://192.168.1.202:8123/
* Access to edit OpenHEMS configuration on OpenHEMS server. The simplest way is to use a sftp client like FileZilla available on Windows and Linux. With this you can copy file from the server to your PC, edit it with your favorite editor (Like Notepad++ on Windows or Gedit on Linux) and then push it back on the server.

# Configure HomeAssistant
Open HomeAssistant on a web browser. If it's first time it will ask you some informations about your house and will create an admin account. Please keep preciously the login/password.

In `Parameters`/`Devices and services` click `Add an integration` and add all the devices you want.
In `Parameters`/`Dashboards`, you can click `Add a Dashboard` to add 2 dashboard.
1. `Default Dashboard` to have a complete dashboard with all your devices watever you configured.
* `Web page` and enter the same url but with ":800" at end like "http://192.168.1.202:8000/". This is the OpenHEMS dashboard.


# Configure OpenHEMS
Keep the web browser on HomeAssistant default dashboard.
And get on OpenHEMS server the file openhems-sample/config/openhems.yaml. It's a YAML file you must respect the format. It is not complicated to undertand bu it doesn't like unexpected space or tabulation.
Before editing it, backup it.

Edit `server:`  block and set the values:
* loop_delay : This is the delay, in seconds, between 2 cycles of OpenHEMS check. Less it is best is the reaction but it will consumme more power.
* network : Musk be `homeassistant` as it is the only available untill now.
* strategy : This is a very important choice as it will the way we choice to consume power. Availables are:
1. `offpeak` : Use it if you want to switch on devices on specific rank hours during the day/night.

Edit `network:` block. For this part, value can be a `recoverable value` notice with an asterisk, in that case the value can be:
* A number if it is a static value that will never change. It can be so if value really never change or it can be a solution if you have no sensor for it.
* A Home-Assistant complete `entity ID` witch you can get on Home-Assistant dashboard. To do so, click on the device line you want to get on the dashboard. You will get a popup window, on top right, click on parameter buttons and copy complete `entity ID` (Click on the icon, will copy it).

First edit `in:` and add as many line like bellow for all electrical source. Usually there is the public grid and/or solar panel
1. `id` : A name witch can be what you want without special caracters.
2. `currentPower`* : This is the currrent power delivered
3. `maxPower`* : This is the maximum power we can get from that source.
4. `minPower`* : This is the minimal power we can get. Usually 0, but it can be negative if it can act as a battery.
3. `powerMargin` : This is the margin to maxPower and minPower we should not go above as a security.

* Then edit `out:`. Each line correspond to a device.
1. `id` : A name witch can be what you want without special caracters.
2. `class` : Sensor type. Today just `switch` are available, but soon we will have `variator` when it can can be controlable power consumption or `cycle` when there is a user choice between few cycle.
2. `current_power`* : This is the currrent power delivered
3. `max_power`* : This is the maximum power we can get from that source.
4. `is_on`* : This is the "switch" button that we can test and use.

Save the configuration, put it on server and restart OpenHEMS server. 
To restart the server, you can run `sudo systemctl restart openhems.service` on the terminal or overwise switch off/switch on it.

