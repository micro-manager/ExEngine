Threading in ExEngine
=====================

ExEngine simplifies multi-threaded hardware control by managing threading complexities. This approach allows for high-performance applications without requiring developers to handle concurrency at every level.

This page provides an overview of ExEngine's threading management and its effective use.

The Challenge: Balancing Simplicity and Performance
---------------------------------------------------

In hardware control applications, there's often a mismatch between simple user code and complex device interactions. Ideally, hardware control should be as straightforward as:

.. code-block:: python

    some_device = SomeDevice()
    some_device.take_action()
    value = some_device.read_value()

While this works for single-threaded applications, it can cause issues in multi-threaded environments. For example, a user interface thread and a separate control logic thread might simultaneously access a device. If the device wasn't explicitly designed for multi-threading (i.e. using locks or other synchronization mechanisms), this can lead to hard-to-diagnose bugs.

Common solutions like single-threaded event loops can limit performance, while implementing thread safety in each device increases complexity.


ExEngine's Solution for Thread-Safe Device Control
--------------------------------------------------

ExEngine addresses the challenge of thread-safe device control by routing all method calls and attribute accesses of `Device` objects through a common thread pool managed by the `ExecutionEngine`. In other words, when a user calls a method on a device, sets an attribute, or gets an attribute, the call is automatically routed to the `ExecutionEngine` for execution.

This allows for simple, seemingly single-threaded user code. That is, users can methods and set attributes in the normal way (e.g. ``device.some_method()``, ``device.some_attribute = value``), from any thread, but the actual execution happens on a thread managed by the executor.

This approach ensures thread safety when using devices from multiple contexts without requiring explicit synchronization in user or device code.

**Low-level Implementation Details**

.. toggle::

    While understanding the underlying mechanics isn't essential for regular usage, here's a brief overview:

    The core of this solution lies in the `DeviceMetaclass`, which wraps all methods and set/get operations on attributes classes inheriting from `Device` subclasses.

    When a method is called or an attribute is accessed, instead of executing directly, a corresponding event (like `MethodCallEvent` or `GetAttrEvent`) is created and submitted to the `ExecutionEngine`. The calling thread blocks until the event execution is complete, maintaining the illusion of synchronous operation.

    In other words, calling a function like:

    .. code-block:: python

        some_device.some_method(arg1, arg2)

    Gets automatically transformed into a ``MethodCallEvent`` object, which is then submitted to the `ExecutionEngine` for execution, and its result is returned to the calling thread.

    .. code-block:: python

        some_event = MethodCallEvent(method_name="some_method",
                                     args=(arg1, arg2),
                                     kwargs={},
                                     instance=some_device)
        future = ExecutionEngine.get_instance().submit(event)
        # Wait for it to complete on the executor thread
        result = future.await_execution()



    On an executor thread, the event's `execute` method is called:

          .. code-block:: python

             def execute(self):
                 method = getattr(self.instance, self.method_name)
                 return method(*self.args, **self.kwargs)


    This process ensures that all device interactions occur on managed threads, preventing concurrent access issues while maintaining a simple API for users.


Direct Use of the ExecutionEngine
---------------------------------

While device operations are automatically routed through the ExecutionEngine, users can also submit complex events directly:

.. code-block:: python

    future = engine.submit(event)

By default, this executes on the ExecutionEngine's primary thread.

ExEngine also supports named threads for task-specific execution:

.. code-block:: python

    engine.submit(readout_event, thread_name="DetectorThread")
    engine.submit(control_event, thread_name="HardwareControlThread")

This feature enables logical separation of asynchronous tasks. For instance:

- One thread can be dedicated to detector readouts
- Another can manage starting, stopping, and controlling other hardware

Using named threads enhances organization and can improve performance in multi-task scenarios.