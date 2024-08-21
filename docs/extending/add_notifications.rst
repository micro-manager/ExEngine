.. _add_notifications:

==============================
Creating Custom Notifications
==============================

To create a custom notification:

1. Subclass ``exengine.base_classes.Notification``
2. Use Python's ``@dataclass`` decorator
3. Define ``category`` (from ``exengine.notifications.NotificationCategory`` enum) and ``description`` (string) as class variables
4. Optionally, specify a payload type using a type hint in the class inheritance. For example, ``class MyCustomNotification(Notification[str])`` indicates this notification's payload will be a string.

Keep payloads lightweight for efficient processing. Example:

.. code-block:: python

    from dataclasses import dataclass
    from exengine.base_classes import Notification
    from exengine.notifications import NotificationCategory

    @dataclass
    class MyCustomNotification(Notification[str]):
        category = NotificationCategory.Device
        description = "A custom device status update"

    # Usage
    notification = MyCustomNotification(payload="Device XYZ is ready")



