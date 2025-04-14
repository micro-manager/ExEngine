"""
Class that executes acquistion events across a pool of threads
"""
import threading
import traceback
from dataclasses import dataclass
from typing import Union, Callable, Type, Dict, Any, Optional
import queue
import inspect

from .notification_base import Notification, NotificationCategory
from .ex_event_base import ExecutorEvent, AnonymousCallableEvent
from .ex_future import ExecutionFuture
from .queue import Queue, Shutdown

_MAIN_THREAD_NAME = 'MainExecutorThread'
_ANONYMOUS_THREAD_NAME = 'AnonymousExecutorThread'

class DeviceBase:
    __slots__ = ('_engine', '_device', '_executor')
    def __init__(self, engine, wrapped_device):
        self._engine = engine
        self._device = wrapped_device
        self._executor = _ExecutionThreadManager(self._engine, name=self.__class__.__name__ + "Worker", sequential=True)

    def submit(self, event: Union[ExecutorEvent | Callable]) -> "ExecutionFuture":
        """
        Submit an event to run on the thread of this device

        todo: add thread safety / locking
        todo: think about Callable argument use case. Is this common enough to warrant special treatment?
        Thread safety / locking:
            A device can be associated to a control thread (i.e. the `control_thread` attribute is set).
            In that case, only the control thread may submit events to the device, and an exception is raised
            if any other thread submits an event.
            Each device is initially controlled by the thread that created it. The `control_thread` can be cleared
            by calling `make_multi_threaded()`, enabling any thread to submit events to the device.
            To obtain temporary exclusive control over a device, use the `with device:` syntax.
            This will block until the ownership is released by the owning thread, and release control when the block is exited.
        """
        return self._executor.submit(event)

    def abort(self):
        """Abort all pending events on this device"""
        self._executor.abort()

    def _shutdown(self, immediately=False, wait=False):
        """
        Terminates the device thread and destroys the underlying device object.

        This function is called by the engine when the device is removed explicitly (see __delitem__) or when
        the engine is shut down.
        It performs the following actions (atomically):
            - Clears all current events (if immediately is True)
            - Schedule a shutdown event on the device thread, which removes the internal reference to the device, causing it to be garbage collected.
            - Signals the device thread to finish

        All subsequent access to the device will fail with a Shutdown exception because the thread is shut down.
        todo: Devices or subsystems may require some actions for a graceful shutdown. How can the user/library developer specify this?

        Args:
            immediately: If True, all pending events are discarded.
                If False, the device finishes all pending events before shutting down.
            wait: If True, waits for the device thread to finish before returning. This should not really be necessary in most cases.

        """
        def do_shutdown():
            self._engine = None
            self._device = None

        self._executor.shutdown(immediately, wait, AnonymousCallableEvent(do_shutdown))

    @staticmethod
    def map_names(class_dict):
        """
        Maps the names of the class to the device
        """
        pass

