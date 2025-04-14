import warnings
from typing import Optional, Any, ClassVar, Type, Callable
from abc import ABC, abstractmethod, ABCMeta
import weakref
import inspect

from .notification_base import Notification
from .notification_base import EventExecutedNotification
from .ex_future import ExecutionFuture


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


class ExecutorEvent(ABC, metaclass=_ExecutorEventMeta):
    # Base events just have an event executed event. Subclasses can also add their own lists
    # of notifications types, and the metaclass will merge them into one big list
    notification_types: ClassVar[list[Type[Notification]]] = [EventExecutedNotification]
    _thread_name: Optional[str] = None

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._num_retries_on_exception = 0
        self._priority = 1 # lower number means higher priority
        self._finished = False
        self._initialized = False
        self.instance = None # Set to a DeviceBase object to run on the thread of that device.
        # Check for method-level preferred thread name first, then class-level
        self._thread_name = getattr(self.execute, '_thread_name', None) or getattr(self.__class__, '_thread_name', None)

    def can_start(self, condition) -> bool:
        """
        Check if the event can start execution. This method is called by the executor before starting the event.
        """
        return True


    def _pre_execution(self, engine) -> ExecutionFuture:
        """
        This is called automatically by the Executor and should not be overriden by subclasses.
        """
        if self._initialized:
            raise Exception("Event has already been initialized. Events cannot be reused.")
        self._initialized = True
        self._engine = engine

        future = ExecutionFuture(event=self)
        # Store this as a weakref so that if user code does not hold a reference to the future,
        # it can be garbage collected. The event should not give access to the future to user code
        self._future_weakref = weakref.ref(future)
        return future

    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the event. This event is called by the executor, and should be overriden by subclasses to implement
        the event's functionality.
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
        future : ExecutionFuture = self._future_weakref()
        if future is not None:
            future._notify_of_event_notification(notification)
        self._engine.publish_notification(notification)

    def _post_execution(self, return_value: Optional[Any] = None, exception: Optional[Exception] = None):
        """
        Method that is called after the event is executed to update acquisition futures about the event's status.
        This is called automatically by the Executor and should not be overriden by subclasses.

        This method signals that the future is complete, so that any thread waiting on it can proceed.

        Args:
            return_value: Return value of the event
            exception: Exception that was raised during execution, if any
        """
        try:
            if self._future_weakref is None:
                raise Exception("Future not set for event")
            self.finished = True
            try:
                if self._engine.__class__.__name__ != "ExecutionEngine":
                    raise Exception("Engine is not an ExecutionEngine") # for debugging
                self._engine.publish_notification(EventExecutedNotification(payload=exception))
            finally:
                future = self._future_weakref()
                if future is not None:
                    print(f"Event {self} finished, notifying future")
                    future._notify_execution_complete(return_value, exception)
        except Exception:
            if exception is not None:
                pass # don't raise an exception from inside the exception handler
            else:
                raise



class AnonymousCallableEvent(ExecutorEvent):
    """
    An event that wraps a callable object and calls it when the event is executed.

    The callable object should take no arguments and optionally return a value.
    """
    def __init__(self, callable_obj: Callable[[], Any]):
        # Check if the callable has no parameters (except for 'self' in case of methods)
        if not callable(callable_obj):
            raise TypeError("Callable object must be a function or method")
        if not inspect.signature(callable_obj).bind():
            raise TypeError("Callable object must take no arguments")

        super().__init__()
        self.callable_obj = callable_obj


    def execute(self):
        return self.callable_obj()