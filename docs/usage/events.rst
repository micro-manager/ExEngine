.. _events:

======
Events
======

Events in ExEngine are the fundamental units of experimental workflows. They represent discrete tasks or operations that can be submitted to the ExecutionEngine for execution. Events provide a flexible and modular way to construct complex experimental workflows, ranging from simple hardware commands to sophisticated multi-step procedures that may involve data analysis.

ExEngine supports two types of events:

- ``Callable`` objects (methods/functions/lambdas) for simple tasks
- ``ExecutorEvent`` subclasses for complex operations


Simple Events: Callable Objects
-------------------------------
For straightforward tasks, you can submit a callable object directly:

.. code-block:: python

    def simple_task():
        do_something()

    engine.submit(simple_task)



ExecutorEvent Objects
----------------------

For more complex operations, use ExecutorEvent subclasses. These provide additional capabilities like notifications and data handling:

.. code-block:: python

    from exengine.events.positioner_events import SetPosition2DEvent

    move_event = SetPosition2DEvent(device=xy_stage, position=(10.0, 20.0))
    future = engine.submit(move_event)



.. code-block:: python

    # Asynchronous execution
    future = engine.submit(move_event)
    # This returns immediately, allowing other operations to continue

The power of this approach lies in its ability to separate the definition of what takes place from the details of how it is executed. While the event defines the operation to be performed, the execution engine manages the scheduling and execution of events across multiple threads. This separation allows for complex workflows to be built up from simple, reusable components, while the execution engine manages the details of scheduling execution, and error handling.

A list of available events can be found in the :ref:`standard_events` section.

Monitoring Event Progress
--------------------------

When an event is submitted to the ExecutionEngine, it is executed on a separate thread. Monitoring its progress is often necessary for several reasons:

- Program flow control (e.g., blocking until completion)
- User interface updates
- Triggering subsequent actions
- Data retrieval from the event

ExEngine provides two mechanisms for this: futures and notifications. The :ref:`futures` and :ref:`notifications` provide full details, while a brief overview is given below:


Futures
^^^^^^^
A future is returned when an event is submitted to the ExecutionEngine. This future represents the eventual result of the event and allows for the following:

- The event's completion can be checked or awaited
- The event's result can be retrieved
- Any data produced by the event can be accessed

For example:

.. code-block:: python

    # The event is submitted and a future is obtained
    future = engine.submit(event)

    # The event's completion is awaited and its result is obtained
    result = future.await_execution()


Notifications
^^^^^^^^^^^^^^

Notifications offer real-time updates about an event's progress without impeding its execution or that of subsequent events. They are useful for monitoring long-running events or updating user interfaces. They should not be used for resource-intensive operations such as retrieving large amounts of data, as they are intended for lightweight communication.


All events emit at minimum an ``EventExecutedNotification`` upon completion. Additional notifications may also be emitted during execution to provide progress updates.

Available notifications for an event can be checked as follows:

.. code-block:: python

    print(MyEvent.notification_types)

A specific notification can be awaited using a future:

.. code-block:: python

    future = engine.submit(my_event)
    future.await_notification(SpecificNotification)

This approach allows for targeted monitoring of event milestones or state changes.

Further details can be found in the :ref:`notifications` section.


Events that return values
--------------------------
Some events in ExEngine return values. These values can be retrieved in two ways:

1. Direct execution:

When executing an event directly, simply capture the return value:

.. code-block:: python

    from exengine.events import SomeComputationEvent

    compute_event = SomeComputationEvent(param1=10, param2=20)
    result = compute_event.execute()
    print(f"Result: {result}")

2. Asynchronous execution with futures:

When submitting an event to the ExecutionEngine, use the future to retrieve the result:

.. code-block:: python

    from exengine import ExecutionEngine

    engine = ExecutionEngine.get_instance()
    future = engine.submit(compute_event)
    result = future.await_execution()
    print(f"Result: {result}")



Composing Complex Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Events can be combined to create more complex workflows:

For example, moving an XY stage, capturing an image, and reading out the data and repeating can be expressed as the following sequence of events:

.. code-block:: python

    from exengine.events import SetPosition2DEvent, StartCapture, ReadoutData, Sleep

    # Create a sequence of events
    events = [
        SetPosition2DEvent(device=xy_stage, position=(0, 0)),
        StartCapture(detector=camera, num_images=1),
        ReadoutData(detector=camera, num_images=1),
        Sleep(time_s=1),
        SetPosition2DEvent(device=xy_stage, position=(10, 10)),
        StartCapture(detector=camera, num_images=1),
        ReadoutData(detector=camera, num_images=1),
    ]

    # Submit all events
    futures = engine.submit(events)


.. TODO: compound future or get individual futures


Event Capabilities
-------------------

Events in ExEngine can have special "Capabilities" that extend their functionality. These Capabilities are accessed through methods on the futures returned when submitting events to the ExecutionEngine.

Data Producing Events
^^^^^^^^^^^^^^^^^^^^^

Some events are capable of generating data during their execution. For these events, you can use the ``await_data`` method on the future to retrieve the produced data:

.. code-block:: python

    future = engine.submit(data_producing_event)
    data, metadata = future.await_data(data_coordinates, return_data=True, return_metadata=True)

This method allows you to wait for specific data to be produced and optionally retrieve both the data and its associated metadata.

``DataProducing`` events must have an associated :ref:`DataCoordinatesIterator <data_coordinates_iterator>` so that the data produced can be uniquely identified, and a :ref:`DataHandler <data_handler>` so that it knows where to send the data.

Stoppable Events
^^^^^^^^^^^^^^^^

Certain events can be interrupted during their execution. If an event is stoppable, you can use the ``stop`` method on its future:

.. code-block:: python

    future = engine.submit(stoppable_event)
    # ... later ...
    future.stop(await_completion=True)

This method requests the event to stop its execution. The ``await_completion`` parameter determines whether the method should block until the event has stopped.

Abortable Events
^^^^^^^^^^^^^^^^

Similar to stoppable events, abortable events can be terminated, but more abruptly. Use the ``abort`` method on the future:

.. code-block:: python

    future = engine.submit(abortable_event)
    # ... later ...
    future.abort(await_completion=True)

This method immediately terminates the event's execution. As with ``stop``, ``await_completion`` determines whether to wait for the abortion to complete.

Creating Custom Events
-----------------------

.. TODO: lambda events

See the :ref:`add_events` section for more information on creating custom events.