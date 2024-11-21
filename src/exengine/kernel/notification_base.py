from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, ClassVar
from enum import Enum
from abc import ABC
from datetime import datetime
from dataclasses import field
import uuid
from .data_coords import DataCoordinates


TNotificationPayload = TypeVar('TNotificationPayload')

class NotificationCategory(Enum):
    Event = 'Update from the execution of an acquisition event'
    Data = 'Data has been acquired by a data producing event'
    Storage = 'Update from a data Storage object'
    Device = 'Update from a Device object'



@dataclass
class Notification(ABC, Generic[TNotificationPayload]):
    """
    Base class for creating notifications. Notifications are dispatched by the execution engine and related components
    to provide asynchronous status updates. They can support a payload of arbitrary type, which can be used to pass
    data or other information along with the notification. However, notifications are designed to be numerous and
    lightweight, so using the payload to pass large amounts or complex data is discouraged.

    To create a notification, subclass this class and set the category and description class variables and optionally
    define a payload type. The Generic type parameter should be the type of the payload, if any. @dataclass can
    be used to simplify the definition of notifications classes, but is not required.

    For example:

    >>>    @dataclass
    >>>    class DataAcquired(Notification[DataCoordinates]):
    >>>
    >>>        # Define the category and description of the notification shared by all instances of this class
    >>>        category = NotificationCategory.Data
    >>>        description = "Data has been acquired by a camera or other data-producing device and is now available"
    >>>
    >>>        # payload is the data coordinates of the acquired
    >>>
    >>>    # Create an instance of the notification
    >>>    notification = DataAcquired(payload=DataCoordinates(t=1, y=2, channel="DAPI"))

    """
    timestamp: datetime = field(default_factory=datetime.now, init=False)
    category: ClassVar[NotificationCategory]
    description: ClassVar[str]
    payload: Optional[TNotificationPayload] = None
    _uuid: uuid.UUID = field(default_factory=uuid.uuid4, init=False)

    def __hash__(self):
        return hash(self._uuid)

    def __eq__(self, other):
        if not isinstance(other, Notification):
            return NotImplemented
        return self._uuid == other._uuid


@dataclass
class EventExecutedNotification(Notification[Optional[Exception]]):
    """
    Notification that is posted when an ExecutionEvent completes.
    If the event raised an exception, it is passed as the payload.
    """
    category = NotificationCategory.Event
    description = "An ExecutionEvent has completed successfully"
    payload: Optional[Exception] = None

@dataclass
class DataStoredNotification(Notification[DataCoordinates]):
    """
    Notification that is posted when data is stored by a Storage object.
    """
    category = NotificationCategory.Data
    description = "Data has been stored in a Storage object"
    payload: DataCoordinates