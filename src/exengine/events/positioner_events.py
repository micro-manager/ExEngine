from typing import Union, Tuple, Optional, SupportsFloat, TYPE_CHECKING
import numpy.typing as npt

from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.device_types import (DoubleAxisPositioner, SingleAxisPositioner,
                          TriggerableSingleAxisPositioner, TriggerableDoubleAxisPositioner)

if TYPE_CHECKING:
    from typing import Any


class SetPosition2DEvent(ExecutorEvent):
    """
    Set the position of a movable device
    """
    def __init__(self, device: Optional[DoubleAxisPositioner], position: Tuple[SupportsFloat, SupportsFloat]):
        super().__init__()
        self.device = device
        self.position = (float(position[0]), float(position[1]))

    def execute(self):
        self.device.set_position(*self.position)

class SetTriggerable2DPositionsEvent(ExecutorEvent):
    """
    Set the position of a movable device
    """

    def __init__(self, device: Optional[TriggerableDoubleAxisPositioner], positions: Union[list[Tuple[float, float]], npt.NDArray["Any"]]):
        super().__init__()
        self.device = device
        self.positions = positions

    def execute(self):
        self.device.set_position_sequence(self.positions)

class SetPosition1DEvent(ExecutorEvent):
    """
    Set the position of a movable device
    """

    def __init__(self, device: Optional[SingleAxisPositioner], position: SupportsFloat):
        super().__init__()
        self.device = device
        self.position = float(position)

    def execute(self):
        self.device.set_position(self.position)

class SetTriggerable1DPositionsEvent(ExecutorEvent):
    """
    Send a sequence of positions to a 1D positioner that will be triggered by TTL pulses
    """

    def __init__(self, device: Optional[TriggerableSingleAxisPositioner], positions: Union[list[float], npt.NDArray["Any"]]):
        super().__init__()
        self.device = device
        self.positions = positions

    def execute(self):
        self.device.set_position_sequence(self.positions)

class StopTriggerablePositionSequenceEvent(ExecutorEvent):
    """
    Stop the current triggerable sequence
    """

    def __init__(self, device: Optional[Union[TriggerableSingleAxisPositioner, TriggerableDoubleAxisPositioner]]):
        super().__init__()
        self.device = device

    def execute(self):
        self.device.stop_position_sequence()