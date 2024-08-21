.. _add_devices:

##############################
Adding Support for New Devices
##############################

This guide outlines the process of adding support for new devices to the ExEngine framework.

1. Inherit from the Device Base Class
==========================================

All new devices should inherit from the ``Device`` base class or one or more of its subclasses (see `exengine.kernel.device_types_base <https://github.com/micro-manager/ExEngine/blob/main/src/exengine/kernel/device_types_base.py>`_)

.. code-block:: python

   from exengine.base_classes import Device

   class ANewDevice(Device):
       def __init__(self, name):
           super().__init__(name)
           # Your device-specific initialization code here

2. Implement Device Functionality
==========================================

Devices can expose functionality through properties and methods. The base ``Device`` class primarily uses properties.

Properties are essentially attributes with additional capabilities. They can have special characteristics, which are defined by implementing abstract methods in the ``Device`` class:

- Allowed values: Properties can have a finite set of allowed values.
- Read-only status: Properties can be set as read-only.
- Limits: Numeric properties can have upper and lower bounds.
- Triggerability: Properties can be hardware-triggerable.

Here's an example of implementing these special characteristics:

.. code-block:: python

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

3. Use Specialized Device Types
==========================================

There are specialized device types that standardize functionalities through methods. For example, a camera device type will have methods for taking images, setting exposure time, etc. Inheriting from one or more of these devices is recommended whenever possible, as it ensures compatibility with existing workflows and events.

Specialized device types implement functionality through abstract methods that must be implemented by subclasses. For example:

.. code-block:: python

   from exengine.device_types import Detector

   # TODO: may change this API in the future
   class ANewCameraDevice(Detector):
       def set_exposure(self, exposure: float) -> None:
           # Implementation here

       def get_exposure(self) -> float:
           # Implementation here

       # Implement other camera-specific methods...

Advanced Topics
===============

What inheritance from ``Device`` provides
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Inheriting from the ``Device`` class or its subclasses provides two main benefits:

1. Compatibility with events for specialized devices in the ExEngine framework, reducing the need to write hardware control code from scratch.
2. **Thread safety**. All calls to devices that may interact with hardware are automatically rerouted to a common thread. This enables code from various parts of a program to interact with a device that may not be thread safe itself. As a result, there is no need to worry about threading and synchronization concerns in devices, thereby simplifying device control code and the process of adding new devices.
3. The ability to monitor all inputs and outputs from devices. Since all calls to devices pass through the execution engine, a complete accounting of the commands sent to hardware and the data received from it can be generated, without having to write more complex code.

Bypassing the Executor
^^^^^^^^^^^^^^^^^^^^^^

In some cases, you may have attributes or methods that don't interact with hardware and don't need to go through the executor. You can bypass the executor for specific attributes or for the entire device:

1. Specify attributes to bypass in the Device constructor:

   .. code-block:: python

      class MyNewDevice(Device):
          def __init__(self, name):
              super().__init__(name, no_executor_attrs=('_some_internal_variable', 'some_method'))
              # This will be executed on the calling thread like a normal attribute
              self._some_internal_variable = 0

          def some_method(self):
              # This method will be executed directly on the calling thread
              pass

2. Bypass the executor for all attributes and methods:

   .. code-block:: python

      class MyNewDevice(Device):
          def __init__(self, name):
              super().__init__(name, no_executor=True)
              # All attributes and methods in this class will bypass the executor
              self._some_internal_variable = 0

          def some_method(self):
              # This method will be executed directly on the calling thread
              pass

Using the first approach allows you to selectively bypass the executor for specific attributes or methods, while the second approach bypasses the executor for the entire device.

Note that when using ``no_executor_attrs``, you need to specify the names of the attributes or methods as strings in a sequence (e.g., tuple or list) passed to the ``no_executor_attrs`` parameter in the ``super().__init__()`` call.

These approaches provide flexibility in controlling which parts of your device interact with the executor, allowing for optimization where direct access is safe and beneficial.