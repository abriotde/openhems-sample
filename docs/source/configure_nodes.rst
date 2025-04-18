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

* *condition* : This is used to set "an appliance to be switched on at the best time until a condition occured". See ::doc:`usage` for details. The condition is a "static Python code". You can use jinja2 code to call getVall() function. This function let us get Home-Assistant value of an entity by id. Example : "{{ getVal('sensor.carcharge') }} < 80" de manière à charger une voiture jusquà 80%

* *isOn* * : This is the HA entity id of the "switch" button that we can test and use.
