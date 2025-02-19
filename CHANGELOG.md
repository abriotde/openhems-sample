# Changelog

## 0.1.9 - 2024-02-19
### Improvement
- Publish openhems as PIP package (Same version). The goal is put it in Home-Assistant's addon.
- Lots of work done on website and hardware study but not on openhems-sample.

### Fix
- Github action python-publish.yml

## 0.1.8 - 2024-01-29
### Improvement
- ADD strategy : Use timeout on scheduled devices to respect constraints
- MOD doc : Add usage documentation
- MOD contract : API to get current pricing and in futur

### Fix

### TODO
- Use internet to get Tempo color instead of HA plugin

## 0.1.7 - 2024-01-03
### Improvement
- MOD : Multi-strategy
- MOD : Add SwitchOffStrategy with extra conditions.

### Fix
- Improve logs with Docker

### TODO
- Update UI YAML edition

## 0.1.6 - 2024-01-03
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
