"""
Base class for all device_implementations that integrates with the execution engine and enables tokenization of device access.
"""
from abc import ABCMeta
from functools import wraps
from typing import Any, Dict, Callable
from weakref import WeakSet
from dataclasses import dataclass

from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.executor import ExecutionEngine
import threading
import sys

_python_debugger_active = any('pydevd' in sys.modules for frame in sys._current_frames().values())



# All threads that were created by code running on an executor thread, or created by threads that were created by
# code running on an executor thread etc. Don't want to auto-reroute these to the executor because this might have
# unintended consequences. So they need to be tracked and not rerouted
_within_executor_threads = WeakSet()
# Keep this list accessible outside of class attributes to avoid infinite recursion
_no_executor_attrs = ['_name', '_no_executor', '_no_executor_attrs']

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

@dataclass
class MethodCallEvent(ExecutorEvent):
    method_name: str
    args: tuple
    kwargs: Dict[str, Any]
    instance: Any

    def execute(self):
        method = getattr(self.instance, self.method_name)
        return method(*self.args, **self.kwargs)

@dataclass
class GetAttrEvent(ExecutorEvent):
    attr_name: str
    instance: Any
    method: Callable

    def execute(self):
        return self.method(self.instance, self.attr_name)

@dataclass
class SetAttrEvent(ExecutorEvent):
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
            if attr_name in _no_executor_attrs or self._no_executor:
                return attr_value(self, *args, **kwargs)
            if DeviceMetaclass._is_reroute_exempted_thread():
                return attr_value(self, *args, **kwargs)
            event = MethodCallEvent(method_name=attr_name, args=args, kwargs=kwargs, instance=self)
            return ExecutionEngine.get_instance().submit(event).await_execution()

        wrapper._wrapped_for_executor = True
        return wrapper

    @staticmethod
    def is_debugger_thread():
        if not _python_debugger_active:
            return False
        # This is a heuristic and may need adjustment based on the debugger used.
        debugger_thread_names = ["pydevd", "Debugger", "GetValueAsyncThreadDebug"]  # Common names for debugger threads
        current_thread = threading.current_thread()
        # Check if current thread name contains any known debugger thread names
        return any(name in current_thread.name or name in str(current_thread.__class__.__name__)
                   for name in debugger_thread_names)

    @staticmethod
    def _is_reroute_exempted_thread() -> bool:
        return (DeviceMetaclass.is_debugger_thread() or ExecutionEngine.on_any_executor_thread() or
                threading.current_thread() in _within_executor_threads)

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
            if name in _no_executor_attrs or self._no_executor:
                return object.__getattribute__(self, name)
            if DeviceMetaclass._is_reroute_exempted_thread():
                return getattribute_with_fallback(self, name)
            else:
                event = GetAttrEvent(attr_name=name, instance=self, method=getattribute_with_fallback)
                return ExecutionEngine.get_instance().submit(event).await_execution()

        def __setattr__(self: 'Device', name: str, value: Any) -> None:
            if name in _no_executor_attrs or self._no_executor:
                original_setattr(self, name, value)
            elif DeviceMetaclass._is_reroute_exempted_thread():
                original_setattr(self, name, value)
            else:
                event = SetAttrEvent(attr_name=name, value=value, instance=self, method=original_setattr)
                ExecutionEngine.get_instance().submit(event).await_execution()

        new_attrs['__getattribute__'] = __getattribute__
        new_attrs['__setattr__'] = __setattr__

        new_attrs['_no_executor'] = True # For startup
        new_attrs['_no_executor_attrs'] = _no_executor_attrs



        # Create the class
        cls = super().__new__(mcs, name, bases, new_attrs)

        # Add automatic registration to the executor
        original_init = cls.__init__

        @wraps(original_init)
        def init_and_register(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Register the instance with the executor
            if hasattr(self, '_name') and hasattr(self, '_no_executor') and not self._no_executor:
                ExecutionEngine.register_device(self._name, self)

        # Use setattr instead of direct assignment
        setattr(cls, '__init__', init_and_register)


        return cls

