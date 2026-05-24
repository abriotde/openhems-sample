"""
This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
The web server is the UI used to that.
"""
import logging
import datetime
import threading
from jinja2 import Template
from openhems.modules.util import CastUtililty, ConfigurationException

# pylint: disable=invalid-name, bad-indentation # Until full migration to snake_case

class OpenHEMSSchedule:
    """
    This class aim to comunicate what devices user want to schedule to the OpenHEMS core server.
     The web server is the UI used to that.
    """
    duration: int = 0
    timeout = "00:00"
    def __init__(self, ha_id: str, name:str, node=None,*, duration:int=0, timeout:datetime=None):
        self.name = name
        self.id = ha_id
        self.timeout:datetime = timeout
        self.duration:int = duration
        self.logger = logging.getLogger(__name__)
        self.strategy_cache = {}
        self._condition = None
        self.node = node
        self.lock = node.lock if node is not None and node.lock is not None else threading.Lock()

    def _get_val(self, ha_id):
        """
        Method used when eval(_condition) to get HA value of an HA id.
        """
        return self.node.network.networkUpdater.getEntityValue(ha_id)

    def set_val(self, ha_id, typename="str"):
        """
        Method used with Jinja2 to register an HA id for later call _get_val().
        Like an __init__()
        """
        if self.node is not None:
            self.node.network.networkUpdater.registerEntity(ha_id, typename)
            return "self._get_val('"+ha_id+"')"
        raise ConfigurationException(
            f"A node is necessary to register an HA id ({ha_id}, {typename})")

    def set_condition(self, condition):
        """
        Set a condition to switch on device.
        Exp: "{{ getVal('sensor.carcharge') }}<80"
        """
        if condition is not None:
            template = Template(condition)
            condition = template.render(getVal=self.set_val)
        self._condition = condition
        return self._condition

    def is_scheduled(self):
        """
        Return True, if device is schedule to be on
        """
        try:
            # pylint: disable=eval-used
            if self._condition is not None and eval(self._condition):
                return True
        except NameError as e:
            self.logger.error("is_scheduled(%s) = ERROR : %s : Ignore this condition.",
                              self._condition, str(e))
            raise ConfigurationException(e) from e
        with self.lock:
            self.logger.debug("OpenHEMSSchedule.is_scheduled(%s) : duration = %s",
                    self.id, self.duration)
        return self.duration is not None and self.duration>0

    def set_schedule(self, duration:int=None, timeout:datetime=None):
        """
        Set device duration to be on
         AND timeout until witch all duration should be elapsed
        """
        msg = ("OpenHEMSSchedule.set_schedule("
            f"{duration} seconds, timeout={timeout})")
        if duration is None:
            duration = self.duration
        if duration!=self.duration or self.timeout!=timeout:
            self.logger.info(msg)
        else:
            self.logger.debug("%s (no change)", msg)
        if timeout is not None and not isinstance(timeout, datetime.datetime):
            timeout = CastUtililty.toTypeDatetime(timeout)
        if not isinstance(duration, int):
            timeout = CastUtililty.toTypeInt(duration)
        with self.lock:
            self.duration = duration
            self.timeout = timeout
            self.strategy_cache = {}

    def get_strategy_cache(self, strategy_id):
        """
        Return cache used by a strategy_id ()
        """
        return self.strategy_cache.get(strategy_id, None)

    def set_strategy_cache(self, strategy_id, value):
        """
        Set cache for a strategy_id    
        """
        with self.lock:
            self.strategy_cache[strategy_id] = value

    def decrement_time(self, duration):
        """
        decrease time to be on from elapsed time.
        """
        with self.lock:
            self.duration = max(self.duration-duration, 0)
        return self.duration

    def __json__(self):
        """
        Export as JSON.
        """
        with self.lock:
            timeout = self.timeout.strftime("%H:%M") if self.timeout is not None else "0"
            if self.timeout is not None:
                timeout_dt = self.timeout.strftime("%Y-%m-%d %H:%M")
            else:
                timeout_dt = None
            return {"name":self.name,
                "duration":self.duration,
                "timeout":timeout,
                "timeout_dt":timeout_dt}

    def __str__(self):
        with self.lock:
            timeout = self.timeout.strftime("%Y-%m-%d %H:%M:%S") if self.timeout is not None else ""
            return f"Schedule({self.name}, duration:{self.duration}, timeout:{timeout})"
