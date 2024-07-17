# Adding Support for New Devices

This guide outlines the process of adding support for new devices to the ExEngine framework.

## 1. Inherit from the Device Base Class

All new devices should inherit from the `Device` base class or one or more of its subclasses (see [exengine.kernel.device_types_base](link-to-device-types-base-documentation)).

```python
from exengine.kernel.device_types_base import Device

class ANewDevice(Device):
    def __init__(self, name):
        super().__init__(name)
        # Your device-specific initialization code here
```

## 2. Implement Device Functionality

Devices can expose functionality through properties and methods. The base `Device` class primarily uses properties.

Properties are essentially attributes with additional capabilities. They can have special characteristics, which are defined by implementing abstract methods in the `Device` class:

- Allowed values: Properties can have a finite set of allowed values.
- Read-only status: Properties can be set as read-only.
- Limits: Numeric properties can have upper and lower bounds.
- Triggerability: Properties can be hardware-triggerable.

Here's an example of implementing these special characteristics:

```python
class ANewDevice(Device):
    def get_allowed_property_values(self, property_name: str) -> List[str]:
        if property_name == "mode":
            return ["fast", "slow", "custom"]
        return []

    def is_property_read_only(self, property_name: str) -> bool:
        return property_name in ["serial_number", "firmware_version"]

    def get_property_limits(self, property_name: str) -> Tuple[float, float]:
        if property_name == "exposure_time":
            return (0.001, 10.0)  # seconds
        return None

    def is_property_hardware_triggerable(self, property_name: str) -> bool:
        return property_name in ["position", "gain"]

    # Implement other abstract methods...
```

## 3. Use Specialized Device Types

There are specialized device types that standardize functionalities through methods. For example, a camera device type will have methods for taking images, setting exposure time, etc. Inheriting from one or more of these devices is recommended whenever possible, as it ensures compatibility with existing workflows and events.

Specilzed device types implement functionality through abstract methods that must be implemented by subclasses. For example:

```python
from exengine.kernel.device_types_base import Camera

# TODO: may change this API in the future
class ANewCameraDevice(Camera):
    def set_exposure(self, exposure: float) -> None:
        # Implementation here

    def get_exposure(self) -> float:
        # Implementation here

    # Implement other camera-specific methods...
```



# Advanced Topics

## What inheritance from `Device` provides

Inheriting from the `Device` class or its subclasses provides two main benefits:

1. Compatibility with events for specialized devices in the ExEngine framework, reducing the need to write hardware control code from scratch.
2. The ability to easy monitor and control hardware access from various parts of a program. By default, inheriting from device reroutes all methods and read/writes to the device through a common thread. This enables code from various parts of a program to interact with a device that may not be thread safe itself, without having to worry about locks and synchronization.

#### Bypassing the Executor

In some cases, you may have an attribute that doesn't interact with hardware and doesn't need to go through the executor. You can bypass the executor by appending `_noexec` to the attribute name. This will cause the attribute to be executed directly on the calling thread.

```python
class MyNewDevice(Device):
    def __init__(self, name):
        super().__init__(name)
        # This will be executed on the calling thread like a normal attribute
        self._some_internal_variable_noexec = 0
```
