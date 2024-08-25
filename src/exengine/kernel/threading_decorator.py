import functools
from typing import Optional, Union, Type, Callable

def on_thread(thread_name: Optional[str] = None):
    """
    Decorator to specify the preferred thread name for a class or method.
    """
    def decorator(obj: Union[Type, Callable]):
        if isinstance(obj, type):
            # It's a class
            obj._thread_name = thread_name
            return obj
        else:
            # It's a method or function
            @functools.wraps(obj)
            def wrapper(*args, **kwargs):
                return obj(*args, **kwargs)
            wrapper._thread_name = thread_name
            return wrapper

    return decorator