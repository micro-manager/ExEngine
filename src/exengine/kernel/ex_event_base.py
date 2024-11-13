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
        self._finished = False
        self._initialized = False
        # Check for method-level preferred thread name first, then class-level
        self._thread_name = getattr(self.execute, '_thread_name', None) or getattr(self.__class__, '_thread_name', None)

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

        Args:
            return_value: Return value of the event
            exception: Exception that was raised during execution, if any
        """
        if self._future_weakref is None:
            raise Exception("Future not set for event")
        future = self._future_weakref()
        self.finished = True
        self._engine.publish_notification(EventExecutedNotification(payload=exception))
        if future is not None:
            future._notify_execution_complete(return_value, exception)



class AnonymousCallableEvent(ExecutorEvent):
    """
    An event that wraps a callable object and calls it when the event is executed.

    The callable object should take no arguments and optionally return a value.
    """
    def __init__(self, callable_obj: Callable[[], Any]):
        super().__init__()
        self.callable_obj = callable_obj
        # Check if the callable has no parameters (except for 'self' in case of methods)
        if not callable(callable_obj):
            raise TypeError("Callable object must be a function or method")
        signature = inspect.signature(callable_obj)
        if not all(param.default != param.empty or param.kind == param.VAR_POSITIONAL for param in
               signature.parameters.values()):
            raise TypeError("Callable object must take no arguments")


    def execute(self):
        return self.callable_obj()