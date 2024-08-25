"""
Unit tests for the ExecutionEngine and Device classes.
Ensures rerouting of method calls to the ExecutionEngine and proper handling of internal threads.
"""

import pytest
from unittest.mock import MagicMock
from exengine.kernel.ex_event_base import ExecutorEvent

from exengine.kernel.device import Device
import time


@pytest.fixture()
def execution_engine():
    engine = ExecutionEngine()
    yield engine
    engine.shutdown()


#############################################################################################
# Tests for automated rerouting of method calls to the ExecutionEngine to executor threads
#############################################################################################
counter = 1
class MockDevice(Device):
    def __init__(self):
        global counter
        super().__init__(name=f'mock_device_{counter}')
        counter += 1
        self._test_attribute = None

    def test_method(self):
        assert ExecutionEngine.on_any_executor_thread()
        assert threading.current_thread().execution_engine_thread
        return True

    def set_test_attribute(self, value):
        assert ExecutionEngine.on_any_executor_thread()
        assert threading.current_thread().execution_engine_thread
        self._test_attribute = value

    def get_test_attribute(self):
        assert ExecutionEngine.on_any_executor_thread()
        assert threading.current_thread().execution_engine_thread
        return self._test_attribute

def test_device_method_execution(execution_engine):
    mock_device = MockDevice()

    result = mock_device.test_method()
    assert result is True

def test_device_attribute_setting(execution_engine):
    mock_device = MockDevice()

    mock_device.set_test_attribute("test_value")
    result = mock_device.get_test_attribute()
    assert result == "test_value"

def test_device_attribute_direct_setting(execution_engine):
    mock_device = MockDevice()

    mock_device.direct_set_attribute = "direct_test_value"
    assert mock_device.direct_set_attribute == "direct_test_value"

def test_multiple_method_calls(execution_engine):
    mock_device = MockDevice()

    result1 = mock_device.test_method()
    mock_device.set_test_attribute("test_value")
    result2 = mock_device.get_test_attribute()

    assert result1 is True
    assert result2 == "test_value"


#######################################################
# Tests for internal threads in Devices
#######################################################

from concurrent.futures import ThreadPoolExecutor
from exengine.kernel.executor import ExecutionEngine
from exengine.device_types import Device
import threading


class ThreadCreatingDevice(Device):
    def __init__(self):
        global counter
        super().__init__(name=f'test{counter}')
        counter += 1
        self.test_attribute = None
        self._internal_thread_result = None
        self._nested_thread_result = None

    def create_internal_thread(self):
        def internal_thread_func():
            # This should not be on an executor thread
            assert not ExecutionEngine.on_any_executor_thread()
            assert not getattr(threading.current_thread(), 'execution_engine_thread', False)
            self.test_attribute = "set_by_internal_thread"

        thread = threading.Thread(target=internal_thread_func)
        thread.start()
        thread.join()

    def create_nested_thread(self):
        def nested_thread_func():
            # This should not be on an executor thread
            assert not ExecutionEngine.on_any_executor_thread()
            assert not getattr(threading.current_thread(), 'execution_engine_thread', False)
            self.test_attribute = "set_by_nested_thread"

        def internal_thread_func():
            thread = threading.Thread(target=nested_thread_func)
            thread.start()
            thread.join()

        thread = threading.Thread(target=internal_thread_func)
        thread.start()
        thread.join()


    def use_threadpool_executor(self):
        def threadpool_func():
            # This should not be on an executor thread
            assert not ExecutionEngine.on_any_executor_thread()
            assert not getattr(threading.current_thread(), 'execution_engine_thread', False)
            self.test_attribute = "set_by_threadpool"

        with ThreadPoolExecutor() as executor:
            executor.submit(threadpool_func)


def test_device_internal_thread(execution_engine):
    """
    Test that a thread created internally by a device is not treated as an executor thread.

    This integration_tests verifies that when a device creates its own internal thread, the code running
    on that thread is not identified as being on an executor thread. It does this by:
    1. Creating a ThreadCreatingDevice instance
    2. Calling a method that spawns an internal thread
    3. Checking that the internal thread successfully set an attribute, indicating that
       it ran without raising any assertions about being on an executor thread
    """
    print('integration_tests started')
    device = ThreadCreatingDevice()
    print('getting ready to create internal thread')
    t = device.create_internal_thread()
    # t.join()

    # while device.test_attribute is None:
    #     time.sleep(0.1)
    assert device.test_attribute == "set_by_internal_thread"


