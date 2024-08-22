.. _devices:


=======
Devices
=======


Devices in ExEngine represent hardware or software components. They provide:

- Standardized interfaces for common functionalities
- Thread-safe execution of commands
- Support for multiple backend implementations (i.e. physical hardware devices or libraries for the control of multiple devices)
- Flexibility to represent any grouping of related functionality


While often used for microscopy hardware, ExEngine's device concept and its benefits are not limited to this domain. A device can represent physical hardware, virtual devices, or software services.



Using Devices
-------------
ExEngine exposes devices through specific backends. 

For example, the Micro-Manager backend enables access to hardware devices controllable through Micro-Manager. (For installation and setup instructions, see :ref:`micro-manager_backend`).

.. code-block:: python

    # (assuming MM backend already installed and initialized)
    # load the micro-manager device for an objective lens switcher
    objective = MicroManagerDevice("Objective")
    
    # Set the objective in use
    objective.Label = "Nikon 10X S Fluor"

Without further specialization, devices are free to have any method and property names. However, certain functionalities are standardized through device types:



Device Types
^^^^^^^^^^^^
Functionality can be grouped with certain device types:

For example, the Detector type, which has standardized methods like start, stop, arm, etc.

Here's a quick example of a Detector:

.. code-block:: python

    detector = MicroManagerCamera()
    camera.arm(10) # this acquires 10 images
    camera.start()

Events often take specific device types as parameters. This enables the re-use of events across multiple devices

For example, the ReadoutData event takes a detector:

.. code-block:: python

    readout_event = ReadoutData(detector=camera, ...)




Thread Safety
-------------
By default, all ExEngine devices are made thread-safe. 

This is done under the hood by intercepting and rerouting all device calls to common threads.

This can be turned off by setting the ``no_executor`` parameter to ``True`` when initializing a device:

.. code-block:: python

    device = SomeDevice(no_executor=True)



Adding New Device Types
-----------------------
For information on adding new device types, see :ref:`add_devices`.