class ExecutionEngine:
    _debug = False

    def __init__(self):
        self._exceptions = Queue()
        self._devices = {}
        first_worker = _ExecutionThreadManager(self, name=_MAIN_THREAD_NAME + "0", sequential=False)
        other_workers = [_ExecutionThreadManager(self, name=_MAIN_THREAD_NAME + str(i), sequential=False, shared=first_worker) for i in range(3)]
        self._workers = [first_worker] + other_workers
        self._notification_queue = Queue()
        self._notification_subscribers: list[Callable[[Notification], None]] = []
        self._notification_subscriber_filters: list[Union[NotificationCategory, Type]] = []
        self._notification_lock = threading.Lock()
        self._notification_thread = None


    def register(self, id: str, obj: object, schema = DeviceBase):
        """
        Wraps an object for use with the ExecutionEngine

        The wrapper exposes the public properties and attributes of the wrapped object, converting
        all get and set access, as well as method calls to Events.
        Private methods and attributes are not exposed.

        After wrapping, the original object should not be used directly anymore.
        All access should be done through the wrapper, which takes care of thread safety, synchronization, etc.

        Args:
            id: Unique id (name) of the device, used by the ExecutionEngine.
            obj: object to wrap. The object should only be registered once. Use of the original object should be avoided after wrapping,
                since access to the original object is not thread safe or otherwise managed by the ExecutionEngine.
        """
        #
        if any(d is obj for d in self._devices) or isinstance(obj, DeviceBase):
            raise ValueError("Object already registered")

        # get a list of all properties and methods, including the ones in base classes
        # Also process class annotations, for attributes that are not properties
        class_hierarchy = inspect.getmro(obj.__class__)
        all_dict = {}
        for c in class_hierarchy[::-1]:
            all_dict.update(c.__dict__)
            annotations = c.__dict__.get('__annotations__', {})
            all_dict.update(annotations)

        # add all attributes that are not already in the dict
        for n, a in obj.__dict__.items():
            if not n.startswith("_") and n not in all_dict:
                all_dict[n] = None

        # create the wrapper class
        class_dict = {}
        slots = []
        for name, attribute in all_dict.items():
            if name.startswith('_'):
                continue  # skip private attributes

            if inspect.isfunction(attribute):
                def method(self, *args, _name=name, **kwargs):
                    event = MethodCallEvent(method_name=_name, args=args, kwargs=kwargs, instance=self._device)
                    return self.submit(event)

                class_dict[name] = method
            else:
                def getter(self, _name=name):
                    event = GetAttrEvent(attr_name=_name, instance=self._device, method=getattr)
                    return self.submit(event).await_execution()

                def setter(self, value, _name=name):
                    event = SetAttrEvent(attr_name=_name, value=value, instance=self._device, method=setattr)
                    self.submit(event).await_execution()

                has_setter = not isinstance(attribute, property) or attribute.fset is not None
                class_dict[name] = property(getter, setter if has_setter else None, None, f"Wrapped attribute {name}")
                if not isinstance(attribute, property):
                    slots.append(name)

        class_dict['__slots__'] = () # prevent addition of new attributes.
        schema.map_names(class_dict)
        WrappedObject = type('_' + obj.__class__.__name__, (schema,), class_dict)
        # todo: cache dynamically generated classes
        wrapped = WrappedObject(self,obj)
        self._devices[id] = wrapped
        return wrapped

    def subscribe_to_notifications(self, subscriber: Callable[[Notification], None],
                                   notification_type: Union[NotificationCategory, Type] = None
                                   ) -> None:
        """
        Subscribe an object to receive notifications.

        Args:
            subscriber (Callable[[Notification], Any]): A callable that takes a single
                Notification object as an argument.
            notification_type (Union[NotificationCategory, Type], optional): The type of notification to subscribe to.
              this can either be a NotificationCategory or a specific subclass of Notification.

        Returns:
            None

        Raises:
            TypeError: If the subscriber is not a callable taking exactly one argument.
        """
        with self._notification_lock:
            if len(self._notification_subscribers) == 0:
                self._notification_thread = threading.Thread(target=self._notification_thread_run)
                self._notification_thread.start()
            self._notification_subscribers.append(subscriber)
            self._notification_subscriber_filters.append(notification_type)

    def unsubscribe_from_notifications(self, subscriber: Callable[[Notification], None]) -> None:
        """
        Unsubscribe an object from receiving notifications.

        Args:
            subscriber (Callable[[Notification], Any]): The callable that was previously subscribed to notifications.

        Returns:
            None
        """
        with self._notification_lock:
            index = self._notification_subscribers.index(subscriber)
            self._notification_subscribers.pop(index)
            self._notification_subscriber_filters.pop(index)

    def _notification_thread_run(self):
        try:
            while True:
                notification = self._notification_queue.get()
                try:
                    with self._notification_lock:
                        for subscriber, filter in zip(self._notification_subscribers, self._notification_subscriber_filters):
                            if filter is not None and isinstance(filter, type) and not isinstance(notification, filter):
                                continue  # not interested in this type
                            if filter is not None and isinstance(filter, NotificationCategory) and notification.category != filter:
                                continue
                            subscriber(notification)
                except Exception as e:
                    self._log_exception(e)
                finally:
                    self._notification_queue.task_done()
        except Shutdown:
            pass

    def publish_notification(self, notification: Notification):
        """
        Publish a notification by adding it the publish queue
        """
        self._notification_queue.put(notification)

    def __getitem__(self, device_id: str):
        """
        Get a device by name

        Args:
            device_id: unique id of the device that was used in the call to register_device.
        Returns:
            device
        Raises:
            KeyError if a device with this id is not found.
        """
        return self._devices[device_id]

    def __delitem__(self, device_id: str):
        """
        Remove a device from the engine and shut it down.
        If the device is still busy, it is allowed to finish what it was doing.
        """
        device = self._devices[device_id]
        device._shutdown(immediately=False, wait=False)
        del self._devices[device_id]


    @staticmethod
    def set_debug_mode(debug):
        ExecutionEngine._debug = debug

    def _log_exception(self, exception):
        self._exceptions.put(exception)

    def check_exceptions(self):
        """
        Check if any exceptions have been raised during the execution of events and raise them if so
        """
        exceptions = self._exceptions
        self._exceptions = queue.Queue()
        exceptions = list(exceptions.queue)
        if exceptions:
            if len(exceptions) == 1:
                raise exceptions[0]
            else:
                raise MultipleExceptions(exceptions)

    def submit(self, event: Union[ExecutorEvent | Callable]) -> ExecutionFuture:
        """
        Submit an event for execution in the worker thread pool.
        Events are executed as soon as the conditions for execution are met.

        The execution threads test if an event is ready to execute by calling the `can_start` method of the event.
        If the event is not ready to start, the event is skipped and the next event is checked.
        After all events have been checked, the threads are suspended.

        Events that report can_start = False are responsible for waking up the suspended threads as soon as they become ready to be executed.
        To enable this, can_start takes a notification listener as an argument, which is notified when the event becomes ready to start (or at least
        needs to be re-evaluated).

        todo: prioritize events?


        See Also:
            `DeviceBase.submit` for submitting events to a specific device.

        Returns:
        --------
        ExecutionFuture.

        Notes:
        ------
        - If a callable object with no arguments is submitted, it will be automatically wrapped in a AnonymousCallableEvent.
        """
        return self._workers[0].submit(event)

    def shutdown(self, immediately=False, wait=True):
        """
        Stop all devices, then stop all threads in the thread pool

        Args:
            immediately: If True, all pending events are discarded.
                If False, the device finishes all pending events before shutting down.
            wait: If True, waits for the device thread to finish and the device to be destroyed
        """
        for device in self._devices.values():
            device._shutdown(immediately, False) # first signal all devices to shut down
        for device in self._devices.values():
            device._shutdown(immediately, True) # then wait for all devices to finish shutting down

        # this will terminate all workers
        self._workers[0].shutdown(immediately, wait)

        # Make sure the notification thread is stopped if it was started at all
        if self._notification_thread is not None:
            self._notification_queue.shutdown(immediately)
            if wait:
                self._notification_thread.join()

