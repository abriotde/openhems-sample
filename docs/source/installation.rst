
Installation
============


There is 3 main way to install OpenHEMS server. See chapters below, classed by dificulty. Once the server is installed, please see :doc:`configure` page to configure it.

Buy it
------

You can bye a pre-installed system on [OpenHEMS server on OpenHomeSystem](https://openhomesystem.com/product/openhems-server/).
Then plug theelectric power cable and the ethenet one. It should be available from local network on http://192.168.1.202:8123/ and http://192.168.1.202:8000/.

From docker
-----------

This is a modern, quick and secure way to install it but there is less customizations way (creating your own Dockerfile from it ?).

Prerequisites
~~~~~~~~~~~~~

* A Linux server

* Home-Assistant installed. You can [install](https://www.home-assistant.io/installation/linux) it as docker too. NB: We recommand to install it on the same server as OpenHEMS but it is not mandatory.


Installation
~~~~~~~~~~~~


You need 3 parameters :

* $OPENHEMS_CONFIGPATH : A folder to store openhems.yaml configuration file.

* $OPENHEMS_LOGPATH : A folder to store logs.

* $MY_TIME_ZONE : find your time-zone

Replace them in the command lne below and run it.

On a Linux server run :

.. code-block:: bash

 docker run -d \
 	--name openhems \
 	--privileged \
 	--restart=unless-stopped \
 	-v $OPENHEMS_CONFIGPATH:/app/config \
 	-v $OPENHEMS_LOGPATH:/log \
 	-v /data:/opt \
 	-e TZ=$MY_TIME_ZONE \
 	-p 8000:8000 \
 	ghcr.io/abriotde/openhems-sample:main

From scratch
------------

This way is reserved to aknowledged people. See dedicated page :doc:`installation_from_scratch`.

