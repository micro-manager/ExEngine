"""
Class that executes acquistion events across a pool of threads
"""
import threading
from collections import deque
from typing import Deque
import warnings
import traceback
from typing import Union, Iterable, Callable, Type
import queue
import inspect

from .notification_base import Notification, NotificationCategory
from .ex_event_base import ExecutorEvent, AnonymousCallableEvent
from .ex_future import ExecutionFuture

_MAIN_THREAD_NAME = 'MainExecutorThread'
_ANONYMOUS_THREAD_NAME = 'AnonymousExecutorThread'

class MultipleExceptions(Exception):
    def __init__(self, exceptions: list[Exception]):
        self.exceptions = exceptions
        messages = [f"{type(e).__name__}: {''.join(traceback.format_exception(type(e), e, e.__traceback__))}" for e in exceptions]
        super().__init__("Multiple exceptions occurred:\n" + "\n".join(messages))

class ExecutionEngine:

    _instance = None
    _lock = threading.Lock()
    _debug = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._exceptions = queue.Queue()
        self._devices = {}
        self._notification_queue = queue.Queue()
        self._notification_subscribers: list[Callable[[Notification], None]] = []
        self._notification_subscriber_filters: list[Union[NotificationCategory, Type]] = []
        self._notification_lock = threading.Lock()
        self._notification_thread = None
        self._shutdown_event = threading.Event()

        with self._lock:
            if not hasattr(self, '_initialized'):
                self._thread_managers = {}
                self._start_new_thread(_MAIN_THREAD_NAME)
                self._initialized = True

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
        while not self._shutdown_event.is_set() or self._notification_queue.qsize() > 0:
            try:
                notification = self._notification_queue.get(timeout=1)
            except queue.Empty:
                continue
            with self._notification_lock:
                for subscriber, filter in zip(self._notification_subscribers, self._notification_subscriber_filters):
                    if filter is not None and isinstance(filter, type) and not isinstance(notification, filter):
                        continue  # not interested in this type
                    if filter is not None and isinstance(filter, NotificationCategory) and notification.category != filter:
                        continue
                    subscriber(notification)

    def publish_notification(self, notification: Notification):
        """
        Publish a notification by adding it the publish queue
        """
        self._notification_queue.put(notification)

    @classmethod
    def get_instance(cls) -> 'ExecutionEngine':
        return cls._instance

    @classmethod
    def get_device(cls, device_name):
        """
        Get a device by name
        """
        if device_name not in cls.get_instance()._devices:
            raise ValueError(f"No device with name {device_name}")
        return cls.get_instance()._devices[device_name]

    @classmethod
    def register_device(cls, name, device):
        """
        Called automatically when a Device is created so that the ExecutionEngine can keep track of all devices
        and look them up by their string names
        """
        # Make sure there's not already a device with this name
        executor = cls.get_instance()
        if name is not None:
            # only true after initialization, but this gets called after all the subclass constructors
            if name in executor._devices and executor._devices[name] is not device:
                raise ValueError(f"Device with name {name} already exists")
            executor._devices[name] = device

    @classmethod
    def on_main_executor_thread(cls):
        """
        Check if the current thread is an executor thread
        """
        return threading.current_thread().name is _MAIN_THREAD_NAME

    @classmethod
    def on_any_executor_thread(cls):
        if ExecutionEngine.get_instance() is None:
            raise RuntimeError("on_any_executor_thread: ExecutionEngine has not been initialized")
        result = (hasattr(threading.current_thread(), 'execution_engine_thread')
                  and threading.current_thread().execution_engine_thread)
        return result

    def _start_new_thread(self, name):
        self._thread_managers[name] = _ExecutionThreadManager(name)

    def set_debug_mode(self, debug):
        ExecutionEngine._debug = debug

    @classmethod
    def _log_exception(cls, exception):
        ExecutionEngine.get_instance()._exceptions.put(exception)

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

    def submit(self, event_or_events: Union[ExecutorEvent, Iterable[ExecutorEvent]], thread_name=None,
               prioritize: bool = False, use_free_thread: bool = False) -> Union[ExecutionFuture, Iterable[ExecutionFuture]]:
        """
        Submit one or more acquisition events or callable objects for execution.

        This method handles the submission of acquisition events or callable objects to be executed on active threads.
        It provides options for event prioritization, thread allocation, and performance optimization.


        Parameters:
        -----------
        event_or_events : Union[ExecutorEvent, Iterable[ExecutorEvent], Callable[[], Any], Iterable[Callable[[], Any]]]
            A single ExecutorEvent, an iterable of ExecutorEvents, or a callable object with no arguments.

        thread_name : str, optional (default=None)
            Name of the thread to submit the event to. If None, the thread is determined by the
            'use_free_thread' parameter.

        prioritize : bool, optional (default=False)
            If True, execute the event(s) before any others in the queue on its assigned thread.
            Useful for system-wide changes affecting other events, like hardware adjustments.

        use_free_thread : bool, optional (default=False)
            If True, execute the event(s) on an available thread with an empty queue, creating a new thread if needed.
            Useful for operations like cancelling or stopping events awaiting signals.
            If False, execute on the primary thread.

        Returns:
        --------
        Union[AcquisitionFuture, Iterable[AcquisitionFuture]]
            For a single event or callable: returns a single ExecutionFuture.
            For multiple events: returns an Iterable of ExecutionFutures.

        Notes:
        ------
        - Use 'prioritize' for critical system changes that should occur before other queued events.
        - 'use_free_thread' is essential for operations that need to run independently, like cancellation events.
        - If a callable object with no arguments is submitted, it will be automatically wrapped in a AnonymousCallableEvent.
        """
        # Auto convert single callable to event
        if callable(event_or_events) and len(inspect.signature(event_or_events).parameters) == 0:
            event_or_events = AnonymousCallableEvent(event_or_events)

        if isinstance(event_or_events, (ExecutorEvent, Callable)):
            event_or_events = [event_or_events]

        events = []
        for event in event_or_events:
            if callable(event):
                events.append(AnonymousCallableEvent(event))
            elif isinstance(event, ExecutorEvent):
                events.append(event)
            else:
                raise TypeError(f"Invalid event type: {type(event)}. "
                                f"Expected ExecutorEvent or callable with no arguments.")

        futures = tuple(self._submit_single_event(event, thread_name or getattr(event, '_thread_name', None),
                                                  use_free_thread, prioritize) for event in events)
        if len(futures) == 1:
            return futures[0]
        return futures

    def _submit_single_event(self, event: ExecutorEvent, thread_name=None, use_free_thread: bool = False,
                             prioritize: bool = False):
        """
        Submit a single event for execution
        """
        future = event._pre_execution(self)
        if use_free_thread:
            need_new_thread = True
            if thread_name is not None:
                warnings.warn("thread_name may be ignored when use_free_thread is True")
            # Iterate through main thread and anonymous threads
            if self._thread_managers[_MAIN_THREAD_NAME].is_free():
                self._thread_managers[_MAIN_THREAD_NAME].submit_event(event, prioritize=prioritize)
                need_new_thread = False
            else:
                for tname in self._thread_managers.keys():
                    if tname.startswith(_ANONYMOUS_THREAD_NAME) and self._thread_managers[tname].is_free():
                        self._thread_managers[tname].submit_event(event, prioritize=prioritize)
                        need_new_thread = False
                        break
            if need_new_thread:
                num_anon_threads = len([tname for tn in self._thread_managers.keys() if
                                        tn.startswith(_ANONYMOUS_THREAD_NAME)])
                anonymous_thread_name = _ANONYMOUS_THREAD_NAME + str(num_anon_threads)
                self._start_new_thread(anonymous_thread_name)
                self._thread_managers[anonymous_thread_name].submit_event(event)
        else:
            if thread_name is not None:
                if thread_name not in self._thread_managers:
                    self._start_new_thread(thread_name)
                self._thread_managers[thread_name].submit_event(event, prioritize=prioritize)
            else:
                self._thread_managers[_MAIN_THREAD_NAME].submit_event(event, prioritize=prioritize)

        return future

    def shutdown(self):
        """
        Stop all threads managed by this executor and wait for them to finish
        """
        # For now just let the devices be garbage collected.
        # TODO: add explicit shutdowns for devices here?
        self._devices = None
        self._shutdown_event.set()
        for thread in self._thread_managers.values():
            thread.shutdown()
        for thread in self._thread_managers.values():
            thread.join()

        # Make sure the notification thread is stopped
        if self._notification_thread is not None:
            # It was never started if no one subscribed
            self._notification_thread.join()
        # delete singleton instance
        ExecutionEngine._instance = None


