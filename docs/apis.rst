==============
API Reference
==============

ExecutionEngine
================

.. autoclass:: exengine.kernel.executor.ExecutionEngine
   :members:
   :exclude-members: register_device

.. autoclass:: exengine.kernel.ex_future.ExecutionFuture
   :members:

.. autoclass:: exengine.device_types.Device
   :members:

.. autoclass:: exengine.kernel.ex_event_base.ExecutorEvent
   :members:

.. autoclass:: exengine.kernel.notification_base.Notification
   :members:


Data
=====

.. autoclass:: exengine.kernel.data_storage_base.DataStorage
   :members:

.. autoclass:: exengine.kernel.data_coords.DataCoordinates

.. autoclass:: exengine.kernel.data_coords.DataCoordinatesIterator
   :members:

.. autoclass:: exengine.kernel.data_handler.DataHandler
   :members:

Micro-Manager Devices
=====================

.. autoclass:: exengine.backends.micromanager.mm_device_implementations.MicroManagerDevice
    :members:

.. autoclass:: exengine.backends.micromanager.mm_device_implementations.MicroManagerSingleAxisStage
    :members:

.. autoclass:: exengine.backends.micromanager.mm_device_implementations.MicroManagerXYStage
    :members:

.. autoclass:: exengine.backends.micromanager.mm_device_implementations.MicroManagerCamera
    :members:


.. _standard_events:

Standard Events
==================

Detector Events
```````````````

.. autoclass:: exengine.events.detector_events.ReadoutData

.. autoclass:: exengine.events.detector_events.DataAcquiredNotification

.. autoclass:: exengine.events.detector_events.StartCapture

.. autoclass:: exengine.events.detector_events.StartContinuousCapture

.. autoclass:: exengine.events.detector_events.StopCapture

Positioner Events
`````````````````

.. autoclass:: exengine.events.positioner_events.SetPosition2DEvent

.. autoclass:: exengine.events.positioner_events.SetTriggerable2DPositionsEvent

.. autoclass:: exengine.events.positioner_events.SetPosition1DEvent

.. autoclass:: exengine.events.positioner_events.SetTriggerable1DPositionsEvent

.. autoclass:: exengine.events.positioner_events.StopTriggerablePositionSequenceEvent

Property Events
````````````````
.. autoclass:: exengine.events.property_events.SetPropertiesEvent

.. autoclass:: exengine.events.property_events.SetTriggerablePropertySequencesEvent

.. autoclass:: exengine.events.property_events.StopTriggerablePropertySequencesEvent

Miscellaneous Events
````````````````````
.. autoclass:: exengine.events.misc_events.Sleep

.. autoclass:: exengine.events.misc_events.SetTimeEvent

Multi-Dimensional Acquisition Events
````````````````````````````````````
.. autofunction:: exengine.events.multi_d_events.multi_d_acquisition_events