from typing import Any, Iterable, Tuple, Union
from exengine.kernel.device import Device
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.ex_event_base import ExecutorEvent

class SetPropertiesEvent(ExecutorEvent):
    """ Set one or more properties (i.e. attributes) of one or more devices """

    def __init__(self, devices_prop_names_values: Iterable[Tuple[Union[Device, str], str, Any]]):
        super().__init__()
        self.devices_prop_names_values = devices_prop_names_values

    def execute(self):
        # set all the properties
        for device, prop_name, value in self.devices_prop_names_values:
            if isinstance(device, str):
                device = ExecutionEngine.get_device(device)
            setattr(device, prop_name, value)


class SetTriggerablePropertySequencesEvent(ExecutorEvent):
    """
    Set a sequence of must for properties of different devices to be cycled through by hardware triggers
    The properties should be triggerable

    The property_sequence should be a list of tuples, each containing:
    - The name of the device or the device object itself
    - The name of the property to set
    - The sequence of values (e.g. a list) to set the property to
    """

    def __init__(self, property_sequences: Iterable[Tuple[Union[Device, str], str, Iterable[Any]]]):
        super().__init__()
        self.property_sequences = property_sequences

    def execute(self):
        # Load all sequences
        # TODO: ned to call list(self.property_sequences) here because otherwise pydantic returns this weird

        for device, prop_name, sequence in self.property_sequences:
            if isinstance(device, str):
                device = ExecutionEngine.get_device(device)
            if not device.is_property_hardware_triggerable(prop_name):
                raise ValueError(f"Property {prop_name} of device {device} is not hardware triggerable")
            device.load_triggerable_sequence(prop_name, list(sequence))
        # Start all sequences
        for device, prop_name, _ in self.property_sequences:
            if isinstance(device, str):
                device = ExecutionEngine.get_device(device)
            device.start_triggerable_sequence(prop_name)


class StopTriggerablePropertySequencesEvent(ExecutorEvent):
    """
    Stop the current triggerable sequence for one or more properties of different devices

    The property_sequence should be a list of tuples, each containing:
    - The name of the device or the device object itself
    - The name of the property to with a property sequence to stop
    """

    def __init__(self, property_sequences: Iterable[Tuple[Union[Device, str], str]]):
        super().__init__()
        self.property_sequences = property_sequences

    def execute(self):
        for device, prop_name in self.property_sequences:
            if isinstance(device, str):
                device = ExecutionEngine.get_device(device)
            device.stop_triggerable_sequence(prop_name)