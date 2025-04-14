"""
Unit tests for the ExecutionEngine and Device classes.
Ensures rerouting of method calls to the ExecutionEngine and proper handling of internal threads.
"""

import pytest
from exengine.kernel.ex_event_base import ExecutorEvent

from exengine.kernel.device import Device
from exengine.kernel.executor import ExecutionEngine
import time


@pytest.fixture()
def engine():
    e = ExecutionEngine()
    yield e
    e.shutdown()


#############################################################################################
# Tests for automated rerouting of method calls to the ExecutionEngine to executor threads
#############################################################################################
counter = 1
class TestDevice:
    """
    These classes are automatically wrapped for use in an ExecutionEngine.
    """
    def __init__(self):
        self.test_attribute = None
        self._test_property = None

    def test_method(self):
        return True

    @property
    def test_property(self):
        return self._test_property

    @test_property.setter
    def test_property(self, value):
        self._test_property = value



def test_device_method_execution(engine):
    engine.register("mock_device0", TestDevice())
    result = engine["mock_device0"].test_method().await_execution()
    assert result is True

def test_device_attribute_setting(engine):
    engine.register("mock_device0", TestDevice())
    engine["mock_device0"].test_attribute = "test_value"
    result = engine["mock_device0"].test_attribute
    assert result == "test_value"

def test_multiple_method_calls(engine):
    mock_device = engine.register("mock_device0", TestDevice())
    result1 = mock_device.test_method().await_execution()
    mock_device.test_attribute = "test_value"
    result2 = mock_device.test_attribute

    assert result1 is True
    assert result2 == "test_value"

def test_device_property_setting(engine):
    mock_device = engine.register("mock_device0", TestDevice())
    engine["mock_device0"].test_property = "test_value"
    result = mock_device.test_property
    assert result == "test_value"

#######################################################
# Tests for internal threads in Devices
#######################################################

from concurrent.futures import ThreadPoolExecutor
from exengine.kernel.executor import ExecutionEngine
import threading


class ThreadCreatingDevice:
    def __init__(self):
        self.test_attribute = None
        self._internal_thread_result = None
        self._nested_thread_result = None

    def create_internal_thread(self):
        def internal_thread_func():
            self.test_attribute = "set_by_internal_thread"

        thread = threading.Thread(target=internal_thread_func)
        thread.start()
        thread.join()

    def create_nested_thread(self):
        def nested_thread_func():
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
            self.test_attribute = "set_by_threadpool"

        with ThreadPoolExecutor() as executor:
            executor.submit(threadpool_func)

def test_device_internal_thread(engine):
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
    engine.register("thread_creator", ThreadCreatingDevice())
    print('getting ready to create internal thread')
    t = engine["thread_creator"].create_internal_thread().await_execution()
    # t.join()

    # while device.test_attribute is None:
    #     time.sleep(0.1)
    assert engine["thread_creator"].test_attribute == "set_by_internal_thread"

def test_device_nested_thread(engine):
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
    device = engine.register("thread_creator", ThreadCreatingDevice())
    device.create_nested_thread()
    while device.test_attribute is None:
        time.sleep(0.1)
    assert device.test_attribute == "set_by_nested_thread"

def test_device_threadpool_executor(engine):
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
    device = engine.register("thread_creator", ThreadCreatingDevice())
    device.use_threadpool_executor()
    while device.test_attribute is None:
        time.sleep(0.1)
    assert device.test_attribute == "set_by_threadpool"


#######################################################
# Tests for other ExecutionEngine functionalities
#######################################################

class SyncEvent(ExecutorEvent):

    def __init__(self, start_event, finish_event):
        super().__init__()
        self.executed = False
        self.executed_time = None
        self.execute_count = 0
        self.executed_thread_name = None
        self.start_event = start_event
        self.finish_event = finish_event

    def execute(self):
        self.executed_thread_name = threading.current_thread().name
        self.start_event.set()  # Signal that the execution has started
        self.finish_event.wait()  # Wait for the signal to finish
        self.executed_time = time.time()
        self.execute_count += 1
        self.executed = True

def create_sync_event(start_event, finish_event):
    return SyncEvent(start_event, finish_event)


def test_submit_single_event(engine):
    """
    Test submitting a single event to the ExecutionEngine.
    Verifies that the event is executed and returns an AcquisitionFuture.
    """
    start_event = threading.Event()
    finish_event = threading.Event()
    event = create_sync_event(start_event, finish_event)

    future = engine.submit(event)
    engine.check_exceptions()
    start_event.wait()  # Wait for the event to start executing
    finish_event.set()  # Signal the event to finish

    while not event.executed:
        time.sleep(0.1)

    assert event.executed


