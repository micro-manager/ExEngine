import inspect

import pytest

from exengine import ExecutionEngine
from exengine.kernel.device import Device
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
def obj():
    return TestObject()

def test_bare(obj):
    """Test the non-wrapped object"""
    obj.value1 = 28
    obj.value2 = 29
    assert obj.value1 == 28
    assert obj.value2 == 29
    with pytest.raises(AttributeError):
        obj.readonly_property = 0 # noqa property cannot be set
    assert obj.readonly_property == -1
    assert obj.public_method(4) == 28 + 29 + 4

def test_wrapping(obj):
    engine = ExecutionEngine()
    wrapper = register(engine, "object1", obj)
    test_bare(wrapper)
    # todo: why doesn't this work?
    # engine["object1"].value1 = 28
    # todo: why use the singleton antipattern?
    ExecutionEngine.get_device("object1").value1 = 7
    assert wrapper.value1 == 7
    engine.shutdown()


class DeviceBase:
    def __init__(self, wrapped_device):
        self._device = wrapped_device

def register(engine: ExecutionEngine, id: str, obj: object):
    """
    Wraps an object for use with the ExecutionEngine

    todo: make method of ExecutionEngine?

    The wrapper exposes the public properties and attributes of the wrapped object, converting
    all get and set access, as well as method calls to Events.
    Private methods and attributes are not exposed.

    After wrapping, the original object should not be used directly anymore.
    All access should be done through the wrapper, which takes care of thread safety, synchronization, etc.

    Args:
        engine: ExecutionEngine instance
        id: Unique id (name) of the device, used by the ExecutionEngine.
        obj: object to wrap. The object should only be registered once. Use of the original object should be avoided after wrapping,
            since access to the original object is not thread safe or otherwise managed by the ExecutionEngine.
    """
    #
    if any(d is obj for d in engine._devices):
        raise ValueError("Object already registered")

    # get a list of all properties and methods, including the ones in base classes
    # Also process class annotations, for attributes that are not properties
    class_hierarchy = inspect.getmro(obj.__class__)
    all_dict = {}
    for c in class_hierarchy[::-1]:
        all_dict.update(c.__dict__)
        annotations = c.__dict__.get('__annotations__', {})
        all_dict.update(annotations)

    # create the wrapper class
    class_dict = {
        '_device': obj,
    }
    for n, a in all_dict.items():
        if n.startswith('_'):
            continue  # skip private attributes
        name = n # capture name
        attribute = a
        print(name)
        if inspect.isfunction(attribute):
            def method(self, *args, _method=attribute, **kwargs):
                print(f"Calling {_method}")
                return _method(self._device, *args, **kwargs)
            class_dict[name] = method
        else:
            def getter(self, _name=name):
                return getattr(self._device, _name)
            def setter(self, value, _name=name):
                setattr(self._device, _name, value)
            class_dict[name] = property(getter, setter, None, f"Wrapped attribute {name}")

        # event = MethodCallEvent(method_name=attr_name, args=args, kwargs=kwargs, instance=self)
        # return ExecutionEngine.get_instance().submit(event, thread_name=thread_name).await_execution()
        # event = GetAttrEvent(attr_name=name, instance=self, method=getattribute_with_fallback)
        # return ExecutionEngine.get_instance().submit(event, thread_name=thread_name).await_execution()
        # event = SetAttrEvent(attr_name=name, value=value, instance=self, method=original_setattr)
        # ExecutionEngine.get_instance().submit(event, thread_name=thread_name).await_execution()
    WrappedObject = type('_' + obj.__class__.__name__, (DeviceBase,), class_dict)
    # todo: cache dynamically generated classes
    wrapped = WrappedObject(obj)
    ExecutionEngine.register_device(id, wrapped)
    return wrapped
