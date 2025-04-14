import inspect

import numpy as np
import openwfs
from openwfs.simulation import Camera, StaticSource
from openwfs.processors import SingleRoi

import pytest

from exengine import ExecutionEngine
from exengine.kernel.device import Device
from exengine.kernel.executor import MethodCallEvent, GetAttrEvent, SetAttrEvent
from exengine.kernel.ex_future import ExecutionFuture

"""
Tests wrapping a genric object for use with the ExecutionEngine
"""

class TestObject:
    """Generic object for testing

    The object has properties with getters and setters, read-only properties, attributes
    and methods.

    The wrapper exposes the public properties and attributes of the wrapped object, converting
    all get and set access, as well as method calls to Events.
    Private methods and attributes are not exposed.
    """
    value2: int

    def __init__(self):
        self._private_attribute = 0
        self._private_property = 2
        self.value1 = 3
        self.value2 = 1

    @property
    def value1(self):
        return self._private_property

    @property
    def readonly_property(self):
        return -1

    @value1.setter
    def value1(self, value):
        self._private_property = value

    def public_method(self, x):
        return self._private_method(x)

    def _private_method(self, x):
        return x + self.value1 + self.value2

@pytest.fixture
def engine():
    e = ExecutionEngine()
    yield e
    e.shutdown()

def verify_behavior(obj):
    """Test the non-wrapped object"""
    with pytest.raises(AttributeError):
        obj.readonly_property = 0 # noqa property cannot be set
    obj.value1 = 28
    obj.value2 = 29
    assert obj.value1 == 28
    assert obj.value2 == 29
    assert obj.readonly_property == -1
    result = obj.public_method(4)
    if isinstance(result, ExecutionFuture):
        result = result.await_execution()
    assert result == 28 + 29 + 4


def test_bare():
    verify_behavior(TestObject())

def test_wrapping(engine):
    wrapper = engine.register("object1", TestObject())
    with pytest.raises(AttributeError):
        wrapper.non_existing_property = 0
    verify_behavior(wrapper)
    engine["object1"].value1 = 7
    assert wrapper.value1 == 7

def test_shutdown(engine):
    "Performs an additional shutdown."
    wrapper = engine.register("object1", TestObject())
    engine.shutdown()


def test_device_base_class(engine):
    class T(TestObject, Device):
        def __init__(self, _name, _engine):
            super().__init__()

    device = T("object1", engine)
    assert engine["object1"] is device
    verify_behavior(device)


def test_openwfs():
    img = np.zeros((1000, 1000), dtype=np.int16)
    cam = Camera(StaticSource(img), analog_max=None)
    engine = ExecutionEngine()
    wrapper = engine.register("camera1", cam)
    future = wrapper.read()
    engine.shutdown()
    frame = future.await_execution()
    assert frame.shape == img.shape
    assert np.all(frame == img)

