import time
import warnings
from dataclasses import dataclass

from exengine.kernel.ex_event_base import ExecutorEvent
from typing import Optional


@dataclass
class Sleep(ExecutorEvent):
    """
    Sleep for a specified amount of time
    """
    time_s: int

    def execute(self):
        time.sleep(self.time_s)

# TODO: should this be set start time event?
@dataclass
class SetTimeEvent(ExecutorEvent):
    """Set the time point"""
    # TODO: why is time index needed??
    time_index: int
    min_start_time: Optional[float] = None

    def execute(self):
        # TODO: delay until ready??
        warnings.warn("SetTimeEvent not implemented")
