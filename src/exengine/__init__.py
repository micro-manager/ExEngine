"""
exengine package

A flexible multi-backend execution engine for microscopy
"""
from ._version import __version__, version_info

from . import kernel
from .kernel.executor import ExecutionEngine
