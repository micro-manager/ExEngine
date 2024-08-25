.. _add_devices:

##############################
Adding New Device Backends
##############################

We welcome contributions of new device backends to ExEngine! If you've developed a backend for a new device, framework, or system, please consider submitting a Pull Request.

This guide outlines the process of adding support for new devices to the ExEngine framework.


Code Organization and packaging
================================

When adding a new backend to ExEngine, follow this directory structure:

.. code-block:: text

    src/exengine/
    └── backends/
        └── your_new_backend/
            ├── __init__.py
            ├── your_implementations.py
            └── test/
                ├── __init__.py
                └── test_your_backend.py

Replace ``your_new_backend`` with an appropriate name for your backend.

You may also want to edit the ``__init__.py`` file in the ``your_new_backend`` directory to import the Classes for each device you implement in the ``your_implementations.py`` or other files (see the micro-manager backend for an example of this).

Additional dependencies
------------------------

If your backend requires additional dependencies, add them to the ``pyproject.toml`` file in the root directory of the project. This ensures that the dependencies are installed when the backend is installed.

1. Open the ``pyproject.toml`` file in the root directory of the project.
2. Add a new optional dependency group for your backend. For example:

   .. code-block:: toml

      [project.optional-dependencies]
      your_new_backend = ["your_dependency1", "your_dependency2"]

3. Update the ``all`` group to include your new backend:

   .. code-block:: toml

      all = [
          "mmpycorex",
          "ndstorage",

          "your_dependency1",
          "your_dependency2"
      ]

4. Also add it to the ``device backends`` group, so that it can be installed with ``pip install exengine[your_new_backend]``:

   .. code-block:: toml

      # device backends
      your_new_backend = ["dependency1", "dependency2"]


Implementing a New Device
===========================

All new devices should inherit from the ``Device`` base class or one or more of its subclasses (see `exengine.device_types <https://github.com/micro-manager/ExEngine/blob/main/src/exengine/device_types.py>`_)

.. code-block:: python

   from exengine.base_classes import Device

   class ANewDevice(Device):
       def __init__(self, name):
           super().__init__(name)
           # Your device-specific initialization code here

Exposing functionality
-----------------------

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

Use Specialized Device Types
---------------------------------

There are specialized device types that standardize functionalities through methods. For example, a camera device type will have methods for taking images, setting exposure time, etc. Inheriting from one or more of these devices is recommended whenever possible, as it ensures compatibility with existing workflows and events.

Specialized device types implement functionality through abstract methods that must be implemented by subclasses. For example:

.. code-block:: python

   from exengine.device_types import Detector

   class ANewCameraDevice(Detector):
       def arm(self, frame_count=None):
           # Implementation here

       def start():
           # Implementation here

       # Implement other detector-specific methods...



Adding Tests
------------

1. Create a ``test_your_backend.py`` file in the ``test/`` directory of your backend.
2. Write pytest test cases for your backend functionality. For example:

   .. code-block:: python

      import pytest
      from exengine.backends.your_new_backend import YourNewDevice

      def test_your_device_initialization():
          device = YourNewDevice("TestDevice")
          assert device.name == "TestDevice"

      def test_your_device_method():
          device = YourNewDevice("TestDevice")
          result = device.some_method()
          assert result == expected_value

      # Add more test cases as needed

Running Tests
-------------

To run tests for your new backend:

1. Install the test dependencies. In the ExEngine root directory, run:

   .. code-block:: bash

      pip install -e exengine[test,your_new_backend]

2. Run pytest for your backend:

   .. code-block:: bash

      pytest -v src/exengine/backends/your_new_backend/test

Adding documentation
------------------------

1. Add documentation for your new backend in the ``docs/`` directory.
2. Create a new RST file, e.g., ``docs/usage/backends/your_new_backend.rst``, describing how to use your backend.
3. Update ``docs/usage/backends.rst`` to include your new backend documentation.

To build the documentation locally, you may need to install the required dependencies. In the ``exengine/docs`` directory, run:

.. code-block:: bash

   pip install -r requirements.txt

Then, to build, in the ``exengine/docs`` directory, run:

.. code-block:: bash

   make clean && make html

then open ``_build/html/index.html`` in a web browser to view the documentation.




Advanced Topics
-----------------

Thread Safety and Execution Control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ExEngine provides powerful threading capabilities for device implementations, ensuring thread safety and allowing fine-grained control over execution threads. Key features include:

Automatic thread safety for device methods and attribute access.
The ability to specify execution threads for devices, methods, or events using the @on_thread decorator.
Options to bypass the executor for non-hardware-interacting methods or attributes.

For a comprehensive guide on ExEngine's threading capabilities, including detailed explanations and usage examples, please refer to the :ref:threading section.


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

