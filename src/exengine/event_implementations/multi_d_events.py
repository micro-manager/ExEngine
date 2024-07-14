from pycromanager.execution_engine.event_implementations.positioner_events import SetPosition2DEvent, SetPosition1DEvent
from pycromanager.execution_engine.event_implementations.camera_events import StartCapture, ReadoutImages
from pycromanager.execution_engine.kernel.acq_event_base import AcquisitionEvent
from pycromanager.execution_engine.event_implementations.misc_events import SetTimeEvent
from pycromanager.execution_engine.kernel.device_types_base import SingleAxisPositioner, DoubleAxisPositioner, Camera
from pycromanager.execution_engine.kernel.data_coords import DataCoordinates
from pycromanager.execution_engine.event_implementations.property_events import (SetTriggerablePropertySequencesEvent,
                                                                                 SetPropertiesEvent)
from pycromanager.execution_engine.event_implementations.positioner_events import SetTriggerable1DPositionsEvent, SetPosition1DEvent
from pycromanager.execution_engine.device_implementations.micromanager.mm_utils import read_mm_config_groups
from typing import Union, List, Iterable, Optional
import numpy as np
import copy
from itertools import chain

def flatten(lst):
    return list(chain(*[flatten(x) if isinstance(x, list) else [x] for x in lst]))