def test_submit_multiple_events(engine):
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

    future1 = engine.submit(event1)
    future2 = engine.submit(event2)

    start_event1.wait()  # Wait for the first event to start executing
    finish_event1.set()  # Signal the first event to finish
    start_event2.wait()  # Wait for the second event to start executing
    finish_event2.set()  # Signal the second event to finish

    while not event1.executed or not event2.executed:
        time.sleep(0.1)

    assert event1.executed
    assert event2.executed


@pytest.mark.skip("This test is broken. Even though event3 gets priority, it may execute after event2.")
def test_event_prioritization(engine):
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

    engine.submit(event1)
    start_event1.wait()  # Wait for the first event to start executing

    engine.submit(event2)
    # race condition, at this point the engine may or may not have started executing event2
    engine.submit(event3, prioritize=True)

    finish_event1.set()
    finish_event2.set()
    finish_event3.set()

    while not event1.executed or not event2.executed or not event3.executed:
        time.sleep(0.1)

    assert event3.executed_time <= event2.executed_time
    assert event1.executed
    assert event2.executed
    assert event3.executed


def test_use_free_thread_parallel_execution(engine):
    """
    Test parallel execution in the ExecutionEngine.
    Verifies that events submitted to the engine directlycan execute in parallel.
    """
    start_event1 = threading.Event()
    finish_event1 = threading.Event()
    event1 = create_sync_event(start_event1, finish_event1)

    start_event2 = threading.Event()
    finish_event2 = threading.Event()
    event2 = create_sync_event(start_event2, finish_event2)

    engine.submit(event1)
    engine.submit(event2)

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


def test_single_execution_with_free_thread(engine):
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

    engine.submit(event1)
    engine.submit(event2)

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

#### Callable submission tests ####
def test_submit_callable(engine):
    def simple_function():
        return 42

    future = engine.submit(simple_function)
    result = future.await_execution()
    assert result == 42

def test_submit_lambda(engine):
    future = engine.submit(lambda: "Hello, World!")
    result = future.await_execution()
    assert result == "Hello, World!"

def test_class_method(engine):
    class TestClass:
        def test_method(self):
            return "Test method executed"

    future = engine.submit(TestClass().test_method)
    result = future.await_execution()
    assert result == "Test method executed"

# (removed, because submitting lists of events is not supported yet, and may not be necessary)
# def test_submit_mixed(engine):
#     class TestEvent(ExecutorEvent):
#         def execute(self):
#             return "Event executed"
#
#     futures = engine.submit([TestEvent(), lambda: 42, lambda: "Lambda"])
#     results = [future.await_execution() for future in futures]
#     assert results == ["Event executed", 42, "Lambda"]

def test_submit_invalid(engine):
    with pytest.raises(TypeError):
        engine.submit(lambda x: x + 1)  # Callable with arguments should raise TypeError

    with pytest.raises(TypeError):
        engine.submit("Not a callable")  # Non-callable, non-ExecutorEvent should raise TypeError

#######################################################
# Tests for named thread functionalities ##############
#######################################################

from exengine.kernel.executor import _MAIN_THREAD_NAME
from exengine.kernel.executor import _ANONYMOUS_THREAD_NAME


def test_submit_to_main_thread(engine):
    """
    Test submitting an event to the main thread.
    """
    start_event = threading.Event()
    finish_event = threading.Event()
    event = create_sync_event(start_event, finish_event)

    future = engine.submit(event)
    start_event.wait()
    finish_event.set()

    assert event.executed_thread_name == _MAIN_THREAD_NAME

def test_device_thread(engine):
    """Test that events submitted to a device are not reordered"""

    class TestDeviceOrdered:
        def __init__(self):
            self.value = 0

        def work(self, old_value, new_value):
            if self.value != old_value:
                raise ValueError("Value was not as expected")
            time.sleep(0.5)
            if self.value != old_value:
                raise ValueError("Value was not as expected")
            self.value = new_value

    device = engine.register("device", TestDeviceOrdered())
    device.work(0, 1)
    device.work(1, 2)
    device.work(2, 3)


def test_worker_thread(engine):
    """Test that events submitted to a worker thread execute in parallel"""
    count = 0
    def worker_thread():
        nonlocal count
        if count != 0:
            raise ValueError("Count was not as expected")
        time.sleep(0.5)
        count += 1

    f1 = engine.submit(worker_thread)
    f2 =engine.submit(worker_thread)
    f3 = engine.submit(worker_thread)
    f1.await_execution()
    f2.await_execution()
    f3.await_execution()
    assert count == 3