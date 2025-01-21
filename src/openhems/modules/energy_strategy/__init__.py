"""
Module for choosing a energy management strategy.
 i.e. An algorythme for optimization.
"""

from .energy_strategy import EnergyStrategy, LOOP_DELAY_VIRTUAL
from .offpeak_strategy import OffPeakStrategy
from .switchoff_strategy import SwitchoffStrategy
# from .emhass_strategy import EmhassStrategy
from .solarbased_strategy import SolarBasedStrategy
from .hybridinverter_strategy import HybridInverterStrategy
