"""
Unit tests for the multi_d_acquisition_events function.
"""
import pytest
import numpy as np
from pycromanager.execution_engine.kernel.device_types_base import Camera, SingleAxisPositioner, DoubleAxisPositioner
from pycromanager.execution_engine.event_implementations.multi_d_events import multi_d_acquisition_events
from pycromanager.execution_engine.event_implementations.positioner_events import SetPosition1DEvent, \
    SetTriggerable1DPositionsEvent
from pycromanager.execution_engine.event_implementations.property_events import SetTriggerablePropertySequencesEvent
from pycromanager.execution_engine.event_implementations.camera_events import StartCapture, ReadoutImages

def test_single_z_stack():
    """
    Test a single Z-stack acquisition without sequencing.
    """
    events = multi_d_acquisition_events(z_start=0, z_end=10, z_step=2)

    assert len(events) == 18  # 6 z-positions * (1 SetPosition1DEvent + 1 StartCapture + 1 ReadoutImages)
    assert isinstance(events[0], SetPosition1DEvent)
    assert isinstance(events[1], StartCapture)
    assert isinstance(events[2], ReadoutImages)


def test_sequenced_z_stack():
    """
    Test a sequenced Z-stack acquisition.
    """
    events = multi_d_acquisition_events(z_start=0, z_end=10, z_step=2, sequence='z')

    assert len(events) == 3  # 1 SetTriggerable1DPositionsEvent + 1 StartCapture + 1 ReadoutImages
    assert isinstance(events[0], SetTriggerable1DPositionsEvent)
    assert isinstance(events[1], StartCapture)
    assert isinstance(events[2], ReadoutImages)
    assert events[1].num_images == 6  # 6 z-positions


def test_sequenced_timelapse():
    """
    Test a time sequence acquisition.
    """
    num_time_points = 5
    time_interval_s = 2.0

    events = multi_d_acquisition_events(
        num_time_points=num_time_points,
        time_interval_s=time_interval_s,
        sequence='t',
        order='t'
    )

    # Check the number of events
    assert len(events) == 2  # StartCapture + ReadoutImages

    # Check the types of events
    assert isinstance(events[0], StartCapture)
    assert isinstance(events[1], ReadoutImages)

    # Check the SetTriggerablePropertySequencesEvent
    # Check the StartCapture event
    assert events[0].num_images == num_time_points

    # Check the ReadoutImages event
    readout_event = events[1]
    assert readout_event.num_images == num_time_points

    # Check the data coordinate iterator
    coords = list(readout_event.data_coordinate_iterator)
    assert len(coords) == num_time_points
    expected_coords = [{'time': i} for i in range(num_time_points)]
    assert [dict(coord) for coord in coords] == expected_coords

def test_channels_only():
    """
    Test acquisition over channels without sequencing.
    """
    events = multi_d_acquisition_events(channel_group='Channel', channels=['DAPI', 'FITC', 'TRITC'],)

    assert len(events) == 9  # 3 channels * (1 SetChannelEvent + 1 StartCapture + 1 ReadoutImages)
    assert isinstance(events[1], StartCapture)
    assert isinstance(events[2], ReadoutImages)


def test_sequenced_channels():
    """
    Test sequenced acquisition over channels.
    """
    events = multi_d_acquisition_events(channel_group='Channel', channels=['DAPI', 'FITC', 'TRITC'], sequence='c')

    assert len(events) == 3  # 1 SetTriggerablePropertySequencesEvent + 1 StartCapture + 1 ReadoutImages
    assert isinstance(events[0], SetTriggerablePropertySequencesEvent)
    assert isinstance(events[1], StartCapture)
    assert isinstance(events[2], ReadoutImages)
    assert events[1].num_images == 3  # 3 channels


def test_channels_and_z_stack_cz():
    """
    Test combined channels and Z-stack acquisition with 'cz' order.
    """
    events = multi_d_acquisition_events(
        z_start=0, z_end=10, z_step=2,
        channel_group='Channel', channels=['DAPI', 'FITC'], order='cz',)

    assert len(
        events) == 36  # 2 channels * 6 z-positions * (1 SetChannelEvent + 1 SetPosition1DEvent + 1 StartCapture + 1 ReadoutImages)


