""""
Base classes for device_implementations that can be used by the execution engine
"""

from abc import abstractmethod, ABC
from typing import Tuple, List, Iterable, Union
import numpy as np
from kernel.device import DeviceMetaclass



class Device(ABC, metaclass=DeviceMetaclass):
    """
    Required base class for all devices usable with the execution engine

    Device classes should inherit from this class and implement the abstract methods. The DeviceMetaclass will wrap all
    methods and attributes in the class to make them thread-safe and to optionally record all method calls and
    attribute accesses.

    Attributes with a trailing _noexec will not be wrapped and will be executed directly on the calling thread. This is
    useful for attributes that are not hardware related and can bypass the complexity of the executor.

    Device implementations can also implement functionality through properties (i.e. attributes that are actually
    methods) by defining a getter and setter method for the property.
    """

    def __init__(self, device_name: str):
        self._device_name_noexec = device_name


    @abstractmethod
    def get_allowed_property_values(self, property_name: str) -> List[str]:
        ...

    @abstractmethod
    def is_property_read_only(self, property_name: str) -> bool:
        ...

    @abstractmethod
    def get_property_limits(self, property_name: str) -> Tuple[float, float]:
        ...

    @abstractmethod
    def is_property_hardware_triggerable(self, property_name: str) -> bool:
        ...

    @abstractmethod
    def get_triggerable_sequence_max_length(self, property_name: str) -> int:
        ...

    @abstractmethod
    def load_triggerable_sequence(self, property_name: str, event_sequence: Iterable[Union[str, float, int]]):
        ...

    @abstractmethod
    def start_triggerable_sequence(self, property_name: str):
        ...

    @abstractmethod
    def stop_triggerable_sequence(self, property_name: str):
        ...



# TODO: could replace hard coded classes with
#  T = TypeVar('T')
#  Positionaer(Generic[T]):
#  and then (float) or (float, float) for number axes
#  or make a triggerable mixin that does this

class SingleAxisPositioner(Device):
    """ A positioner that can move along a single axis (e.g. a z drive used as a focus stage) """

    @abstractmethod
    def set_position(self, position: float) -> None:
        ...

    @abstractmethod
    def get_position(self) -> float:
        ...


class TriggerableSingleAxisPositioner(SingleAxisPositioner):
    """
    A special type of positioner that can accept a sequence of positions to move to when provided external TTL triggers
    """
    @abstractmethod
    def set_position_sequence(self, positions: np.ndarray) -> None:
        ...

    @abstractmethod
    def get_triggerable_position_sequence_max_length(self) -> int:
        ...

    @abstractmethod
    def stop_position_sequence(self) -> None:
        ...


class DoubleAxisPositioner(Device):

        @abstractmethod
        def set_position(self, x: float, y: float) -> None:
            ...

        @abstractmethod
        def get_position(self) -> Tuple[float, float]:
            ...

class TriggerableDoubleAxisPositioner(DoubleAxisPositioner):

        @abstractmethod
        def set_position_sequence(self, positions: np.ndarray) -> None:
            ...

        @abstractmethod
        def get_triggerable_position_sequence_max_length(self) -> int:
            ...

        @abstractmethod
        def stop_position_sequence(self) -> None:
            ...


class Camera(Device):
    """
    Generic class for a camera and the buffer where it stores data
    """

    # TODO: maybe change these to attributes?
    @abstractmethod
    def set_exposure(self, exposure: float) -> None:
        ...

    @abstractmethod
    def get_exposure(self) -> float:
        ...

    @abstractmethod
    def arm(self, frame_count=None) -> None:
        """
        Arms the device before an start command. This optional command validates all the current features for
        consistency and prepares the device for a fast start of the Acquisition. If not used explicitly,
        this command will be automatically executed at the first AcquisitionStart but will not be repeated
        for the subsequent ones unless a feature is changed in the device.
        """
        ...

    @abstractmethod
    def start(self) -> None:
        ...

    # TODO: is it possible to make this return the number of images captured, to know about when to stop readout?
    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def is_stopped(self) -> bool:
        ...

    # TODO: perhaps this should be a seperate buffer class
    @abstractmethod
    def pop_image(self, timeout=None) -> Tuple[np.ndarray, dict]:
        """
        Get the next image and metadata from the camera buffer. If timeout is None, this function will block until
        an image is available. If timeout is a number, this function will block for that many seconds before returning
        (None, None) if no image is available
        """
        ...

