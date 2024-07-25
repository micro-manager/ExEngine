"""
Tests with Micro-Manaager Demo config hardware for running multi-dimensional acquisitions using direct
construction of low-level acquisition events
"""

import os
import numpy as np
import pytest
from mmpycorex import create_core_instance, terminate_core_instances, get_default_install_location
from exengine.backends.micromanager.mm_device_implementations import (
    MicroManagerSingleAxisStage, MicroManagerDevice, MicroManagerXYStage, MicroManagerCamera
)
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_handler import DataHandler
from exengine.storage_backends.NDTiffandRAM import NDRAMStorage
from exengine.events.positioner_events import (
    SetPosition1DEvent, SetTriggerable1DPositionsEvent, StopTriggerablePositionSequenceEvent
)
from exengine.events.property_events import (
    SetTriggerablePropertySequencesEvent, StopTriggerablePropertySequencesEvent
)
from exengine.kernel.data_coords import DataCoordinates
from exengine.events.detector_events import StartCapture, ReadoutData


@pytest.fixture(scope="module")
def setup_micromanager():
    mm_install_dir = get_default_install_location()
    config_file = os.path.join(mm_install_dir, 'MMConfig_demo.cfg')
    create_core_instance(mm_install_dir, config_file,
                   buffer_size_mb=1024, max_memory_mb=1024,
                   python_backend=True,
                   debug=False)
    yield
    terminate_core_instances()


@pytest.fixture(scope="module")
def execution_engine():
    return ExecutionEngine()


@pytest.fixture(scope="module")
def devices():
    z_device = MicroManagerSingleAxisStage('Z')
    camera_device = MicroManagerCamera()
    xy_device = MicroManagerXYStage()
    return z_device, camera_device, xy_device


def test_non_sequenced_z_stack(setup_micromanager, execution_engine, devices):
    z_device, camera_device, _ = devices
    storage = NDRAMStorage()
    data_handler = DataHandler(storage)

    events = []
    for z_index, z_pos in enumerate(np.arange(0, 20, 4)):
        events.append(SetPosition1DEvent(device=z_device, position=z_pos))
        events.append(StartCapture(detector=camera_device, num_images=1))
        events.append(ReadoutData(detector=camera_device, data_coordinates_iterator=[DataCoordinates(z=z_index)],
                                  data_handler=data_handler))

    futures = execution_engine.submit(events)
    futures[-1].await_execution()

    means = [storage[{'z': i}].mean() for i in range(5)]
    assert all(means[i] > means[i + 1] for i in range(4))
    data_handler.finish()


def test_sequenced_z_stack(setup_micromanager, execution_engine, devices):
    z_device, camera_device, _ = devices
    storage = NDRAMStorage()
    data_handler = DataHandler(storage)

    z_device.UseSequences = 'Yes'
    assert z_device.UseSequences == 'Yes'

    z_positions = np.arange(0, 20, 4)
    z_sequence = SetTriggerable1DPositionsEvent(device=z_device, positions=z_positions)
    start_capture_event = StartCapture(detector=camera_device, num_images=len(z_positions))
    readout_event = ReadoutData(detector=camera_device,
                                data_coordinates_iterator=(DataCoordinates(z=z) for z in range(len(z_positions))),
                                data_handler=data_handler)
    stop_sequence_event = StopTriggerablePositionSequenceEvent(device=z_device)

    _, _, _, future = execution_engine.submit([z_sequence, start_capture_event, readout_event, stop_sequence_event])

    future.await_execution()
    execution_engine.check_exceptions()
    data_handler.finish()

    means = [storage[{'z': i}].mean() for i in range(len(z_positions))]
    assert all(means)


def test_sequence_over_channels(setup_micromanager, execution_engine, devices):
    _, camera_device, _ = devices
    storage = NDRAMStorage()
    data_handler = DataHandler(storage)

    objective_device = MicroManagerDevice('Objective')
    values = ['Nikon 10X S Fluor', 'Nikon 20X Plan Fluor ELWD', 'Nikon 40X Plan Fluor ELWD']
    channel_names = ['A', 'B', 'C']
    prop_sequence = SetTriggerablePropertySequencesEvent(property_sequences=[(objective_device, 'Label', values)])
    start_capture_event = StartCapture(detector=camera_device, num_images=len(values))
    readout_event = ReadoutData(detector=camera_device,
                                data_coordinates_iterator=(DataCoordinates(channel=c) for c in channel_names),
                                data_handler=data_handler)
    stop_sequence_event = StopTriggerablePropertySequencesEvent(property_sequences=[(objective_device, 'Label')])

    _, _, _, future = execution_engine.submit([prop_sequence, start_capture_event, readout_event, stop_sequence_event])

    future.await_execution()
    execution_engine.check_exceptions()
    data_handler.finish()

    means = [storage[{'channel': channel}].mean() for channel in channel_names]
    assert all(means)


def test_shutdown(execution_engine):
    execution_engine.shutdown()