class _ExecutionThreadManager:
    """
    Class which manages a single thread that executes events from a queue, one at a time.
    """
    def __init__(self, engine: ExecutionEngine, name: str, sequential:bool, shared: Optional["_ExecutionThreadManager"] = None):
        self._engine = engine
        self._sequential = sequential
        if shared:
            self._queue = shared._queue
            self._queue_condition = shared._queue_condition
        else:
            self._queue = []
            self._queue_condition = threading.Condition(lock=DebugLock())
            self._queue_condition.terminating = False # add custom property to the condition

        self._thread = threading.Thread(target=self._run_thread, name=name)
        self._thread.start()

    def submit(self, event: Union[ExecutorEvent | Callable]) -> ExecutionFuture:
        if not isinstance(event, ExecutorEvent):
            event = AnonymousCallableEvent(event)

        if self._queue_condition.terminating:
            raise Shutdown  # we are shutting down, so don't accept new events

        if event._finished:
            # this is unrecoverable, never retry
            raise RuntimeError("Event ", event, " was already executed")

        # todo: rethink lifecycle of events. Perhaps the event itself can be the Future?
        future = event._pre_execution(self._engine)
        with self._queue_condition:
            self._queue.append(event)
            self._queue_condition.notify()

        return future

    def _run_thread(self):
        """Main loop for worker threads.

        A thread is stopped by sending a TerminateThreadEvent to it, which raises a Shutdown exception.
        """
        while True:
            with self._queue_condition:
                event = None
                if len(self._queue) > 0:
                    if self._sequential and self._queue[0].can_start(self._queue_condition):
                        # Get the next event from the queue.
                        event = self._queue.pop(0)
                    else:
                        # Finds the first event that is ready to start.
                        event = next((e for e in self._queue if e.can_start(self._queue_condition)), None)
                        self._queue.remove(event)
                elif self._queue_condition.terminating:
                    # Queue empty and terminating.
                    break

                if event is None:
                    self._queue_condition.wait()
                    continue

            try:
                result = event.execute()
                event._post_execution(result)
            except Exception as e:
                self._engine._log_exception(e)
                event._post_execution(exception=e)  # cannot raise an exception


    def shutdown(self, immediately:bool=False, wait:bool=True, final_event: Optional[ExecutorEvent]=None):
        """
        Shutdown the thread.

        Calling this function multiple times is safe. When called with `immediately=True`, all pending events, including the final event, are discarded.
        When multiple callse are made with `immediately=False`, all final_events are executed in the order they were provided.

        Args:
            immediately: If True, all pending events are discarded.
                If False, the device finishes all pending events before shutting down.
            wait: If True, waits for the device thread to finish and the device to be destroyed
            final_event: If provided, this final event is injected in the queue before shutting it down.
                This final event is always executed.


        Raises:
            Shutdown: If the thread is already shutting down
        """
        with self._queue_condition:
            if immediately: # note: we cannot call 'abort' because the lock in the condition variable is not reentrant
                for event in self._queue:
                    event._post_execution(exception=Shutdown()) # abort all events
                self._queue.clear()
            if final_event is not None:
                self._queue.append(final_event)
            self._queue_condition.terminating = True
            self._queue_condition.notify_all()

        if wait:
            self._thread.join()

    def abort(self):
        """Abort all pending events on this device"""
        with self._queue_condition:
            for event in self._queue:
                event._post_execution(exception=Shutdown()) # abort all events. Todo: custom exception?
            self._queue.clear()