def test_device_nested_thread(execution_engine):
    """
    Test that a nested thread (a thread created by another thread within the device)
    is not treated as an executor thread.

    This integration_tests ensures that even in a nested thread scenario, the code is not identified
    as running on an executor thread. It does this by:
    1. Creating a ThreadCreatingDevice instance
    2. Calling a method that spawns an internal thread, which in turn spawns another thread
    3. Checking that the nested thread successfully set an attribute, indicating that
       it ran without raising any assertions about being on an executor thread
    """
    device = ThreadCreatingDevice()
    device.create_nested_thread()
    while device.test_attribute is None:
        time.sleep(0.1)
    assert device.test_attribute == "set_by_nested_thread"


def test_device_threadpool_executor(execution_engine):
    """
    Test that a thread created by ThreadPoolExecutor within a device method
    is not treated as an executor thread.

    This integration_tests verifies that when using Python's ThreadPoolExecutor to create a thread
    within a device method, the code running in this thread is not identified as being
    on an executor thread. It does this by:
    1. Creating a ThreadCreatingDevice instance
    2. Calling a method that uses ThreadPoolExecutor to run a function
    3. Checking that the function successfully set an attribute, indicating that
       it ran without raising any assertions about being on an executor thread
    """
    device = ThreadCreatingDevice()
    device.use_threadpool_executor()
    while device.test_attribute is None:
        time.sleep(0.1)
    assert device.test_attribute == "set_by_threadpool"


#######################################################
# Tests for other ExecutionEngine functionalities
#######################################################
def create_sync_event(start_event, finish_event):
    event = MagicMock(spec=ExecutorEvent)
    event._finished = False
    event._initialized = False
    event.num_retries_on_exception = 0
    event.executed = False
    event.executed_time = None
    event.execute_count = 0

    def execute():
        event.thread_name = threading.current_thread().name
        start_event.set()  # Signal that the execution has started
        finish_event.wait()  # Wait for the signal to finish
        event.executed_time = time.time()
        event.execute_count += 1
        event.executed = True

    event.execute.side_effect = execute
    event._post_execution = MagicMock()
    return event


def test_submit_single_event(execution_engine):
    """
    Test submitting a single event to the ExecutionEngine.
    Verifies that the event is executed and returns an AcquisitionFuture.
    """
    start_event = threading.Event()
    finish_event = threading.Event()
    event = create_sync_event(start_event, finish_event)

    future = execution_engine.submit(event)
    execution_engine.check_exceptions()
    start_event.wait()  # Wait for the event to start executing
    finish_event.set()  # Signal the event to finish

    while not event.executed:
        time.sleep(0.1)

    assert event.executed


def test_submit_multiple_events(execution_engine):
    """
    Test submitting multiple events to the ExecutionEngine.
    Verifies that all events are executed and return AcquisitionFutures.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    future1 = execution_engine.submit(event1)
    future2 = execution_engine.submit(event2)

    start_event1.wait()  # Wait for the first event to start executing
    finish_event1.set()  # Signal the first event to finish
    start_event2.wait()  # Wait for the second event to start executing
    finish_event2.set()  # Signal the second event to finish

    while not event1.executed or not event2.executed:
        time.sleep(0.1)

    assert event1.executed
    assert event2.executed


def test_event_prioritization(execution_engine):
    """
    Test event prioritization in the ExecutionEngine.
    Verifies that prioritized events are executed before non-prioritized events.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    start_event3 = threading.Event()
    finish_event3 = threading.Event()
    event3 = create_sync_event(start_event3, finish_event3)

    execution_engine.submit(event1)
    start_event1.wait()  # Wait for the first event to start executing

    execution_engine.submit(event2)
    execution_engine.submit(event3, prioritize=True)

    finish_event1.set()
    finish_event2.set()
    finish_event3.set()

    while not event1.executed or not event2.executed or not event3.executed:
        time.sleep(0.1)

    assert event3.executed_time <= event2.executed_time
    assert event1.executed
    assert event2.executed
    assert event3.executed


