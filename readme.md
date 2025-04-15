
.. raw:: html
  <div align="center">
    <br>
    <img alt="OpenHomeSystem" src="https://openhomesystem.com/wp-content/uploads/2024/10/cropped-logo_openhomesystem_100.png">
    <h1>OpenHEMS</h1>
    <strong>A simple Home Energy Management System</strong>
  </div>
  
  <br>
  
  <p align="center">
    <a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample/releases">
      <img alt="GitHub release (latest by date)" src="https://img.shields.io/github/v/release/abriotde/openhems-sample">
    </a>
    <a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample/actions">
      <img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/abriotde/openhems-sample/python-test.yml?branch=main">
    </a>
    <a hstyle="text-decoration:none" ref="https://codecov.io/github/abriotde/openhems-sample" >
      <img src="https://codecov.io/github/abriotde/openhems-sample/branch/main/graph/badge.svg?token=4Y5ANTFLW7"/>
    </a>
    <a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample/blob/main/LICENSE">
      <img alt="GitHub" src="https://img.shields.io/github/license/abriotde/openhems-sample">
    </a>
    <!-- a style="text-decoration:none" href="https://pypi.org/project/openhems-sample/">
      <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/openhems-sample">
    </a>
    <a style="text-decoration:none" href="https://pypi.org/project/openhems/">
      <img alt="PyPI - Status" src="https://img.shields.io/pypi/status/openhems">
    </a -->
    <a style="text-decoration:none" href="https://openhems.readthedocs.io/en/latest/">
      <img alt="Read the Docs" src="https://img.shields.io/readthedocs/openhems-sample">
    </a>
  </p>
  
  <div align="center">
    <a style="text-decoration:none" href="https://openhems.readthedocs.io/en/latest/">
        <img src="https://raw.githubusercontent.com/abriotde/openhems-sample/main/docs/images/Documentation_button.svg" alt="Documentation">
    </a>
    <a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample/discussions">
        <img src="https://raw.githubusercontent.com/abriotde/openhems-sample/main/docs/images/Community_button.svg" alt="Community">
    </a>
    <a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample/issues">
        <img src="https://raw.githubusercontent.com/abriotde/openhems-sample/main/docs/images/Issues_button.svg" alt="Issues">
    </a>
    <!-- a style="text-decoration:none" href="https://github.com/abriotde/openhems-sample-add-on">
       <img src="https://raw.githubusercontent.com/abriotde/openhems-sample/main/docs/images/EMHASS_Add_on_button.svg" alt="OpenHEMS Add-on">
    </a -->
  </div>
  
  <br>
  
  <p align="center">
  If you like this work please consider buying a coffee ;-) 
  </p>
  <p align="center">
    <a href="https://buymeacoffee.com/openhomesystem" target="_blank">
      <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" >
    </a>
  </p>


Presentation
============

This software is an Open-Source Home Energy Management System based on [Home-Assistant](https://www.home-assistant.io/) installation. It all run locally witch is good for privacy and is customizable.
A packaged product, is avalable on https://openhomesystem.com/product/openhems-server/

This software is usefull to get an as smart as possible management of power consumption and production. This should lead to cost reduction. 

* If you have a solar panel with battery, it will allow you to have smaller battery (witch is the most expensive part).

* If you have a public power grid source with variable cost, it will allow you to consume when it's lower cost.

Warning : This software is under activ developpment and is used on production but remain at early developpment.
All contribution to the software are welcome. Please contact contact@openhomesystem.com for any questions.


Features
========

:white_check_mark: Easy installation and UI configuration with HTML pages\
:white_check_mark: Support multiple off-peak time-slots and even variable time-slots and cost (RTE Tempo contract).\
:white_check_mark: Usefull if you don't have solar panel but only a contract with off-peak.\
:white_check_mark: Solar panel management with EMHASS using AI\
:white_check_mark: Basic solar panel management without AI for no sell or no buy strategy.\
:white_check_mark: Home-Assistant widget to schedule devices (washing-machine, charging car... )\
:white_check_mark: Time-out for scheduled devices.\
:white_check_mark: Configurable priority handling between multiple appliances\
:white_check_mark: Define an *On/Off switch interval* / solar power averaging interval\
:white_check_mark: Always check maximum capacities to avoid black-out\
:white_check_mark: Supports one- and three-phase appliances\
:white_check_mark: Supports *Only-Switch-On* devices (like washing machines, dishwashers)\

We are expected to add soon the following features. We need beta-tester for those features. If you are interested, please contact us.

:x: Variable switch support (like solar router, car charger)\
:x: Works with hybrid and standard inverters\

What OpenHEMS is not.

:warning: It will never guarantee a reaction time due to the performance of the home automation network and OpenHEMS (the worst is WiFi).\
:warning: Due to the licence, we do not garentee there is no bugs or problems. For garentee like this please contact us for a comercial support.\

Prerequisites
=============

* Controlable devices:

  * devices witch start on plug like electric-car or old washing machine.

  * connected devices like washing-machine.

* Advantages to delay some consumption. Depending on your electric source (Contract with offpeak hours, solar panels).

* A Linux based server, connected to home network, with a recent Python installation.

* And some software skills...

* More prerequisites, for installation are detailed on installation's documentation.

Install this software
=====================

See the [documentation](https://openhems.readthedocs.io/en/latest/installation.html)

There is a video, in French, to explain how to configure OpenHEMS on [Youtube](https://www.youtube.com/watch?v=1rb9n-XyTsM)

Configure
=========

See the [documentation](https://openhems.readthedocs.io/en/latest/configure.html)

usefull documentation
=====================

- https://developers.home-assistant.io/docs/development_environment
- https://www.home-assistant.io/installation/linux
- https://emhass.readthedocs.io/en/latest/
