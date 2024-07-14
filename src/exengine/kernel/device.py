"""
Base class for all device_implementations that integrates with the execution engine and enables tokenization of device access.
"""
from abc import ABC, ABCMeta
from functools import wraps
from typing import Any, Dict, Callable, List, Union, Iterable
from weakref import WeakSet

from pycromanager.execution_engine.kernel.acq_event_base import AcquisitionEvent
from pycromanager.execution_engine.kernel.executor import ExecutionEngine
import threading
from abc import abstractmethod
import sys

_python_debugger_active = any('pydevd' in sys.modules for frame in sys._current_frames().values())



# All threads that were created by code running on an executor thread, or created by threads that were created by
# code running on an executor thread etc. Don't want to auto-reroute these to the executor because this might have
# unintended consequences. So they need to be tracked and not rerouted
_within_executor_threads = WeakSet()

def thread_start_hook(thread):
    # keep track of threads that were created by code running on an executor thread so calls on them
    # dont get rerouted to the executor
    if ExecutionEngine.on_any_executor_thread() or threading.current_thread() in _within_executor_threads:
        _within_executor_threads.add(thread)

# Monkey patch the threading module so we can monitor the creation of new threads
_original_thread_start = threading.Thread.start

# Define a new start method that adds the hook
def _thread_start(self, *args, **kwargs):
    try:
        thread_start_hook(self)
        _original_thread_start(self, *args, **kwargs)
    except Exception as e:
        print(f"Error in thread start hook: {e}")
        # traceback.print_exc()

# Replace the original start method with the new one
threading.Thread.start = _thread_start


class MethodCallEvent(AcquisitionEvent):
    method_name: str
    args: tuple
    kwargs: Dict[str, Any]
    instance: Any

    def execute(self):
        method = getattr(self.instance, self.method_name)
        return method(*self.args, **self.kwargs)

class GetAttrEvent(AcquisitionEvent):
    attr_name: str
    instance: Any
    method: Callable

    def execute(self):
        return self.method(self.instance, self.attr_name)

class SetAttrEvent(AcquisitionEvent):
    attr_name: str
    value: Any
    instance: Any
    method: Callable

    def execute(self):
        self.method(self.instance, self.attr_name, self.value)


