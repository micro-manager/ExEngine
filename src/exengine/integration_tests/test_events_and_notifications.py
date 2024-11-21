"""
Integration tests for events, notifications, futures, and the execution engine
"""
import pytest
from exengine import ExecutionEngine
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.notification_base import Notification, NotificationCategory


class TestNotification(Notification[str]):
    category = NotificationCategory.Event
    description = "Test notification for integration testing"

class AnotherTestNotification(Notification[int]):
    category = NotificationCategory.Data
    description = "Another test notification"

class YetAnotherTestNotification(Notification[float]):
    category = NotificationCategory.Device
    description = "Yet another test notification"

class NotificationEmittingEvent(ExecutorEvent):
    notification_types = [TestNotification, AnotherTestNotification, YetAnotherTestNotification]

    def __init__(self, notifications_to_emit: list[Notification]):
        super().__init__()
        self.notifications_to_emit = notifications_to_emit


    def execute(self):
        for notification in self.notifications_to_emit:
            self.publish_notification(notification)
        return "Event executed"

@pytest.fixture
def engine():
    engine = ExecutionEngine()
    yield engine
    engine.shutdown()

def test_subscribe_with_notification_type_filter(engine):
    received_notifications = []

    def notification_callback(notification):
        received_notifications.append(notification)

    # Subscribe to TestNotification only
    engine.subscribe_to_notifications(notification_callback, TestNotification)

    # Create and submit an event that emits different types of notifications
    notifications = [
        TestNotification(payload="Should be received"),
        AnotherTestNotification(payload=42),
        YetAnotherTestNotification(payload=3.14)
    ]
    event = NotificationEmittingEvent(notifications_to_emit=notifications)
    f = engine.submit(event)

    f.await_execution()
    engine.shutdown()
    engine.check_exceptions()


    # Check if only TestNotification was received
    assert len(received_notifications) == 1
    assert isinstance(received_notifications[0], TestNotification)
    assert received_notifications[0].payload == "Should be received"

def test_subscribe_without_filter(engine):
    received_notifications = []

    def notification_callback(notification):
        received_notifications.append(notification)

    # Subscribe without any filter
    engine.subscribe_to_notifications(notification_callback)

    # Create and submit an event that emits different types of notifications
    notifications = [
        TestNotification(payload="Event notification"),
        AnotherTestNotification(payload=42),
        YetAnotherTestNotification(payload=3.14)
    ]
    event = NotificationEmittingEvent(notifications_to_emit=notifications)
    f = engine.submit(event)

    f.await_execution()
    engine.shutdown()
    engine.check_exceptions()

    # Check if all notifications were received
    assert len(received_notifications) == 4 # includes AcquisitionEventCompletedNotification
    assert isinstance(received_notifications[0], TestNotification)
    assert isinstance(received_notifications[1], AnotherTestNotification)
    assert isinstance(received_notifications[2], YetAnotherTestNotification)

def test_multiple_subscriptions_with_different_filters(engine):
    received_notifications_1 = []
    received_notifications_2 = []
    received_notifications_3 = []

    def callback_1(notification):
        received_notifications_1.append(notification)

    def callback_2(notification):
        received_notifications_2.append(notification)

    def callback_3(notification):
        received_notifications_3.append(notification)

    # Subscribe with different filters
    engine.subscribe_to_notifications(callback_1, TestNotification)
    engine.subscribe_to_notifications(callback_2, NotificationCategory.Data)
    engine.subscribe_to_notifications(callback_3)  # No filter

    # Create and submit an event that emits different types of notifications
    notifications = [
        TestNotification(payload="Event notification"),
        AnotherTestNotification(payload=42),
        YetAnotherTestNotification(payload=3.14)
    ]
    event = NotificationEmittingEvent(notifications_to_emit=notifications)
    f = engine.submit(event)

    f.await_execution()
    engine.shutdown()
    engine.check_exceptions()

    # Check if notifications were received according to filters
    assert len(received_notifications_1) == 1
    assert isinstance(received_notifications_1[0], TestNotification)

    assert len(received_notifications_2) == 1
    assert isinstance(received_notifications_2[0], AnotherTestNotification)

    assert len(received_notifications_3) == 4 # includes AcquisitionEventCompletedNotification
    assert isinstance(received_notifications_3[0], TestNotification)
    assert isinstance(received_notifications_3[1], AnotherTestNotification)
    assert isinstance(received_notifications_3[2], YetAnotherTestNotification)
