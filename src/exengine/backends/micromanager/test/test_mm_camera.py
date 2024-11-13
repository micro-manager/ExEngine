import pytest
import time
import itertools
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_handler import DataHandler
from exengine.kernel.data_coords import DataCoordinates
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera
from exengine.storage_backends.ndtiff_and_ndram.NDTiffandRAM import NDRAMStorage
from exengine.events.detector_events import (StartCapture, ReadoutData,
                                             StartContinuousCapture, StopCapture)

@pytest.fixture(scope="module")
def executor():
    executor = ExecutionEngine()
    yield executor
    executor.shutdown()

@pytest.fixture
def camera(launch_micromanager):
    return MicroManagerCamera()

def capture_images(num_images, executor, camera):
    # TODO: Replace this with a mock storage class
    storage = NDRAMStorage()
    data_handler = DataHandler(storage=storage)

    start_capture_event = StartCapture(num_blocks=num_images, detector=camera)
    readout_images_event = ReadoutData(num_blocks=num_images, detector=camera,
                                       data_coordinates_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                       data_handler=data_handler)

    executor.submit([start_capture_event, readout_images_event])

    while {'time': num_images - 1} not in storage:
        time.sleep(1)

    data_handler.finish()

@pytest.mark.usefixtures("launch_micromanager")
def test_finite_sequence(executor, camera):
    capture_images(100, executor, camera)
    print('Finished first one')

@pytest.mark.usefixtures("launch_micromanager")
def test_single_image(executor, camera):
    capture_images(1, executor, camera)
    print('Finished single image')

@pytest.mark.usefixtures("launch_micromanager")
def test_multiple_single_image_captures(executor, camera):
    for _ in range(5):
        capture_images(1, executor, camera)
    print('Finished multiple single image captures')


@pytest.mark.usefixtures("launch_micromanager")
def test_continuous_capture(executor, camera):
    storage = NDRAMStorage()
    data_handler = DataHandler(storage=storage)

    start_capture_event = StartContinuousCapture(detector=camera)
    readout_images_event = ReadoutData(detector=camera,
                                       data_coordinates_iterator=(DataCoordinates(time=t) for t in itertools.count()),
                                       data_handler=data_handler)
    stop_capture_event = StopCapture(detector=camera)

    _, readout_future, _ = executor.submit([start_capture_event, readout_images_event, stop_capture_event])
    time.sleep(2)
    readout_future.stop(await_completion=True)

    data_handler.finish()
    print('Finished continuous capture')