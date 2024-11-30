"""
Base class for all device_implementations that integrates with the execution engine and enables tokenization of device access.
"""
from functools import wraps
from weakref import WeakSet

import threading
import sys

from .executor import MethodCallEvent, GetAttrEvent, SetAttrEvent, ExecutionEngine

# class DeviceMetaclass(ABCMeta):
#     """
#     Metaclass for device_implementations that wraps all methods and attributes in the device class to add the ability to
#     control their execution and access. This has two purposes:
#
#     1) Add the ability to record all method calls and attribute accesses for tokenization
#     2) Add the ability to make all methods and attributes thread-safe by putting them on the Executor
#     3) Automatically register all instances of the device with the ExecutionEngine
#     """
#     @staticmethod
#     def wrap_for_executor(attr_name, attr_value):
#         if hasattr(attr_value, '_wrapped_for_executor'):
#             return attr_value
#
#         # Add this block to handle properties
#         if isinstance(attr_value, property):
#             return property(
#                 fget=DeviceMetaclass.wrap_for_executor(f"{attr_name}_getter", attr_value.fget) if attr_value.fget else None,
#                 fset=DeviceMetaclass.wrap_for_executor(f"{attr_name}_setter", attr_value.fset) if attr_value.fset else None,
#                 fdel=DeviceMetaclass.wrap_for_executor(f"{attr_name}_deleter", attr_value.fdel) if attr_value.fdel else None,
#                 doc=attr_value.__doc__
#             )
#
#         @wraps(attr_value)
#         def wrapper(self: 'Device', *args: Any, **kwargs: Any) -> Any:
#             if attr_name in _no_executor_attrs or self._no_executor:
#                 return attr_value(self, *args, **kwargs)
#             if DeviceMetaclass._is_reroute_exempted_thread():
#                 return attr_value(self, *args, **kwargs)
#             # check for method-level preferred thread name first, then class-level
#             thread_name = getattr(attr_value, '_thread_name', None) or getattr(self, '_thread_name', None)
#             #if ExecutionEngine.on_any_executor_thread():
#                 # check for device-level preferred thread
#             #    if thread_name is None or threading.current_thread().name == thread_name:
#             #        return attr_value(self, *args, **kwargs)
#             event = MethodCallEvent(method_name=attr_name, args=args, kwargs=kwargs, instance=self)
#             return self._engine.submit(event, thread_name=thread_name).await_execution()
#
#         wrapper._wrapped_for_executor = True
#         return wrapper
#
#     @staticmethod
#     def is_debugger_thread():
#         if not _python_debugger_active:
#             return False
#         # This is a heuristic and may need adjustment based on the debugger used.
#         debugger_thread_names = ["pydevd", "Debugger", "GetValueAsyncThreadDebug"]  # Common names for debugger threads
#         current_thread = threading.current_thread()
#         # Check if current thread name contains any known debugger thread names
#         return any(name in current_thread.name or name in str(current_thread.__class__.__name__)
#                    for name in debugger_thread_names)
#
#     @staticmethod
#     def _is_reroute_exempted_thread() -> bool:
#         return DeviceMetaclass.is_debugger_thread() or threading.current_thread() in _within_executor_threads
#
#     @staticmethod
#     def find_in_bases(bases, method_name):
#         for base in bases:
#             if hasattr(base, method_name):
#                 return getattr(base, method_name)
#         return None
#
#     def __new__(mcs, name: str, bases: tuple, attrs: dict) -> Any:
#         new_attrs = {}
#         for attr_name, attr_value in attrs.items():
#             if not attr_name.startswith('_'):
#                 if isinstance(attr_value, property):  # Property
#                     new_attrs[attr_name] = mcs.wrap_for_executor(attr_name, attr_value)
#                 elif callable(attr_value):  # Regular method
#                     new_attrs[attr_name] = mcs.wrap_for_executor(attr_name, attr_value)
#                 else:  # Attribute
#                     new_attrs[attr_name] = attr_value
#             else:
#                 new_attrs[attr_name] = attr_value
#
#
#         original_setattr = attrs.get('__setattr__') or mcs.find_in_bases(bases, '__setattr__') or object.__setattr__
#         def getattribute_with_fallback(self, name):
#             """ Wrap the getattribute method to fallback to getattr if an attribute is not found """
#             try:
#                 return object.__getattribute__(self, name)
#             except AttributeError:
#                 try:
#                     return self.__getattr__(name)
#                 except AttributeError as e:
#                     if _python_debugger_active and (name == 'shape' or name == '__len__'):
#                         pass  # This prevents a bunch of irrelevant errors in the Pycharm debugger
#                     else:
#                         raise e
#
#         def __getattribute__(self: 'Device', name: str) -> Any:
#             if name.startswith('_') or name in _no_executor_attrs or self._no_executor:
#                 return object.__getattribute__(self, name)
#             if DeviceMetaclass._is_reroute_exempted_thread():
#                 return getattribute_with_fallback(self, name)
#             thread_name = getattr(self, '_thread_name', None)
#             #if ExecutionEngine.on_any_executor_thread():
#             #    # check for device-level preferred thread
#             #    if thread_name is None or threading.current_thread().name == thread_name:
#             #        return getattribute_with_fallback(self, name)
#             event = GetAttrEvent(attr_name=name, instance=self, method=getattribute_with_fallback)
#             return self._engine.submit(event, thread_name=thread_name).await_execution()
#
#         def __setattr__(self: 'Device', name: str, value: Any) -> None:
#             if name in _no_executor_attrs or self._no_executor:
#                 return original_setattr(self, name, value)
#             if DeviceMetaclass._is_reroute_exempted_thread():
#                 return original_setattr(self, name, value)
#             thread_name = getattr(self, '_thread_name', None)
#             # if ExecutionEngine.on_any_executor_thread():
#             #     # Check for device-level preferred thread
#             #     if thread_name is None or threading.current_thread().name == thread_name:
#             #         return original_setattr(self, name, value)
#             event = SetAttrEvent(attr_name=name, value=value, instance=self, method=original_setattr)
#             self._engine.submit(event, thread_name=thread_name).await_execution()
#
#         new_attrs['__getattribute__'] = __getattribute__
#         new_attrs['__setattr__'] = __setattr__
#
#         new_attrs['_no_executor'] = True # For startup
#         new_attrs['_no_executor_attrs'] = _no_executor_attrs
#
#
#
#         # Create the class
#         cls = super().__new__(mcs, name, bases, new_attrs)
#
#         return cls