def multi_d_acquisition_events(
        num_time_points: int = None,
        time_interval_s: Union[float, List[float]] = 0,
        z_start: float = None,
        z_end: float = None,
        z_step: float = None,

        channel_group: str = None,
        channels: list = None, # TODO: this can be tree of device: properties?
        channel_exposures_ms: list = None,

        xy_positions: Iterable = None,
        xyz_positions: Iterable = None,
        position_labels: List[str] = None,
        order: str = "tpcz",
        sequence: str = None, # should be "zc", "cz", "tzc", etc
        camera: Optional[Union[Camera, str]] = None,
        xy_device: Optional[SingleAxisPositioner] = None,
        z_device: Optional[SingleAxisPositioner] = None,
):


    # TODO: docstring
    if channel_group is not None or channels is not None or channel_exposures_ms is not None:
        raise NotImplementedError("Channels are not yet implemented")


    if sequence is not None and not order.endswith(sequence):
        raise ValueError("Can only sequence over inner axes")

    if xy_positions is not None and xyz_positions is not None:
        raise ValueError("xyz_positions and xy_positions are incompatible arguments that cannot be passed together")

    order = order.lower()
    if "p" in order and "z" in order and order.index("p") > order.index("z"):
        raise ValueError("This function requires that the xy position come earlier in the order than z")

    if isinstance(time_interval_s, list):
        if len(time_interval_s) != num_time_points:
            raise ValueError("Length of time interval list should be equal to num_time_points")


    if position_labels is not None:
        if xy_positions is not None and len(xy_positions) != len(position_labels):
            raise ValueError("xy_positions and position_labels must be of equal length")
        if xyz_positions is not None and len(xyz_positions) != len(position_labels):
            raise ValueError("xyz_positions and position_labels must be of equal length")

    has_zsteps = False
    if any([z_start, z_step, z_end]):
        if not None in [z_start, z_step, z_end]:
            has_zsteps = True
        else:
            raise ValueError('All of z_start, z_step, and z_end must be provided')

    z_positions = None
    if xy_positions is not None:
        xy_positions = np.asarray(xy_positions)
        z_positions = None
    elif xyz_positions is not None:
        xyz_positions = np.asarray(xyz_positions)
        xy_positions = xyz_positions[:, :2]
        z_positions = xyz_positions[:, 2][:, None]

    if has_zsteps:
        z_rel = np.arange(z_start, z_end + z_step, z_step)
        if z_positions is None:
            z_positions = z_rel
            if xy_positions is not None:
                z_positions = np.broadcast_to(z_positions, (xy_positions.shape[0], z_positions.shape[0]))
        else:
            pos = []
            for z in z_positions:
                pos.append(z + z_rel)
            z_positions = np.asarray(pos)

    if position_labels is None and xy_positions is not None:
        position_labels = list(range(len(xy_positions)))

    def generate_events(event_list, order, coords=None):
        if coords is None:
            coords = {}
        if len(order) == 0:
            yield event_list, coords
            return

        elif sequence is not None and order == sequence:
            # Hardware sequencing over inner axes
            total_sequence_length = 1
            axis_lengths = {}
            for axis in sequence:
                if axis == 't':
                    axis_lengths[axis] = num_time_points
                elif axis == 'z':
                    axis_lengths[axis] = len(z_positions)
                elif axis == 'c':
                    axis_lengths[axis] = len(channels)
                else:
                    raise ValueError(f"Unknown sequence axis: {axis}")
                total_sequence_length *= axis_lengths[axis]

            sequences = {}
            for i, axis in enumerate(sequence):
                if axis == 't':
                    values = np.arange(num_time_points)
                elif axis == 'z':
                    values = z_positions
                elif axis == 'c':
                    values = channels
                else:
                    raise ValueError(f"Unknown sequence axis: {axis}")

                if axis == sequence[-1]:
                    # Innermost axis: repeat the values
                    repeat_count = total_sequence_length // len(values)
                    sequences[axis] = np.tile(values, repeat_count)
                else:
                    # Other axes: duplicate each value
                    inner_product = np.prod([axis_lengths[a] for a in sequence[i + 1:]])
                    outer_product = np.prod([axis_lengths[a] for a in sequence[:i]])
                    sequences[axis] = np.tile(np.repeat(values, inner_product), outer_product)

            # Create single events with full sequences for each axis
            new_event_list = copy.deepcopy(event_list)
            if 'z' in sequence:
                new_event_list.append(SetTriggerable1DPositionsEvent(
                    device=z_device, positions=sequences['z']
                ))
            if 'c' in sequence:
                raise NotImplementedError("Channel sequencing not yet implemented")
                # new_event_list.append(SetTriggerablePropertySequencesEvent(
                #     property_sequences=[(channel_group, 'Label', sequences['c'].tolist())]
                # ))

            # Add StartCapture event
            new_event_list.append(StartCapture(camera=camera, num_images=total_sequence_length))

            # Create data coordinates for ReadoutImages
            axes_names = {"t": "time", "z": "z", "c": "channel", "p": "position"}
            coords_iterator = [
                DataCoordinates(**{
                    axes_names[axis]: {v: i for i, v in enumerate(dict.fromkeys(sequences[axis]))}[sequences[axis][i]]
                    if isinstance(sequences[axis][0], (int, float, np.number))
                    else sequences[axis][i]
                    for axis in sequence
                })
                for i in range(total_sequence_length)
            ]

            new_event_list.append(ReadoutImages(
                camera=camera,
                num_images=total_sequence_length,
                data_coordinate_iterator=coords_iterator
            ))

            yield new_event_list, coords

        elif order[0] == "t" and num_time_points is not None and num_time_points > 0:
            time_indices = np.arange(num_time_points)
            if isinstance(time_interval_s, list):
                absolute_start_times = np.cumsum(time_interval_s)
            for time_index in time_indices:
                new_event_list = copy.deepcopy(event_list)
                new_coords = copy.deepcopy(coords)
                if isinstance(time_interval_s, list):
                    min_start_time = absolute_start_times[time_index]
                else:
                    min_start_time = time_index * time_interval_s if time_interval_s != 0 else None
                new_event_list.append(SetTimeEvent(time_index=time_index, min_start_time=min_start_time))
                new_coords['time'] = time_index
                yield from generate_events(new_event_list, order[1:], new_coords)
        elif order[0] == "z" and z_positions is not None:
            for z_index, z in enumerate(z_positions.flatten()):
                new_event_list = copy.deepcopy(event_list)
                new_coords = copy.deepcopy(coords)
                new_event_list.append(SetPosition1DEvent(device=z_device, position=z))
                new_coords['z'] = z_index
                yield from generate_events(new_event_list, order[1:], new_coords)
        elif order[0] == "p" and xy_positions is not None:
            for p_index, (p_label, xy) in enumerate(zip(position_labels, xy_positions)):
                new_event_list = copy.deepcopy(event_list)
                new_coords = copy.deepcopy(coords)
                new_event_list.append(SetPosition2DEvent(device=xy_device, position=xy))
                new_coords['position'] = p_label
                yield from generate_events(new_event_list, order[1:], new_coords)

        elif order[0] == "c" and channel_group is not None and channels is not None:
            for i, channel in enumerate(channels):
                new_event_list = copy.deepcopy(event_list)
                new_coords = copy.deepcopy(coords)
                exposure = channel_exposures_ms[i] if channel_exposures_ms is not None else None
                new_event_list.append(
                    SetPropertiesEvent(channel_group=channel_group, channel=channel, exposure_ms=exposure))
                new_coords['channel'] = channel
                yield from generate_events(new_event_list, order[1:], new_coords)
        else:
            yield from generate_events(event_list, order[1:], coords)

    all_events = list(generate_events([], order))

    final_events = []
    for event_set, coords in all_events:
        if sequence is None:
            # Non-sequenced case: Add StartCapture and ReadoutImages events
            num_images = 1
            event_set.append(StartCapture(camera=camera, num_images=num_images))
            event_set.append(ReadoutImages(camera=camera, num_images=num_images,
                                           data_coordinate_iterator=[DataCoordinates(**coords)]))

        final_events.append(event_set)

    return flatten(final_events)