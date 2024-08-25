import pytest
import threading
import functools
from exengine.kernel.device import Device
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.executor import ExecutionEngine
from exengine import on_thread
from exengine.kernel.executor import _MAIN_THREAD_NAME



class ThreadRecordingEvent(ExecutorEvent):
    def execute(self):
        return threading.current_thread().name


@on_thread("CustomEventThread")
class DecoratedEvent(ThreadRecordingEvent):
    pass


class TestDevice(Device):

    def __init__(self, name):
        super().__init__(name, no_executor_attrs=('_attribute', 'set_attribute_thread',
                                                  'get_attribute_thread', 'regular_method_thread',
                                                  'decorated_method_thread'))
        self._attribute = 123

    @property
    def attribute(self):
        self.get_attribute_thread = threading.current_thread().name
        return self._attribute

    @attribute.setter
    def attribute(self, value):
        self.set_attribute_thread = threading.current_thread().name
        self._attribute = value

    def regular_method(self):
        self.regular_method_thread = threading.current_thread().name

    @on_thread("CustomMethodThread")
    def decorated_method(self):
        self.decorated_method_thread = threading.current_thread().name


@on_thread("CustomDeviceThread")
class CustomThreadTestDevice(Device):

    def __init__(self, name):
        super().__init__(name, no_executor_attrs=('_attribute',
                                                  'set_attribute_thread', 'get_attribute_thread',
                                                  'regular_method_thread', 'decorated_method_thread'))
        self._attribute = 123

    @property
    def attribute(self):
        self.get_attribute_thread = threading.current_thread().name
        return self._attribute

    @attribute.setter
    def attribute(self, value):
        self.set_attribute_thread = threading.current_thread().name
        self._attribute = value

    def regular_method(self):
        self.regular_method_thread = threading.current_thread().name

@pytest.fixture()
def engine():
    engine = ExecutionEngine()
    yield engine
    engine.shutdown()

############################################################
# Event tests
############################################################

def test_undecorated_event(engine):
    """
    Test that an undecorated event executes on the main executor thread.
    """
    event = ThreadRecordingEvent()
    future = engine.submit(event)
    result = future.await_execution()
    assert result == _MAIN_THREAD_NAME

def test_decorated_event(engine):
    """
    Test that a decorated event executes on the specified custom thread.
    """
    event = DecoratedEvent()
    future = engine.submit(event)
    result = future.await_execution()
    assert result == "CustomEventThread"


############################################################
# Device tests
############################################################
def test_device_attribute_access(engine):
    """
    Test that device attribute access runs on the main thread when nothing else specified.
    """
    device = TestDevice("TestDevice")
    device.attribute = 'something'
    assert device.set_attribute_thread == _MAIN_THREAD_NAME

def test_device_regular_method_access(engine):
    """
    Test that device method access runs on the main thread when nothing else specified.
    """
    device = TestDevice("TestDevice")
    device.regular_method()
    assert device.regular_method_thread == _MAIN_THREAD_NAME

def test_device_decorated_method_access(engine):
    """
    Test that device method access runs on the main thread when nothing else specified.
    """
    device = TestDevice("TestDevice")
    device.decorated_method()
    assert device.decorated_method_thread == "CustomMethodThread"

def test_custom_thread_device_attribute_access(engine):
    """
    Test that device attribute access runs on the custom thread when specified.
    """
    custom_device = CustomThreadTestDevice("CustomDevice")
    custom_device.attribute = 'something'
    assert custom_device.set_attribute_thread == "CustomDeviceThread"

def test_custom_thread_device_property_access(engine):
    """
    Test that device property access runs on the custom thread when specified.
    """
    custom_device = CustomThreadTestDevice("CustomDevice")
    custom_device.attribute = 'something'
    assert custom_device.set_attribute_thread == "CustomDeviceThread"

    f = custom_device.attribute
    assert custom_device.get_attribute_thread == "CustomDeviceThread"


@on_thread("OuterThread")
class OuterThreadDevice(Device):
    def __init__(self, name, inner_device):
        super().__init__(name)
        self.inner_device = inner_device
        self.outer_thread = None

    def outer_method(self):
        self.outer_thread = threading.current_thread().name
        self.inner_device.inner_method()


@on_thread("InnerThread")
class InnerThreadDevice(Device):
    def __init__(self, name):
        super().__init__(name)
        self.inner_thread = None

    def inner_method(self):
        self.inner_thread = threading.current_thread().name


def test_nested_thread_switch(engine):
    """
    Test that nested calls to methods with different thread specifications
    result in correct thread switches at each level.
    """
    inner_device = InnerThreadDevice("InnerDevice")
    outer_device = OuterThreadDevice("OuterDevice", inner_device)

    class OuterEvent(ExecutorEvent):
        def execute(self):
            outer_device.outer_method()

    event = OuterEvent()

    engine.submit(event).await_execution()

    assert outer_device.outer_thread == "OuterThread"
    assert inner_device.inner_thread == "InnerThread"


def another_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class MultiDecoratedDevice(Device):
    @on_thread("Thread1")
    @another_decorator
    def method1(self):
        return threading.current_thread().name

    @another_decorator
    @on_thread("Thread2")
    def method2(self):
        return threading.current_thread().name


def test_multiple_decorators(engine):
    """
    Test that the thread decorator works correctly when combined with other decorators.
    """
    device = MultiDecoratedDevice("MultiDevice")

    class MultiEvent(ExecutorEvent):
        def execute(self):
            return device.method1(), device.method2()

    assert engine.submit(MultiEvent()).await_execution() == ("Thread1", "Thread2")