def test_use_free_thread_parallel_execution(execution_engine):
    """
    Test parallel execution using free threads in the ExecutionEngine.
    Verifies that events submitted with use_free_thread=True can execute in parallel.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    execution_engine.submit(event1)
    execution_engine.submit(event2, use_free_thread=True)

    # Wait for both events to start executing
    assert start_event1.wait(timeout=5)
    assert start_event2.wait(timeout=5)

    # Ensure that both events are executing simultaneously
    assert start_event1.is_set()
    assert start_event2.is_set()

    # Signal both events to finish
    finish_event1.set()
    finish_event2.set()

    while not event1.executed or not event2.executed:
        time.sleep(0.1)

    assert event1.executed
    assert event2.executed


def test_single_execution_with_free_thread(execution_engine):
    """
    Test that each event is executed only once, even when using use_free_thread=True.
    Verifies that events are not executed multiple times regardless of submission method.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    execution_engine.submit(event1)
    execution_engine.submit(event2, use_free_thread=True)

    # Wait for both events to start executing
    assert start_event1.wait(timeout=5)
    assert start_event2.wait(timeout=5)

    # Signal both events to finish
    finish_event1.set()
    finish_event2.set()

    while not event1.executed or not event2.executed:
        time.sleep(0.1)

    assert event1.executed
    assert event2.executed
    assert event1.execute_count == 1
    assert event2.execute_count == 1


#######################################################
# Tests for named thread functionalities ##############
#######################################################

from exengine.kernel.executor import _MAIN_THREAD_NAME
from exengine.kernel.executor import _ANONYMOUS_THREAD_NAME


def test_submit_to_main_thread(execution_engine):
    """
    Test submitting an event to the main thread.
    """
    start_event = threading.Event()
    finish_event = threading.Event()
    event = create_sync_event(start_event, finish_event)

    future = execution_engine.submit(event)
    start_event.wait()
    finish_event.set()

    assert event.thread_name == _MAIN_THREAD_NAME

def test_submit_to_new_anonymous_thread(execution_engine):
    """
    Test that submitting an event with use_free_thread=True creates a new anonymous thread if needed.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    # Submit first event to main thread
    execution_engine.submit(event1)
    start_event1.wait()

    # Submit second event with use_free_thread=True
    future2 = execution_engine.submit(event2, use_free_thread=True)
    start_event2.wait()

    finish_event1.set()
    finish_event2.set()

    assert event1.thread_name == _MAIN_THREAD_NAME
    assert event2.thread_name.startswith(_ANONYMOUS_THREAD_NAME)
    assert len(execution_engine._thread_managers) == 2  # Main thread + 1 anonymous thread

def test_multiple_anonymous_threads(execution_engine):
    """
    Test creation of multiple anonymous threads when submitting multiple events with use_free_thread=True.
    """
    events = []
    start_events = []
    finish_events = []
    num_events = 5

    for _ in range(num_events):
        start_event = threading.Event()
        finish_event = threading.Event()
        event = create_sync_event(start_event, finish_event)
        events.append(event)
        start_events.append(start_event)
        finish_events.append(finish_event)

    futures = [execution_engine.submit(event, use_free_thread=True) for event in events]

    for start_event in start_events:
        start_event.wait()

    for finish_event in finish_events:
        finish_event.set()

    thread_names = set(event.thread_name for event in events)
    assert len(thread_names) == num_events  # Each event should be on a different thread
    assert all(name.startswith(_ANONYMOUS_THREAD_NAME) or name == _MAIN_THREAD_NAME for name in thread_names)
    assert len(execution_engine._thread_managers) == num_events   # num_events anonymous threads

def test_reuse_named_thread(execution_engine):
    """
    Test that submitting multiple events to the same named thread reuses that thread.
    """
    thread_name = "custom_thread"
    events = []
    start_events = []
    finish_events = []
    num_events = 3

    for _ in range(num_events):
        start_event = threading.Event()
        finish_event = threading.Event()
        event = create_sync_event(start_event, finish_event)
        events.append(event)
        start_events.append(start_event)
        finish_events.append(finish_event)

    futures = [execution_engine.submit(event, thread_name=thread_name) for event in events]

    for finish_event in finish_events:
        finish_event.set()

    for start_event in start_events:
        start_event.wait()

    assert all(event.thread_name == thread_name for event in events)
    assert len(execution_engine._thread_managers) == 2  # Main thread + 1 custom named thread