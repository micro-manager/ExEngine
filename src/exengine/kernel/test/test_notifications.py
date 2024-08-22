import pytest
from unittest.mock import Mock, call
import numpy as np

from exengine.kernel.notification_base import Notification, NotificationCategory
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.notification_base import EventExecutedNotification
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_handler import DataHandler
from exengine.kernel.data_storage_base import DataStorage
from exengine.kernel.notification_base import DataStoredNotification
from exengine.kernel.data_coords import DataCoordinates


# Mock classes for testing
class CustomNotification(Notification):
    category = NotificationCategory.Event
    description = "Custom notification for testing"


class CustomEvent(ExecutorEvent):
    notification_types = [CustomNotification]

    def execute(self):
        return "Custom event executed"


@pytest.fixture
def mock_storage():
    return Mock(spec=DataStorage)

@pytest.fixture
def mock_execution_engine(monkeypatch):
    mock_engine = Mock(spec=ExecutionEngine)
    monkeypatch.setattr(ExecutionEngine, 'get_instance', lambda: mock_engine)
    return mock_engine


@pytest.fixture
def data_handler(mock_storage, mock_execution_engine):
    return DataHandler(mock_storage, _executor=mock_execution_engine)


def test_notification_types_inheritance():
    """
    Test that notification subclasses that declare their own notification types
    are included in the list of valid notification types for an event,
    in addition to the default notification types.
    """
    assert set(CustomEvent.notification_types) == {CustomNotification, EventExecutedNotification}


def test_event_completion_notification(mock_execution_engine):
    """
    Test that notifications are posted when an event completes.
    """
    event = CustomEvent()
    event._pre_execution(mock_execution_engine)
    event._post_execution(mock_execution_engine)

    # Check if the notification was published
    mock_execution_engine.publish_notification.assert_called_once()
    published_notification = mock_execution_engine.publish_notification.call_args[0][0]
    assert isinstance(published_notification, EventExecutedNotification)


def test_custom_notification_posting(mock_execution_engine):
    """
    Test that custom notifications can be posted during event execution.
    """
    event = CustomEvent()
    mock_future = Mock()
    event._pre_execution(mock_execution_engine)
    event._future_weakref = Mock(return_value=mock_future)

    custom_notification = CustomNotification()
    event.publish_notification(custom_notification)

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
    event._pre_execution(Mock())

    with pytest.warns(UserWarning):
        event.publish_notification(InvalidNotification())


def test_event_exception_in_notification(mock_execution_engine):
    """
    Test that when an event raises an exception, it's included in the completion notification.
    """
    event = CustomEvent()
    event._pre_execution(mock_execution_engine)
    test_exception = ValueError("Test exception")
    event._post_execution(mock_execution_engine, exception=test_exception)

    mock_execution_engine.publish_notification.assert_called_once()
    published_notification = mock_execution_engine.publish_notification.call_args[0][0]
    assert isinstance(published_notification, EventExecutedNotification)
    assert published_notification.payload == test_exception


def test_data_stored_notification(data_handler, mock_execution_engine):
    sample_coordinates = DataCoordinates(time=0)
    data_handler.put(sample_coordinates, np.array([1,2,3,4]), {}, None)

    data_handler.finish()
    data_handler.await_completion()

    mock_execution_engine.publish_notification.assert_called_once()
    notification = mock_execution_engine.publish_notification.call_args[0][0]
    assert isinstance(notification, DataStoredNotification)
    assert notification.payload == sample_coordinates