def test_channels_and_z_stack_zc():
    """
    Test combined channels and Z-stack acquisition with 'zc' order.
    """
    events = multi_d_acquisition_events(
        z_start=0, z_end=10, z_step=2,
        channel_group='Channel', channels=['DAPI', 'FITC'],
        order='zc',
    )

    assert len(
        events) == 36  # 6 z-positions * 2 channels * (1 SetPosition1DEvent + 1 SetChannelEvent + 1 StartCapture + 1 ReadoutImages)


def test_sequenced_channels_and_z_stack_zc_order():
    """
    Test sequenced acquisition for both channels and Z-stack.
    """
    events = multi_d_acquisition_events(
        z_start=0, z_end=10, z_step=2,
        channel_group='Channel', channels=['DAPI', 'FITC'],
        sequence="zc", order="zc"
    )

    # 1 SetTriggerable1DPositionsEvent + 1 SetTriggerablePropertySequencesEvent + 1 StartCapture + 1 ReadoutImages
    assert len(events) == 4
    assert isinstance(events[0], SetTriggerablePropertySequencesEvent) or isinstance(events[1], SetTriggerablePropertySequencesEvent)
    assert isinstance(events[1], SetTriggerable1DPositionsEvent) or isinstance(events[0], SetTriggerable1DPositionsEvent)
    assert isinstance(events[2], StartCapture)
    assert isinstance(events[3], ReadoutImages)

    # Check if the number of images is correct (6 z-positions * 2 channels)
    assert events[2].num_images == 12

    # Check if the number of z-positions is correct
    assert len(events[0].positions) == 12

    # Check if the channel sequence is correct (repeated for each z-position)
    expected_channel_sequence = ['DAPI', 'FITC'] * 6
    assert events[1].property_sequences[0][2] == expected_channel_sequence

    # Check if the data coordinate iterator has the correct number of coordinates
    assert len(list(events[3].data_coordinate_iterator)) == 12

    # Check if the z-positions and channels are correctly sequenced
    expected_coords = [
        {'z': 0, 'channel': 'DAPI'}, {'z': 0, 'channel': 'FITC'},
        {'z': 1, 'channel': 'DAPI'}, {'z': 1, 'channel': 'FITC'},
        {'z': 2, 'channel': 'DAPI'}, {'z': 2, 'channel': 'FITC'},
        {'z': 3, 'channel': 'DAPI'}, {'z': 3, 'channel': 'FITC'},
        {'z': 4, 'channel': 'DAPI'}, {'z': 4, 'channel': 'FITC'},
        {'z': 5, 'channel': 'DAPI'}, {'z': 5, 'channel': 'FITC'}
    ]

    assert [dict(coord) for coord in events[3].data_coordinate_iterator] == expected_coords


def test_sequenced_channels_and_z_stack_cz_order():
    """
    Test sequenced acquisition for channels and Z-stack with 'cz' order.
    """
    events = multi_d_acquisition_events(
        z_start=0, z_end=10, z_step=2,
        channel_group='Channel', channels=['DAPI', 'FITC'],
        sequence="cz", order="cz"
    )

    assert len(events) == 4
    assert isinstance(events[0], SetTriggerablePropertySequencesEvent) or isinstance(events[1], SetTriggerablePropertySequencesEvent)
    assert isinstance(events[1], SetTriggerable1DPositionsEvent) or isinstance(events[0], SetTriggerable1DPositionsEvent)
    assert isinstance(events[2], StartCapture)
    assert isinstance(events[3], ReadoutImages)
    assert events[2].num_images == 12

    expected_channel_sequence = ['DAPI'] * 6 + ['FITC'] * 6
    assert events[1].property_sequences[0][2] == expected_channel_sequence

    expected_coords = [
        {'channel': 'DAPI', 'z': 0}, {'channel': 'DAPI', 'z': 1}, {'channel': 'DAPI', 'z': 2},
        {'channel': 'DAPI', 'z': 3}, {'channel': 'DAPI', 'z': 4}, {'channel': 'DAPI', 'z': 5},
        {'channel': 'FITC', 'z': 0}, {'channel': 'FITC', 'z': 1}, {'channel': 'FITC', 'z': 2},
        {'channel': 'FITC', 'z': 3}, {'channel': 'FITC', 'z': 4}, {'channel': 'FITC', 'z': 5}
    ]
    assert [dict(coord) for coord in events[3].data_coordinate_iterator] == expected_coords

