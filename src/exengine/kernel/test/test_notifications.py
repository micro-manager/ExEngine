import pytest
from unittest.mock import Mock, call
from exengine.kernel.notification_base import Notification, NotificationCategory
from exengine.kernel.acq_event_base import AcquisitionEvent, AcquisitionEventCompletedNotification
from exengine.kernel.executor import ExecutionEngine


# Mock classes for testing
class CustomNotification(Notification):
    category = NotificationCategory.Event
    description = "Custom notification for testing"


class CustomEvent(AcquisitionEvent):
    notification_types = [CustomNotification]

    def execute(self):
        return "Custom event executed"


@pytest.fixture
def mock_execution_engine(monkeypatch):
    mock_engine = Mock(spec=ExecutionEngine)
    monkeypatch.setattr(ExecutionEngine, 'get_instance', lambda: mock_engine)
    return mock_engine


def test_notification_types_inheritance():
    """
    Test that notification subclasses that declare their own notification types
    are included in the list of valid notification types for an event,
    in addition to the default notification types.
    """
    assert set(CustomEvent.notification_types) == {CustomNotification, AcquisitionEventCompletedNotification}


def test_event_completion_notification(mock_execution_engine):
    """
    Test that notifications are posted when an event completes.
    """
    event = CustomEvent()
    mock_future = Mock()
    event._set_future(mock_future)
    event._post_execution()

    # Check if the notification was published
    mock_execution_engine.publish_notification.assert_called_once()
    published_notification = mock_execution_engine.publish_notification.call_args[0][0]
    assert isinstance(published_notification, AcquisitionEventCompletedNotification)


def test_custom_notification_posting(mock_execution_engine):
    """
    Test that custom notifications can be posted during event execution.
    """
    event = CustomEvent()
    mock_future = Mock()
    event._set_future(mock_future)

    custom_notification = CustomNotification()
    event.post_notification(custom_notification)

    # Check if the notification was passed to the future
    mock_future._notify_of_event_notification.assert_called_once_with(custom_notification)


def test_invalid_notification_type_warning():
    """
    Test that a warning is issued when posting an invalid notification type.
    """

    class InvalidNotification(Notification):
        category ='General'
        description = "Invalid notification"

    event = CustomEvent()
    event._set_future(Mock())

    with pytest.warns(UserWarning):
        event.post_notification(InvalidNotification())


def test_event_exception_in_notification(mock_execution_engine):
    """
    Test that when an event raises an exception, it's included in the completion notification.
    """
    event = CustomEvent()
    event._set_future(Mock())

    test_exception = ValueError("Test exception")
    event._post_execution(exception=test_exception)

    mock_execution_engine.publish_notification.assert_called_once()
    published_notification = mock_execution_engine.publish_notification.call_args[0][0]
    assert isinstance(published_notification, AcquisitionEventCompletedNotification)
    assert published_notification.payload == test_exception