import threading
import pytest
import numpy as np
from typing import Dict
import time

from exengine.kernel.data_handler import DataHandler
from exengine.kernel.data_coords import DataCoordinates, DataCoordinatesIterator
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.ex_event_capabilities import DataProducing
from exengine.kernel.ex_future import ExecutionFuture

class MockDataHandler(DataHandler):
    def __init__(self):
        self.data_storage = {}

    def put(self, coords: DataCoordinates, image: np.ndarray, metadata: Dict, future: ExecutionFuture = None):
        self.data_storage[coords] = (image, metadata)

    def get(self, coords: DataCoordinates, return_data=True, return_metadata=True, processed=False):
        if coords not in self.data_storage:
            return None, None
        data, metadata = self.data_storage[coords]
        return data if return_data else None, metadata if return_metadata else None


class MockDataProducing(DataProducing, ExecutorEvent):

    def __init__(self):
        super().__init__(data_coordinates_iterator=DataCoordinatesIterator.create(
            [{"time": 0}, {"time": 1}, {"time": 2}]))
        self.data_handler = MockDataHandler()

    def execute(self):
        pass


@pytest.fixture
def mock_event():
    return MockDataProducing()


@pytest.fixture
def execution_future(mock_event):
    return ExecutionFuture(event=mock_event)


def test_notify_execution_complete(execution_future):
    """
    Test that the acquisition future is notified when the event is complete
    """

    def complete_event():
        time.sleep(0.1)
        execution_future._notify_execution_complete(None)

    # print all active threads
    for thread in threading.enumerate():
        print(thread)

    # print name of current thread
    print('current ', threading.current_thread().name)

    thread = threading.Thread(target=complete_event)
    thread.start()
    execution_future.await_execution(timeout=5)
    assert execution_future._event_complete.is_set()


def test_notify_data(execution_future):
    """
    Test that the acquisition future is notified when data is added
    """
    coords = DataCoordinates({"time": 1})
    image = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    metadata = {"some": "metadata"}

    execution_future._notify_data(coords, image, metadata)
    assert coords in execution_future._acquired_data_coordinates


def test_await_data(execution_future):
    """ Test that the acquisition future can wait for data to be added """
    coords = DataCoordinates({"time": 1})
    image = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    metadata = {"some": "metadata"}

    def wait_and_notify():
        # Delay so that the await_data call is made before the data is added it, it gets held in RAM
        # rather than retrieved from the storage_backends by the data handler
        time.sleep(2)
        execution_future._notify_data(coords, image, metadata)
    thread = threading.Thread(target=wait_and_notify)
    thread.start()

    data, meta = execution_future.await_data(coords, return_data=True, return_metadata=True)
    assert np.array_equal(data, image)
    assert meta == metadata


def test_await_data_processed(execution_future):
    """ Test that the acquisition future can wait for processed data to be added """
    coords = DataCoordinates(time=1)
    image = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    metadata = {"some": "metadata"}

    def wait_and_notify():
        # Delay so that the await_data call is made before the data is added it, it gets held in RAM
        # rather than retrieved from the storage_backends by the data handler
        time.sleep(2)
        execution_future._notify_data(coords, image, metadata, processed=True)
    thread = threading.Thread(target=wait_and_notify)
    thread.start()

    data, meta = execution_future.await_data(coords, return_data=True, return_metadata=True, processed=True)
    assert np.array_equal(data, image)
    assert meta == metadata


def test_await_data_saved(execution_future):
    coords = DataCoordinates(time=1)
    image = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    metadata = {"some": "metadata"}

    def wait_and_notify():
        # Delay so that the await_data call is made before the data is added it, it gets held in RAM
        # rather than retrieved from the storage_backends by the data handler
        time.sleep(2)
        execution_future._notify_data(coords, image, metadata, stored=True)

    thread = threading.Thread(target=wait_and_notify)
    thread.start()

    data, meta = execution_future.await_data(coords, return_data=True, return_metadata=True, stored=True)
    assert np.array_equal(data, image)
    assert meta == metadata


def test_check_if_coordinates_possible(execution_future):
    coords = DataCoordinates({"time": 1})

    try:
        execution_future._check_if_coordinates_possible(coords)
    except ValueError:
        pytest.fail("Unexpected ValueError raised")

def test_check_if_coordinates_not_possible(execution_future):
    coords = DataCoordinates(time=1, channel='not_possible')

    with pytest.raises(ValueError):
        execution_future._check_if_coordinates_possible(coords)
