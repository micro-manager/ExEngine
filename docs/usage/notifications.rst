.. _notifications:

=============
Notifications
=============


Notifications in ExEngine provide a powerful mechanism for asynchronous communication between the Execution and user code. They allow devices, events, and other components to broadcast updates about their status or important occurrences. This enables reactive programming patterns, allowing your software to respond dynamically to changes in the system state or experimental conditions.

Notifications can serve several purposes:

 - Inform about the completion of asynchronous operations (i.e. those occuring on a different thread)
 - Alert about changes in device states
 - Communicate errors or warnings
 - Provide updates on the progress of long-running tasks



Anatomy of a Notification
^^^^^^^^^^^^^^^^^^^^^^^^^^

Notifications in ExEngine are instances of classes derived from the base ``Notification`` class. Each notification has several components:

1. **Category**: Defined by the ``NotificationCategory`` enum, this indicates the broad type of the notification (``Event``, ``Data``, ``Storage``, or ``Device``).

2. **Description**: A string providing a  explanation of what the notification represents.

3. **Payload**: An optional piece of data associated with the notification, whose type depends on the particular notification.

4. **Timestamp**: Automatically set to the time the notification was created.


Built-in Notification Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ExEngine provides built-in notification types, such as:

1. ``EventExecutedNotification``: Posted when an ExecutionEvent completes. Its payload is None, or an Exception if the event didn't complete successfully

2. ``DataStoredNotification``: Posted when data is stored by a Storage object. Its payload is the ``DataCoordinates`` of the stored data.



Subscribing to Notifications
----------------------------

To subscribe to notifications from ExEngine, you can use the ``subscribe_to_notifications`` method of the ``ExecutionEngine`` instance:

.. code-block:: python

    from exengine import ExecutionEngine

    def notification_handler(notification):
        print(f'Got Notification: time {notification.timestamp} and payload {notification.payload}')

    engine = ExecutionEngine.get_instance()

    engine.subscribe_to_notifications(notification_handler)

    
    # When finished, unsubscribe
    engine.unsubscribe_from_notifications(notification_handler)



Your ``notification_handler`` function will be called each time a new notification is posted. Since there may be many notifications produced by the ``ExecutionEngine``, these handler functions should not contain code that takes a long time to run.


Filtering Subscriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can filter notifications by type (i.e. a specific notification subclass) or category when subscribing, so that the handler function only gets called for a subset of notifications

.. code-block:: python


    # Subscribe to a specific notification type
    # SpecificNotificationClass should be a subclass of exengine.base_classes.Notification
    engine.subscribe_to_notifications(handler, SpecificNotificationClass)


    # Subscribe to notifications of a specific category
    from exengine.kernel.notification_base import NotificationCategory

    engine.subscribe_to_notifications(handler, NotificationCategory.Data)

Multiple subscriptions with different filters can be set up:

.. code-block:: python

    engine.subscribe_to_notifications(handler1, NotificationA)
    engine.subscribe_to_notifications(handler2, NotificationCategory.Device)
    engine.subscribe_to_notifications(handler3)  # No filter, receives all notifications




Determining Available Notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ExecutorEvents`` declare the types of notifications they might emit through the ``notification_types`` class attribute. This attribute is a list of Notification types that the event may produce during its execution.

To discover which notification types are supported by a particular event:

.. code-block:: python

    print(MyEvent.notification_types)


All ExecutorEvents include the ``EventExecutedNotification`` by default. Subclasses can add their additional custom types of notifications.



Awaiting Notifications from a Future
------------------------------------

Notifications can be awaited on an :ref:`ExecutionFuture <futures>` in addition to subscribing to ExEngine notifications. This is useful for waiting on specific conditions related to a particular ``ExecutorEvent``:

.. code-block:: python

    future = engine.submit(some_event)
    notification = future.await_notification(SomeSpecificNotification)

The Future tracks all notifications for its event. If called after a notification occurs, it returns immediately.



Publishing Notifications
-------------------------

Events can emit notifications using the ``publish_notification`` method:

.. code-block:: python

    class MyEvent(ExecutorEvent):
        notification_types = [MyCustomNotification]

        def execute(self):
            # ... do something ...
            self.publish_notification(MyCustomNotification(payload="Something happened"))




Creating Custom Notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See :ref:`add_notifications` .