class Device:
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
    def __new__(cls, name: str, engine: "ExecutionEngine", *args, **kwargs):
        obj = super().__new__(cls)
        obj.__init__(name, engine, *args, **kwargs)
        return engine.register(name, obj)

    # def __init__(self, engine: "ExecutionEngine", name: str, no_executor: bool = False, no_executor_attrs: Sequence[str] = ('_name', )):
    #     """
    #     Create a new device
    #
    #     :param name: The name of the device
    #     :param no_executor: If True, all methods and attributes will be executed directly on the calling thread instead
    #     of being rerouted to the executor
    #     :param no_executor_attrs: If no_executor is False, this is a list of attribute names that will be executed
    #     directly on the calling thread
    #     """
    #     self._engine = engine
    #     self._no_executor_attrs.extend(no_executor_attrs)
    #     self._no_executor = no_executor
    #     self._name = name
    #     engine.register_device(name, self)
    #
    #
    # def get_allowed_property_values(self, property_name: str) -> Optional[list[str]]:
    #     return None  # By default, any value is allowed
    #
    # def is_property_read_only(self, property_name: str) -> bool:
    #     return False  # By default, properties are writable
    #
    # def get_property_limits(self, property_name: str) -> Tuple[Optional[float], Optional[float]]:
    #     return (None, None)  # By default, no limits
    #
    # def is_property_hardware_triggerable(self, property_name: str) -> bool:
    #     return False  # By default, properties are not hardware triggerable
    #
    # def get_triggerable_sequence_max_length(self, property_name: str) -> int:
    #     raise NotImplementedError(f"get_triggerable_sequence_max_length is not implemented for {property_name}")
    #
    # def load_triggerable_sequence(self, property_name: str, event_sequence: Iterable[Union[str, float, int]]):
    #     raise NotImplementedError(f"load_triggerable_sequence is not implemented for {property_name}")
    #
    # def start_triggerable_sequence(self, property_name: str):
    #     raise NotImplementedError(f"start_triggerable_sequence is not implemented for {property_name}")
    #
    # def stop_triggerable_sequence(self, property_name: str):
    #     raise NotImplementedError(f"stop_triggerable_sequence is not implemented for {property_name}")
