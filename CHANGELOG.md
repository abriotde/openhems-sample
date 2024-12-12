# Changelog

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
