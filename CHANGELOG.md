# Changelog

## 0.2.12 - 2025-06-12
### Improvement
- Separate feedbackSwitch

### Fix
- Catch all errors on server loop to avoid crash the thread.
- when started manually a switch, there was no call to decrementTime

## 0.2.11 - 2025-05-21
### Improvement
- ADD Notify loop errors on dashboard.

## 0.2.10 - 2025-04-26
### Improvement
- MOD readme : To catch attention, add screenshot + install insstructions
- ADD Switch witch are not switchable by home automation : It allow reduce margin because we can count heavy consumer that are not switchable to avoid black-out (on off-peak time-slots).
- ADD Sqlite3 DB to record/analyze behavior of switch : guess characteristics.
- ADD FeedbackSwitch with a modelization by polynomial regression

## 0.2.9 - 2025-04-18
## FIX
- MOD Avoid import sko.GA (witch need pip) when not used (not using annealing strategy)

### Improvement
- ADD web page to get basic informations : The most important is 'version'
- ADD automatic switch : switch on when you can until X occured.
- MOD readme : add white_check_mark.
- ADD web tooltips on dynamic popup (for nodes/strategies) and update translations

## 0.2.8 - 2025-04-15
### Fix
- FIX strategy/annealing : Use genetic algorythm for more reliable results.
- FIX node/solarpanel :  add tests on it and complete class attributes.

### Improvement
- ADD dev : manage time by event subsuscription : registerDecrementTime
- MOD strategy/solarnosell : Add some more complex parameters for finer configuration.
- MOD doc : ADD autogeneration of docstring
- MOD doc : Update configure/usage
- MOD test : Improve

## 0.2.7 - 2025-04-07
### Fix
- FIX Home-Assistant addon, create /etc/openhems/openhems.yaml (config file) if not exists.

## 0.2.6 - 2025-04-07
To fix Home-Assistant addon, must upgrade version for so few.

### Fix
- FIX Start even if CastException or over at init.

## 0.2.5 - 2025-04-06
To fix Home-Assistant addon, must upgrade version for so few.

### Fix
- FIX Start even if the classname is missing or miss configured.

## 0.2.4 - 2025-04-05
### Fix
- FIX web /params UI for editing configuration
- FIX : Start even if a critical parameter of a node fail to get values.
- FIX : Start even if logfile is unknown or Home-Assistant API unavailable.

## 0.2.3 - 2025-04-03
Want to extends possibilities. For the moment it do not run ok, but write down main ideas and try to determine main usable strategies.

### Improvement
- ADD SolarNoSellStrategy
- ADD SimulatedAnnealing Strategy (do not work)
- ADD first notions of variable device
- Factorize code for strategy using an algo running not at each cycle : emhass & annealing
- Update documentation

## 0.2.2 - 2025-04-01
### Fix
- FIX security against over-load problems + add devices deactivation to avoid ping-pong effect.

### Improvement
- ADD multi hours-ranges for contract. Before we have only 2 : peak-hours and off-peak.
- ADD priority notion for devices.
- Improve test_server.py with multi-cycle and test security against over-load.

## 0.2.1 - 2025-03-27
### Fix
- FIX docker stability
- FIX integration for Home-Assisant.

### Improvement
- Update Documentation

## 0.2.0 - 2025-03-24
### Fix
- Configuration UI : It was broken since the possibility to have multiple strategies. It was not very stable even before.
- Emhass : it was broken too since multi-strategies
- Improve autostart with systemd while running OpenHEMS on separate docker (Not in HAOS).
- Bug, not decreasing device duration, fixed.

### Improvement
- ADD call to a web API to get RTE Tempo color

### Todo
- Improve stability of
- Update documentations

## 0.1.14 - 2025-02-20
### Fix
- Fix pip package usage : Add necessary datas and correct paths. The goal is to create Home-Assistant integration.

## 0.1.13 - 2025-02-20

## 0.1.12 - 2025-02-20

## 0.1.11 - 2025-02-20

## 0.1.10 - 2025-02-20

## 0.1.9 - 2025-02-19
### Improvement
- Publish openhems as PIP package (Same version). The goal is put it in Home-Assistant's addon.
- Lots of work done on website and hardware study but not on openhems-sample.

### Fix
- Github action python-publish.yml

## 0.1.8 - 2025-01-29
### Improvement
- ADD strategy : Use timeout on scheduled devices to respect constraints
- MOD doc : Add usage documentation
- MOD contract : API to get current pricing and in futur

### Fix

### TODO
- Use internet to get Tempo color instead of HA plugin

## 0.1.7 - 2025-01-03
### Improvement
- MOD : Multi-strategy
- MOD : Add SwitchOffStrategy with extra conditions.

### Fix
- Improve logs with Docker

### TODO
- Update UI YAML edition

## 0.1.6 - 2025-01-03
### Improvement
- MOD log for docker on stdout
- MOD : some more log.

### Fix
- FIX cast_utility.toTypeInt("0.0") crash

## 0.1.5 - 2024-12-10
### Improvement
- ADD IHM for editing YAML configuration
- ADD resilience on error: Start anyway Web server and display errors and configuration screen to fix them.
- UPDATE documentation
- ADD some translation system.
- MOD configuration : Create localization "header" for place/hours/language.

## 0.1.4 - 2024-11-18
### Improvement
- ADD Auto-génération of Emhass yaml configuration => Avoid problems
- ADD notion of Contract to manage peak-hours "dynamically".
- MOD ConfigurationManager : get sub-dict of sub-configurations
- UPDATE Emhass

### Fix
- FIX Install OpenHEMS as docker (And command VPN)
- FIX Pipelines

## 0.1.3 - 2024-11-18
### Improvement
- Aplication as a Docker

### Fix
- FIX and stabilize Emhass

## 0.1.2 - 2024-10-11
### Improvement
- EmhassStrategy
- Fatorize code
- Changelog

## 0.1.1 - 2024-10-04
### Improvement
- Ehmass POC
- Tests (FakeNetworkUpdater)
- Pipelines => Pylint, Codecov, pip
- Documentation on readthedoc
### Fix
- HomeAssistantStrategy
- Pipelines : Pylint + Codecov => Improve code reliability and lisibility

## 0.1.0 - 2024-08-25
### Improvement
- HomeAssistantStrategy
- Loging system with logrotate
- Install scripts
- Auto-Upgrade system
