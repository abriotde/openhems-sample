Configure nodes
===============

In this page, we will see more in details how to configure each nodes types. Nodes are for all appliances and electric devices which consumes or deliver electricity (active in home automation).

publicpowergrid
---------------

The public power grid : Most of us have one and only one. In this a important field is the contract witch define prices.

solarpanel
----------

The solar panels, but if you have a wind turbine, define it as "solarpanel" should work well.

battery
-------

The battery.

switch
------

This is the standard class for all electrical appliance witch can be switch on and off (pump, car charger, whasing machines... ). 

Differents kinds
~~~~~~~~~~~~~~~~

OpenHEMS allow you to set many level of switch:

* *Basic switch* : This is a switch that HA can't switch on. So OpenHEMS don't. But, with usually a plug, we HA know how much power the device use. So OpenHEMS can guess if the device is on. This is usefull to take into account his "maxPower" for computation of security power to avoid black out. We consider that, if the device is on, it can use his maxPOower quickly.

* *Standard switch* : This is a switch that OpenHEMS can switch. This is activate by the presence of "isOn" parameter. For this switch, you can ask them to start in the dashborad.

* *Automatic switch* : This is switch witch start automatically to keep a sensor value in a margin. OpenHEMS can control them to ensure that. But it can do more, it can use the margin to "store some power". The idea is to go on top in fast energy timeslot and to let it at go down at lowest on starving energy time.


Specifics paramters
~~~~~~~~~~~~~~~~~~~

* *condition* : This is used to set "an appliance to be switched on at the best time until a condition occured". See ::doc:`usage` for details. The condition is a "static Python code". You can use jinja2 code to call getVall() function. This function let us get Home-Assistant value of an entity by id. Example : "{{ getVal('sensor.carcharge') }} < 80" de manière à charger une voiture jusquà 80%

* *isOn* * : This is the HA entity id of the "switch" button that we can test and use. This is not a mandatory field (in this case, this is a *Basic switch*).

* *sensor* : The HA entity id of the sensor witch give a feedback to the switch. Off-course, the is not a mandatory field, if you have a *Standard switch* do not configure it.

* *direction* : If 1, we consider that the sensor grow up when device is on, and go down else (when off). If -1, this is the opposite. Default is true, and all the documentation is writen for it. Consider the opposite if it's -1. NB: For the moment we do not implement a goal to be in the middle with a reverse engine or a variable one.

* *target* : The sensor target as a min and max values. If above, OpenHEMS will stop the device, if under it will start it. 

* *constraints* : A set of constraints to respect. If not respected there is no choice, OpenHEMS act.

  * *maxPower* : The maximum power the appliance can support. If above, stop it.

  * *minPower* : The minimum power the appliance should support. If under, stop it.

  * *minDurationOn* : The minimum duration the appliance should be on. If under, OpenHEMS won't stop it. Usefull if the appliance do not support beeing stoped during startup or to avoid yo-yo effect.

  * *minDurationOff* : The minimum duration the appliance should be off. If under, OpenHEMS won't start it. Usefull if the appliance do not support beeing started while not fully stoped or to avoid yo-yo effect.

  * *maxDurationOn* : The maximum duration the appliance should be on. If above, OpenHEMS will stop it. Usefull to avoid over-heating, or useless over-use.

  * *maxDurationOff* : The maximum duration the appliance should be off. If above, OpenHEMS will start it. Usefull to avoid freezing for example.