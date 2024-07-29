.. _usage:

######
Usage
######

ExEngine is built around four key abstractions: Devices, Events, Futures, and Notifications.

Devices
=======
Devices in ExEngine are software representations of hardware components in a microscope system. When possible, they provide a consistent way to interact with diverse equipment, abstracting away the complexities of individual hardware implementations. When not possible, devices can additionally expose specialized APIs specific to individual components.

ExEngine supports multiple **backends** - individual devices or libraries of devices (e.g., Micro-Manager). The method to create devices depends on the specific backend in use.


Here's a minimal example using the Micro-Manager backend:

.. code-block:: python

   from mmpycorex import create_core_instance
   from exengine.kernel.executor import ExecutionEngine
   from exengine.backends.micromanager.mm_device_implementations import MicroManagerSingleAxisStage

   # Create the ExecutionEngine
   executor = ExecutionEngine()

   # Initialize Micro-Manager core
   create_core_instance(config_file='MMConfig_demo.cfg')

   # Access Micro-Manager device
   z_stage = MicroManagerSingleAxisStage()

   z_stage.set_position(1234.56)


Device Hierarchies
""""""""""""""""""

Devices in ExEngine exist in hierarchies. All devices must inherit from the exengine.Device base class. Further functionality can be standardized by inheriting from one or more specific device type classes. For example, ``MicroManagerSingleAxisStage`` is a subclass of ``exengine.SingleAxisPositioner``, which is itself a subclass of ``exengine.Device``.

The advantage of this hierarchical structure is that it standardizes functionality, allowing code to be written for generic device types (e.g., a single axis positioner) that will work with many different device libraries. This approach enables a common API across different libraries of devices, similar to Micro-Manager's device abstraction layer but on a meta-level - spanning multiple device ecosystems rather than just devices within a single project. However, ExEngine's device system is designed to be adaptable. While adhering to the standardized interfaces offers the most benefits, users can still leverage many advantages of the system without implementing these specialized APIs.


TODO: thread standardization features of devices (and how to turn off)

TODO: calling functions on devices directly

TODO: link to guide to adding backends

TODO: transition to more complex with events


Events
======
Events are modular units of instructions and or computation. They can be as simple as a single command like moving the position of a hardware device, or contain multiple steps and computation. They provide building blocks to create more complex experimental workflows.


TODO: what else should be said about events?


Notifications
=============
Notifications provide a mechanism for asynchronous communication within the system. They allow devices, events, and other components to broadcast updates about their status or important occurrences. This feature enables reactive programming patterns, allowing your software to respond dynamically to changes in the system state or experimental conditions.

Futures
=======
Futures represent the outcome of asynchronous operations. They provide a way to handle long-running tasks without blocking the main execution thread. Futures allow you to submit events for execution and then either wait for their completion or continue with other tasks, checking back later for results. This enables efficient, non-blocking execution of complex workflows.
