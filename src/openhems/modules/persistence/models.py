
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class NetworkSnapshot:
    id: int
    timestamp: datetime
    network_json: str


@dataclass(slots=True)
class ForecastDB:
    id: Optional[int]
    source: str
    timestamp: datetime
    valid_from: datetime
    valid_to: datetime
    payload_json: str


@dataclass(slots=True)
class OptimizationRun:
    id: Optional[int]
    timestamp: datetime
    finished_at: datetime
    strategy: str
    duration_ms: int
    score: Optional[float]

class EventType(enum.Enum):
    """
    List available event types
    """
    SWITCH_ON = 0
    SWITCH_OFF = 1

@dataclass(slots=True)
class EventDB:
    """
    Exp: Switch on device "mycar", due to reach offpeak hours & car programed for 2h.
    """
    id: Optional[int]
    timestamp: datetime
    type: EventType     # SWITCH_ON
    device: str         # mycar
    action: str         # SWITCH(on)
    source: str         # offpeak strategy
    reason: str         # "reach offpeak hours & car programed for 2h"
 
@dataclass(slots=True)
class RecordDB:
    """
    Exp: Switch on device "mycar", due to reach offpeak hours & car programed for 2h.
    """
    id: Optional[int]
    timestamp: datetime
    type: str           # FeedBackSwitch for exp
    device: str         # mycar
    subtype: str        # ON/OFF
    step: int           # 2 : Count the number of on/off range recorded.
    value: float        # 2.35
