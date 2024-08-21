.. _add_events:

#######################
Creating Custom Events
#######################

Basic Event Creation
--------------------

To create a custom event:

1. Subclass ``ExecutorEvent``
2. Implement the ``execute()`` method

.. code-block:: python

    from exengine.base_classes import ExecutorEvent

    class MyCustomEvent(ExecutorEvent):
        def execute(self):
            # Main event logic goes here
            result = self.perform_operation()
            return result

        def perform_operation(self):
            # Implement your operation here
            pass

Adding Notifications
--------------------

To add notifications:

1. Specify ``notification_types``
2. Use ``self.publish_notification()`` in ``execute()``

.. code-block:: python

    from exengine.notifications import MyCustomNotification

    class MyEventWithNotification(ExecutorEvent):
        notification_types = [MyCustomNotification]

        def execute(self):
            # Event logic
            self.publish_notification(MyCustomNotification(payload="Operation completed"))

Implementing Capabilities
-------------------------

Data Producing Capability
^^^^^^^^^^^^^^^^^^^^^^^^^

For events that produce data:

.. code-block:: python

    from exengine.base_classes import ExecutorEvent, DataProducing

    class MyDataProducingEvent(ExecutorEvent, DataProducing):
        def execute(self):
            data, metadata = self.generate_data()
            self.put_data(data_coordinates, data, metadata)

        def generate_data(self):
            # Generate your data here
            pass

Stoppable Capability
^^^^^^^^^^^^^^^^^^^^

For stoppable events:

.. code-block:: python

    from exengine.base_classes import ExecutorEvent, Stoppable

    class MyStoppableEvent(ExecutorEvent, Stoppable):
        def execute(self):
            while not self.is_stop_requested():
                self.do_work()
            self.cleanup()

        def do_work(self):
            # Implement your work here
            pass

        def cleanup(self):
            # Cleanup logic here
            pass