class _ExecutionThreadManager:
    """
    Class which manages a single thread that executes events from a queue, one at a time. Events can be added
    to either end of the queue, in order to prioritize them. The thread will stop when the shutdown method is called,
    or in the event of an unhandled exception during event execution.

    This class handles thread safety so that it is possible to check if the thread has any currently executing events
    or events in its queue with the is_free method.

    """
    _deque: Deque[ExecutorEvent]
    thread: threading.Thread

    def __init__(self, name='UnnamedExectorThread'):
        super().__init__()
        self.thread = threading.Thread(target=self._run_thread, name=name)
        self.thread.execution_engine_thread = True
        self._deque = deque()
        self._shutdown_event = threading.Event()
        self._terminate_event = threading.Event()
        self._exception = None
        self._event_executing = False
        self._addition_condition = threading.Condition()
        self.thread.start()

    def join(self):
        self.thread.join()

    def _run_thread(self):
        event = None
        while True:
            if self._terminate_event.is_set():
                return
            if self._shutdown_event.is_set() and not self._deque:
                return
            # Event retrieval loop
            while event is None:
                with (self._addition_condition):
                    if not self._deque:
                        # wait until something is in the queue
                        self._addition_condition.wait()
                    if self._terminate_event.is_set():
                        return
                    if self._shutdown_event.is_set() and not self._deque:
                        # awoken by a shutdown event and the queue is empty
                        return
                    event: ExecutorEvent = self._deque.popleft()
                    if not hasattr(event, '_num_retries_on_exception'):
                        warnings.warn("Event does not have num_retries_on_exception attribute, setting to 0")
                        event._num_retries_on_exception = 0
                    num_retries = event._num_retries_on_exception
                    self._event_executing = True

            # Event execution loop
            exception = None
            return_val = None
            for attempt_number in range(event._num_retries_on_exception + 1):
                if self._terminate_event.is_set():
                    return  # Executor has been terminated
                try:
                    if ExecutionEngine._debug:
                        print("Executing event", event.__class__.__name__, threading.current_thread())
                    if event._finished:
                        raise RuntimeError("Event ", event, " was already executed")
                    return_val = event.execute()
                    if ExecutionEngine._debug:
                        print("Finished executing", event.__class__.__name__, threading.current_thread())
                    break
                except Exception as e:
                    warnings.warn(f"{e} during execution of {event}" + (", retrying {num_retries} more times"
                                  if num_retries > 0 else ""))
                    # traceback.print_exc()
                    exception = e
            if exception is not None:
                ExecutionEngine.get_instance()._log_exception(exception)
            event._post_execution(return_value=return_val, exception=exception)
            with self._addition_condition:
                self._event_executing = False
            event = None

    def is_free(self):
        """
        return true if an event is not currently being executed and the queue is empty
        """
        with self._addition_condition:
            return not self._event_executing and not self._deque and not \
                    self._terminate_event.is_set() and not self._shutdown_event.is_set()

    def submit_event(self, event, prioritize=False):
        """
        Submit an event for execution on this thread. If prioritize is True, the event will be executed before any other
        events in the queue.
        """
        with self._addition_condition:
            if self._shutdown_event.is_set() or self._terminate_event.is_set():
                raise RuntimeError("Cannot submit event to a thread that has been shutdown")
            if prioritize:
                self._deque.appendleft(event)
            else:
                self._deque.append(event)
            self._addition_condition.notify_all()

    def terminate(self):
        """
        Stop the thread immediately, without waiting for the current event to finish
        """
        with self._addition_condition:
            self._terminate_event.set()
            self._shutdown_event.set()
            self._addition_condition.notify_all()
        self.thread.join()
    def shutdown(self):
        """
        Stop the thread and wait for it to finish
        """
        with self._addition_condition:
            self._shutdown_event.set()
            self._addition_condition.notify_all()
        self.thread.join()

