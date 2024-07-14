from typing import List, Union, Tuple, Optional
import numpy as np
from dataclasses import dataclass

from pycromanager.execution_engine.kernel.acq_event_base import AcquisitionEvent
from pycromanager.execution_engine.kernel.device_types_base import (DoubleAxisPositioner, SingleAxisPositioner,
                                                    TriggerableSingleAxisPositioner, TriggerableDoubleAxisPositioner)


@dataclass
class SetPosition2DEvent(AcquisitionEvent):
    """
    Set the position of a movable device
    """
    device: Optional[DoubleAxisPositioner]
    position: Tuple[float, float]

    def execute(self):
        self.device.set_position(*self.position)

@dataclass
class SetTriggerable2DPositionsEvent(AcquisitionEvent):
    """
    Set the position of a movable device
    """
    device: Optional[DoubleAxisPositioner]
    positions: Union[List[Tuple[float, float]], np.ndarray]

    def execute(self):
        self.device.set_position_sequence(self.positions)

@dataclass
class SetPosition1DEvent(AcquisitionEvent):
    """
    Set the position of a movable device
    """
    device: Optional[SingleAxisPositioner]
    position: Union[float, int]

    def execute(self):
        self.device.set_position(self.position)

@dataclass
class SetTriggerable1DPositionsEvent(AcquisitionEvent):
    """
    Send a sequence of positions to a 1D positioner that will be triggered by TTL pulses
    """
    device: Optional[TriggerableSingleAxisPositioner]
    positions: Union[List[float], np.ndarray]

    def execute(self):
        self.device.set_position_sequence(self.positions)

@dataclass
class StopTriggerablePositionSequenceEvent(AcquisitionEvent):
    """
    Stop the current triggerable sequence
    """
    device: Optional[Union[TriggerableSingleAxisPositioner, TriggerableDoubleAxisPositioner]]

    def execute(self):
        self.device.stop_position_sequence()