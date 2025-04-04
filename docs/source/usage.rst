
Usage
=====


In this paragraph we will see main use cases of OpenHEMS and how we can use it. We will introduce some notions.

As said previously, you need to have controlable devices. But there is different contrallable devices:


Different devices
-----------------

Human controlled devices
~~~~~~~~~~~~~~~~~~~~~~~~

This is devices witch usually we need to press a button. Instead of doing this, for those devices, OpenHEMS offer an interface in Home-Assistant to ask OpenHEMS to start it in the futur. This interface is accessible from any web brower (Firefox, Chromium, Safari...) and from the Android and iOS application Home-Assistant.

In this interface, for each devices, you can set 

* "Duration" : how-long you want the device to be up, precise to the minute. If it's a cycle, no time is needed, just a start. 

* "Time out" : optionnally a time out. This time out is a time during the next 24 hours. If you not set, OpenHEMS can use many day to achieve it (Bu usually do it in 24h).

This concern a waste majority of devices.

Automatical devices
~~~~~~~~~~~~~~~~~~~

This concern devices witch we want to be on depending on time or other existing parameters. We think to Wi-Fi who some want to switch off on night or to outside light whitch some want to switch on depending on sun rise. Some can be optionnal functionnality that we can switch off during higth load. We think to fountain or automatic mower (or vacuum cleaner) charge.

Retro-action controlled devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is devices witch can be controlled "automatically" by one or many sensor. It can be heating, fridge, Controlled Mechanical Ventilation (CMV).

For this there is usually an acceptable margin, with OpenHEMS we could play with this margin to reduce consumption. But there is few benefits to expect. The idea is to overload when there is electricity at low cost (or to much) and to let go down to minimum value at exepensive periods. The problem is that there is an overload during overload period witch is maybe not really economically interesting and maybe a loss of confort.

For each devices you will affect a "strategy". This strategy will decide when to start & stop it. There is some different kind of strategy. Lets explore it.


Different strategy
------------------

First, we class use cases depending on source power.

* With unpredictable source power but usually with a static cost. Typically with solar-panels or wind turbine.

* With predictable and reliable source of power but with a variable cost. Usually it's public power grid.

* For cases with predictable, reliable and fixed cost, OpenHEMS is less usefull except maybe to reduce some consumptions.


Offpeak strategy
~~~~~~~~~~~~~~~~

The offpeak strategy is for predictable sources. Usually it consist on a public power grid source with offpeak/peak hours. Usually it is fixed off-peak hours but we can imagine to change it. We can have more complex cases with variable costs.

For this we use "Offpeak" strategy. In this cases devices are start during offpeak range time. 

But some time ther is not enough time during offpeak periods to respect wanted time out. In this case, the system wil decide a minimum switch on during peak period at lower cost.

It happen the consumption run to higth (configured), for safety the system will suspend device.


Switchoff strategy
~~~~~~~~~~~~~~~~~~

This strategy is used for devices to switch on (or switch off) during a period depending time. We can configure to add conditions witch is usefull to switch off not neccessary devices on exceptionnal and critical cases (Hight cost or low battery)


Emhass strategy
~~~~~~~~~~~~~~~

The Emhass strategy is based on Emhass project. You can see his [documentation](https://emhass.readthedocs.io/en/latest/differences.html) for more informations.

Basically, this strategy is interesting when there is unpredictable power sources (like solar panels and/or battery).

In this cases, OpenHEMS will have to guess what should be the production and consumption to decide what to do and when. For this it uses Artificial Intelligence and based on history and meteo prediction, try to guess.
