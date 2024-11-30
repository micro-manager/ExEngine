from .executor import ExecutionEngine

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

class Device:
    """
    Base class that causes the object to be automatically registered on creation.

    Usage:
        class MyDevice(Device):
            def __init__(self, name: str, engine: ExecutionEngine, ...):
                ...

        engine = ExecutionEngine()
        device = MyDevice("device_name", engine, ...)

    Has the same effect as:
        class MyDevice:
            ...

        engine = ExecutionEngine()
        device = engine.register("device_name", MyDevice(...))
    """
    def __new__(cls, name: str, engine: "ExecutionEngine", *args, **kwargs):
        obj = super().__new__(cls)
        obj.__init__(name, engine, *args, **kwargs)
        return engine.register(name, obj)

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