def test_sequenced_time_channels_and_z_stack_tzc_order():
    """
    Test sequenced acquisition for time, channels, and Z-stack with 'tzc' order.
    """
    events = multi_d_acquisition_events(
        num_time_points=3, time_interval_s=1,
        z_start=0, z_end=6, z_step=2,
        channel_group='Channel', channels=['DAPI', 'FITC'],
        sequence="tzc", order="tzc"
    )

    assert len(events) == 4
    assert isinstance(events[0], SetTriggerablePropertySequencesEvent) or isinstance(events[0], SetTriggerable1DPositionsEvent)
    assert isinstance(events[1], SetTriggerable1DPositionsEvent) or isinstance(events[1], SetTriggerablePropertySequencesEvent)
    assert isinstance(events[2], StartCapture)
    assert events[2].num_images == 24  # 3 time points * 4 z-positions * 2 channels


    expected_z_sequence = np.array([0, 0, 2, 2, 4, 4, 6, 6, 0, 0, 2, 2, 4, 4, 6, 6, 0, 0, 2, 2, 4, 4, 6, 6])
    assert np.array_equal(events[0].positions, expected_z_sequence)

    expected_channel_sequence = ['DAPI', 'FITC'] * 12  # Repeats for each time and z combination
    assert events[1].property_sequences[0][2] == expected_channel_sequence

    # Check the first few and last few coordinates
    coords = list(events[3].data_coordinate_iterator)
    assert len(coords) == 24
    assert [dict(coord) for coord in coords[:4]] == [
        {'time': 0, 'z': 0, 'channel': 'DAPI'}, {'time': 0, 'z': 0, 'channel': 'FITC'},
        {'time': 0, 'z': 1, 'channel': 'DAPI'}, {'time': 0, 'z': 1, 'channel': 'FITC'}
    ]
    assert [dict(coord) for coord in coords[-4:]] == [
        {'time': 2, 'z': 2, 'channel': 'DAPI'}, {'time': 2, 'z': 2, 'channel': 'FITC'},
        {'time': 2, 'z': 3, 'channel': 'DAPI'}, {'time': 2, 'z': 3, 'channel': 'FITC'}
    ]

def test_sequenced_channels_and_positions():
    """
    Test sequenced acquisition for channels and XY positions.
    """
    events = multi_d_acquisition_events(
        channel_group='Channel', channels=['DAPI', 'FITC'],
        xy_positions=[(0, 0), (100, 100), (200, 200)],
        sequence="cp", order="cp"
    )

    assert len(events) == 4
    assert isinstance(events[0], SetTriggerablePropertySequencesEvent)  # Channel
    assert isinstance(events[1], StartCapture)
    assert isinstance(events[2], ReadoutImages)
    assert events[1].num_images == 6  # 2 channels * 3 positions

    expected_channel_sequence = ['DAPI', 'FITC'] * 3  # Repeats for each position
    assert events[0].property_sequences[0][2] == expected_channel_sequence

    coords = list(events[2].data_coordinate_iterator)
    assert len(coords) == 6
    expected_coords = [
        {'channel': 'DAPI', 'position': 0}, {'channel': 'FITC', 'position': 0},
        {'channel': 'DAPI', 'position': 1}, {'channel': 'FITC', 'position': 1},
        {'channel': 'DAPI', 'position': 2}, {'channel': 'FITC', 'position': 2}
    ]
    assert [dict(coord) for coord in coords] == expected_coords

def test_error_incompatible_sequence_and_order():
    """
    Test that an error is raised when sequence and order are incompatible.
    """
    with pytest.raises(ValueError, match="Can only sequence over inner axes"):
        multi_d_acquisition_events(
            z_start=0, z_end=10, z_step=2,
            channel_group='Channel', channels=['DAPI', 'FITC'],
            sequence="cz", order="zc"
        )
