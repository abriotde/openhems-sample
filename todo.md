# Administration
- Contact installer
- Open Home Fundation https://www.openhomefoundation.org/ ?
- funding/crowd : kickstarter
- promote : LinuxFR

# Integration
- IA to command OpenHEMS devices ("Start the washing machine") & as "Personnal Assistant"

# Development
- dev/publicpowergrid : Add variable maximum power consumption for time-slots.
- dev/updater : Add HomeStateUpdater from OpenHAB, Jeedom, Domoticz.
- dev/strategy : Add solar panel without internet, use Python skyfield module or pvlib module
- dev/datas : Script to get EDF datas
- dev/schedule : Set available schedule by power (Kwh) instead of time.
- dev/maintenance Add remote SSH maintenance (on 'dev')
- dev/admin : PyPi : https://pypi.org/project/emhass/
- dev/schedule : Gestion des Kw consommés dans le but de facturer au Kw
- dev/admin : configure HTML root for proxy.
- dev/schedule/automatic : For devices with a sensor witch give a value to maintain in a range goal (VMC, water heater, freezer, heater) => need to introduce an emergency notion && an average frequency
- dev/rust : re-implement it as Rust or Go? Warning for IA...
- dev/maintenance : Package Python app as runable without venv : Nuitka or UV, cf branch "packaging"
- dev/admin : Run openhems as user 'openhems' instead root

# To Check
- Works with hybrid and standard inverters
