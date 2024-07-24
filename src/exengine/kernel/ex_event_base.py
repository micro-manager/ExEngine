import warnings
import numpy as np
from typing import Optional, Any,ClassVar, Type, List, Dict, Union, Iterable
from abc import ABC, abstractmethod, ABCMeta
import weakref
from dataclasses import dataclass, field
from exengine.kernel.notification_base import Notification

from typing import TYPE_CHECKING

from kernel.notification_base import EventExecutedNotification
from exengine.kernel.data_coords import DataCoordinates, DataCoordinatesIterator
from exengine.kernel.data_handler import DataHandler

# if TYPE_CHECKING: # avoid circular imports
from exengine.kernel.ex_future import ExecutionFuture


class _ExecutorEventMeta(ABCMeta):
    """
    Metaclass for ExecutorEvent that collects all notification types and capabilities from base classes and subclasses,
    and dynamically generates context and future classes with the methods from the capabilities added to them.
    """
    def __new__(mcs, name, bases, attrs):
        # Collect notifications from all base classes
        all_notifications = set()
        for base in bases:
            if hasattr(base, 'notification_types'):
                all_notifications.update(base.notification_types)

        # Add notifications defined in the current class
        if 'notification_types' in attrs:
            all_notifications.update(attrs['notification_types'])

        # Set the combined notifications
        attrs['notification_types'] = list(all_notifications)

        # Collect capabilities of corresponding futures from all mixin classes
        future_capabilities = set()
        for base in bases:
            if hasattr(base, '__future_capability__'):
                future_capabilities.add(base.__future_capability__)
        attrs['__future_capabilities__'] = frozenset(future_capabilities)
        return super().__new__(mcs, name, bases, attrs)


@dataclass
class ExecutorEvent(ABC, metaclass=_ExecutorEventMeta):
    _num_retries_on_exception: int = field(default=0, kw_only=True)
    # Base events just have an event executed event. Subclasses can also add their own lists
    # of notifications types, and the metaclass will merge them into one big list
    notification_types: ClassVar[List[Type[Notification]]] = [EventExecutedNotification]
    finished = False

    def _create_future(self) -> ExecutionFuture:
        return ExecutionFuture(event=self)

    def _pre_execution(self, engine):
        """
        This is called automatically by the Executor and should not be overriden by subclasses.
        """
        self._engine = engine
        if self.finished:
            raise Exception("Event has already been executed")

    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the event. This event is called by the executor, and should be overriden by subclasses to implement
        the event's functionality.

        Args:
            context: Execution context object that holds information related to this specific execution of the event.
            (Since the same event can be reused multiple times, this object is unique to each execution of the event.)
        """
        pass

    def publish_notification(self, notification: Notification):
        """
        Publish a notification that will be accessible through Futures and made available to any notification
        subscribers.
        """
        # Check that the notification is of a valid type
        if notification.__class__ not in self.notification_types:
            warnings.warn(f"Notification type {notification.__class__} is not in the list of valid notification types"
                          f"for this event. It should be added in the Event's constructor.")
        if self._future_weakref is None:
            raise Exception("Future not set for event")
        future = self._future_weakref()
        if future is not None:
            future._notify_of_event_notification(notification)
        self._engine.publish_notification(notification)

    def _set_future(self, future: 'ExecutionFuture'):
        """
        Called by the executor to set the future associated with this event
        """
        # Store this as a weakref so that if user code does not hold a reference to the future,
        # it can be garbage collected. The event should not give access to the future to user code
        self._future_weakref = weakref.ref(future)

    def _post_execution(self, return_value: Optional[Any] = None, exception: Optional[Exception] = None):
        """
        Method that is called after the event is executed to update acquisition futures about the event's status.
        This is called automatically by the Executor and should not be overriden by subclasses.

        Args:
            return_value: Return value of the event
            exception: Exception that was raised during execution, if any
        """
        if self._future_weakref is None:
            raise Exception("Future not set for event")
        future = self._future_weakref()
        if future is not None:
            future._notify_execution_complete(return_value, exception)
        self.finished = True
        self._engine.publish_notification(EventExecutedNotification(payload=exception))

    def _request_stop(self):
        """
        Called by the future
        """
        self._stop_requested = True


############################################################################################################
## Special Capabilities for Events
############################################################################################################

@dataclass
class DataProducing:
    """
    Acquisition events that produce data should inherit from this class. They are responsible for putting data
    into the output queue. This class provides a method for putting data into the output queue. It must be passed
    a DataHandler object that will handle the data, and an image_coordinate_iterator object that generates the
    coordinates of each piece of data (i.e. image) that will be produced by the event. For example, {time: 0},
    {time: 1}, {time: 2} for a time series acquisition.
    """
    # Data handling
    data_coordinate_iterator: Union[DataCoordinatesIterator,
        Iterable[DataCoordinates], Iterable[Dict[str, Union[int, str]]]]
    _data_handler: DataHandler = field(default=None)  # This can be added at runtime


    def __post_init__(self):
        # auto convert it
        self.data_coordinate_iterator = DataCoordinatesIterator.create(self.data_coordinate_iterator)


    def put_data(self, data_coordinates: DataCoordinates, image: np.ndarray, metadata: Dict):
        """
        Put data into the output queue
        """
        # TODO: replace future weakref with just a callable?
        self._data_handler.put(data_coordinates, image, metadata, self._future_weakref())

    def _check_if_coordinates_possible(self, coordinates):
        """
        Check if the given coordinates are possible for this event. raise a ValueError if not
        """
        possible = self.data_coordinate_iterator.might_produce_coordinates(coordinates)
        if possible is False:
            raise ValueError("This event is not expected to produce the given coordinates")
        elif possible is None:
            # TODO: suggest a better way to do this (ie a smart generator that knows if produced coordinates are valid)
            warnings.warn("This event may not produce the given coordinates")




@dataclass
class Stoppable:
    """
    This capability adds the ability to stop ExecutorEvents that are running or ar going to run. The implementation
    of the event is responsible for checking if is_stop_requested() returns True and stopping their execution if it
    does. When stopping, an orderly shutdown should be performed, unlike when aborting, which should be immediate.
    The details of what such an orderly shutdown entails are up to the implementation of the event.
    """

    _stop_requested: bool = field(default=False, init=False)

    def is_stop_requested(self) -> bool:
        return self._stop_requested

    def _request_stop(self):
        self._stop_requested = True


@dataclass
class Abortable:
    """
    Acquisition events that can be aborted should inherit from this class. They are responsible for checking if
    is_abort_requested() returns True and aborting their execution if it does. When aborted, the event should
    immediately stop its execution.
    """

    _abort_requested: bool = field(default=False, init=False)

    def is_abort_requested(self) -> bool:
        return self._abort_requested

    def _request_abort(self):
        self._abort_requested = True




