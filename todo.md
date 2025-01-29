# Administration
- Contact installer
- Open Home Fundation https://www.openhomefoundation.org/ ?

# Development
- funding/crowd : kickstarter
- promote : LinuxFR
- prod/mvp : Minimum Valuable Product
- dev/strategy : use timeout to stay alife
- dev/general : Improve resilience : When fail get global status at init time wait and retry
- dev/ihm : Improve edit Yaml configuration whith HTML : Check pb openhems.yaml.20241226: save without diff for nodes + node_id
- dev/admin : Run openhems as user 'openhems' instead root, use 
- dev/updater : Add HomeStateUpdater from openhab_api.py
- dev/strategy : Add solar panel without internet, use Python skyfield module or pvlib module
- dev/datas : Script to get EDF datas.
- dev/schedule : Set available schedule by power (Kwh) instead of time.
- dev/maintenance Add remote SSH maintenance (on 'dev')
- dev/admin : PyPi : https://pypi.org/project/emhass/
- dev/schedule : Gestion des Kw consommés dans le but de facturer au Kw
- dev/admin : configure HTML root for proxy.
- dev/schedule/automatic : For devices with a sensor witch give a value to maintain in a range goal (VMC, water heater, freezer, heater) => need to introduce an emergency notion && an average frequency
- dev/rust : re-implement it as Rust
- dev/maintenance : Package Python app as runable without venv : Nuitka or UV, cf branch "packaging"
- dev/api : Use internet to get Tempo color instead of HA plugin (web or develop a custom openhomesystem api)
