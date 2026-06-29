from abc import ABC, abstractmethod

from .models import (
    EventDB,
    ForecastDB,
    NetworkSnapshot,
    OptimizationRun,
)


class Repository(ABC):

    @abstractmethod
    def save_snapshot(self, snapshot: NetworkSnapshot) -> None:
        ...

    @abstractmethod
    def save_event(self, event: EventDB) -> None:
        ...

    @abstractmethod
    def commit(self) -> None:
        ...

    def save_record(self, record):
        ...

    def get_records(self, type, device, subtype=None):
        ...