@dataclass
class MethodCallEvent(ExecutorEvent):
    def __init__(self, method_name: str, args: tuple, kwargs: Dict[str, Any], instance: Any):
        super().__init__()
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs
        self.instance = instance

    def execute(self):
        method = getattr(self.instance, self.method_name)
        return method(*self.args, **self.kwargs)

class ShutdownEvent(ExecutorEvent):
    def execute(self):
        raise Shutdown()

class GetAttrEvent(ExecutorEvent):

    def __init__(self, attr_name: str, instance: Any, method: Callable):
        super().__init__()
        self.attr_name = attr_name
        self.instance = instance
        self.method = method

    def execute(self):
        value = self.method(self.instance, self.attr_name)
        print(f"Got {self.attr_name} with value {value}")
        return value


class SetAttrEvent(ExecutorEvent):

    def __init__(self, attr_name: str, value: Any, instance: Any, method: Callable):
        super().__init__()
        self.attr_name = attr_name
        self.value = value
        self.instance = instance # wrapped object
        self.method = method

    def execute(self):
        self.method(self.instance, self.attr_name, self.value)
        print(f"Set {self.attr_name} to {self.value}")


class MultipleExceptions(Exception):
    def __init__(self, exceptions: list[Exception]):
        self.exceptions = exceptions
        messages = [f"{type(e).__name__}: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}" for e in exceptions]
        super().__init__("Multiple exceptions occurred:\n" + "\n".join(messages))

class DebugLock:
    """Helper class for debugging deadlocks. Can be removed later.
    It seems that the debugger cannot (always?) suspend threads that are blocked on a lock.
    Therefore, we cannot use the debugger to inspect the state of the threads and identify readlocks.
    As a partial workaround, put a breakpoint on the 'pass' line below to suspend a thread that is waiting for a DebugLock (used in Condition variables)."""
    def __init__(self):
        self._lock = threading.Lock()

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args):
        self.release()

    def acquire(self, blocking=True, timeout=-1):
        if blocking and timeout == -1:
            while not self._lock.acquire(True, 1.0):
                pass # breakpoint here
            return True
        else:
            self._lock.acquire(blocking, timeout)

    def release(self):
        self._lock.release()