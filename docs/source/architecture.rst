
Architecture description
========================

This part is mainly for developers who want to edit the code.

# Architecture

Unlike many Home Assistant integrations, OpenHEMS is built around a single object: the **Network**.

The Network is the in-memory representation of the electrical installation. Every source, consumer, battery, solar panel and switch belongs to the Network.

The application itself contains very little business logic. Most of the intelligence comes from collaborating components:

* **Network**
* **NetworkUpdater**
* **Feeder**
* **Strategy**

These four concepts form the core of OpenHEMS.

## Core Components

Network

```

The `Network` is the domain model.

It contains every electrical node ( `Node` ) and their current state:

- public grid ( class `publicpowergrid` )
- solar panels ( class `solarpanel` )
- batteries ( class `battery` )
- controllable appliances on/off ( class `switch` )
- sensors ( class `switch` )

The Network never communicates directly with Home Assistant.

Its responsibility is only to represent the current state of the house.

NetworkUpdater
```

The `NetworkUpdater` synchronizes the Network with the outside world.

Its responsibilities are:

* read sensors from Home Assistant
* update node values
* refresh forecasts
* update temporary values
* ensure the Network always represents the current state

It acts as the bridge between the physical installation and the in-memory model.

Feeders

```

A `Feeder` knows how to obtain one specific kind of information.

Examples include:

- Home Assistant entities
- weather forecasts
- electricity prices
- photovoltaic forecasts

Each feeder updates only the information it owns.

Adding support for a new external service usually means implementing a new Feeder, without modifying the rest of the application.

Strategies
```

A `Strategy` is responsible for making decisions.

It receives a fully updated Network and determines which devices should start or stop.

A Strategy never communicates directly with Home Assistant.

Instead, it modifies the Network or produces an action plan that will later be applied.

This separation makes it possible to implement multiple optimization algorithms while keeping the rest of the application unchanged.

## Execution Loop

Each iteration follows the same sequence.

::

```
    +----------------+
    | NetworkUpdater |
    +----------------+
             |
             | updates
             v
       +------------+
       |  Network   |
       +------------+
             ^
             |
    +--------+--------+
    |                 |
Feeders          Forecasts
             |
             v
      +--------------+
      |   Strategy   |
      +--------------+
             |
     decides actions
             |
             v
    Home Assistant API
```

A Strategy never reads Home Assistant directly.

A Feeder never makes optimization decisions.

The Network contains no communication code.

Each component has a single responsibility.