class DeviceMetaclass(ABCMeta):
    """
    Metaclass for device_implementations that wraps all methods and attributes in the device class to add the ability to
    control their execution and access. This has two purposes:

    1) Add the ability to record all method calls and attribute accesses for tokenization
    2) Add the ability to make all methods and attributes thread-safe by putting them on the Executor
    3) Automatically register all instances of the device with the ExecutionEngine
    """
    @staticmethod
    def wrap_for_executor(attr_name, attr_value):
        if hasattr(attr_value, '_wrapped_for_executor'):
            return attr_value

        @wraps(attr_value)
        def wrapper(self: 'Device', *args: Any, **kwargs: Any) -> Any:
            if ExecutionEngine.on_any_executor_thread():
                return attr_value(self, *args, **kwargs)
            event = MethodCallEvent(method_name=attr_name, args=args, kwargs=kwargs, instance=self)
            return ExecutionEngine.get_instance().submit(event).await_execution()

        wrapper._wrapped_for_executor = True
        return wrapper

    @staticmethod
    def find_in_bases(bases, method_name):
        for base in bases:
            if hasattr(base, method_name):
                return getattr(base, method_name)
        return None

    def __new__(mcs, name: str, bases: tuple, attrs: dict) -> Any:
        new_attrs = {}
        for attr_name, attr_value in attrs.items():
            if not attr_name.startswith('_'):
                if callable(attr_value):
                    new_attrs[attr_name] = mcs.wrap_for_executor(attr_name, attr_value)
                else:
                    pass
            else:
                new_attrs[attr_name] = attr_value

        def is_debugger_thread():
            if not _python_debugger_active:
                return False
            # This is a heuristic and may need adjustment based on the debugger used.
            debugger_thread_names = ["pydevd", "Debugger", "GetValueAsyncThreadDebug"]  # Common names for debugger threads
            current_thread = threading.current_thread()
            # Check if current thread name contains any known debugger thread names
            return any(name in current_thread.name or name in str(current_thread.__class__.__name__)
                       for name in debugger_thread_names)

        original_setattr = attrs.get('__setattr__') or mcs.find_in_bases(bases, '__setattr__') or object.__setattr__
        def getattribute_with_fallback(self, name):
            """ Wrap the getattribute method to fallback to getattr if an attribute is not found """
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                try:
                    return self.__getattr__(name)
                except AttributeError as e:
                    if _python_debugger_active and (name == 'shape' or name == '__len__'):
                        pass  # This prevents a bunch of irrelevant errors in the Pycharm debugger
                    else:
                        raise e

        def __getattribute__(self: 'Device', name: str) -> Any:
            if name.endswith('_noexec'):
                # special attributes unrelated to hardware that should not be rerouted to the executor
                return getattribute_with_fallback(self, name)
            if is_debugger_thread():
                return getattribute_with_fallback(self, name)
            if ExecutionEngine.on_any_executor_thread():
                # already on the executor thread, so proceed as normal
                return getattribute_with_fallback(self, name)
            elif threading.current_thread() in _within_executor_threads:
                return getattribute_with_fallback(self, name)
            else:
                event = GetAttrEvent(attr_name=name, instance=self, method=getattribute_with_fallback)
                return ExecutionEngine.get_instance().submit(event).await_execution()

        def __setattr__(self: 'Device', name: str, value: Any) -> None:
            # These methods don't need to be on the executor because they have nothing to do with hardware
            if name.endswith('_noexec'):
                original_setattr(self, name, value)
            if is_debugger_thread():
                original_setattr(self, name, value)
            elif ExecutionEngine.on_any_executor_thread():
                original_setattr(self, name, value)  # we're already on the executor thread, so just set it
            elif threading.current_thread() in _within_executor_threads:
                original_setattr(self, name, value)
            else:
                event = SetAttrEvent(attr_name=name, value=value, instance=self, method=original_setattr)
                ExecutionEngine.get_instance().submit(event).await_execution()

        new_attrs['__getattribute__'] = __getattribute__
        new_attrs['__setattr__'] = __setattr__


        # Create the class
        cls = super().__new__(mcs, name, bases, new_attrs)

        # Add automatic registration to the executor
        original_init = cls.__init__

        @wraps(original_init)
        def init_and_register(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Register the instance with the executor
            if hasattr(self, '_device_name_noexec'):
                ExecutionEngine.register_device(self._device_name_noexec, self)

        # Use setattr instead of direct assignment
        setattr(cls, '__init__', init_and_register)


        return cls

class Device(ABC, metaclass=DeviceMetaclass):
    """
    Required base class for all devices usable with the execution engine

    Device classes should inherit from this class and implement the abstract methods. The DeviceMetaclass will wrap all
    methods and attributes in the class to make them thread-safe and to optionally record all method calls and
    attribute accesses.

    Attributes with a trailing _noexec will not be wrapped and will be executed directly on the calling thread. This is
    useful for attributes that are not hardware related and can bypass the complexity of the executor.

    Device implementations can also implement functionality through properties (i.e. attributes that are actually
    methods) by defining a getter and setter method for the property.
    """

    def __init__(self, device_name: str):
        self._device_name_noexec = device_name


    @abstractmethod
    def get_allowed_property_values(self, property_name: str) -> List[str]:
        ...

    @abstractmethod
    def is_property_read_only(self, property_name: str) -> bool:
        ...

    @abstractmethod
    def get_property_limits(self, property_name: str) -> (float, float):
        ...

    @abstractmethod
    def is_property_hardware_triggerable(self, property_name: str) -> bool:
        ...

    @abstractmethod
    def get_triggerable_sequence_max_length(self, property_name: str) -> int:
        ...

    @abstractmethod
    def load_triggerable_sequence(self, property_name: str, event_sequence: Iterable[Union[str, float, int]]):
        ...

    @abstractmethod
    def start_triggerable_sequence(self, property_name: str):
        ...

    @abstractmethod
    def stop_triggerable_sequence(self, property_name: str):
        ...
