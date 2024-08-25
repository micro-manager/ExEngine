# src/exengine/integration_tests/test_imports.py

import pytest


def test_import_engine():
    try:
        from exengine import ExecutionEngine
    except ImportError as e:
        pytest.fail(f"Import failed for ExecutionEngine: {e}")


def test_import_base_classes():
    try:
        from exengine.base_classes import (Notification, ExecutorEvent, NotificationCategory, Abortable,
                                           DataProducing, Stoppable, DataStorage)
    except ImportError as e:
        pytest.fail(f"Import failed for base_classes: {e}")

def test_import_notifications():
    try:
        from exengine.notifications import NotificationCategory, DataStoredNotification, EventExecutedNotification
    except ImportError as e:
        pytest.fail(f"Import failed for notifications: {e}")

def test_import_data():
    try:
        from exengine.data import DataCoordinates, DataCoordinatesIterator, DataHandler
    except ImportError as e:
        pytest.fail(f"Import failed for data: {e}")

def test_mm_imports():
    try:
        from exengine.backends.micromanager import (MicroManagerDevice, MicroManagerCamera,
                                                    MicroManagerSingleAxisStage, MicroManagerXYStage)
    except ImportError as e:
        pytest.fail(f"Import failed for MicroManagerDevice: {e}")

def test_onthread_import():
    try:
        from exengine import on_thread
    except ImportError as e:
        pytest.fail(f"Import failed for MicroManagerDevice: {e}")

def test_ndstorage_imports():
    try:
        from exengine.storage_backends.ndtiff_and_ndram import NDTiffStorage, NDRAMStorage
    except ImportError as e:
        pytest.fail(f"Import failed for MicroManagerDevice: {e}")