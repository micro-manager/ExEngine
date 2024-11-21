"""
exengine package

A flexible multi-backend execution engine for microscopy
"""
from ._version import __version__, version_info

from .kernel.executor import ExecutionEngine
from .kernel.threading_decorator import on_thread

__all__ = [
    "ExecutionEngine",
    "on_thread",
    "__version__",
    "version_info",
]
