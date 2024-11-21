"""
Additional functionalities that can be added to ExecutorEvents
"""
from typing import Dict, Union, Iterable, TYPE_CHECKING
import itertools

import numpy.typing as npt

from .data_coords import DataCoordinates, DataCoordinatesIterator
from .data_handler import DataHandler

if TYPE_CHECKING:
    from typing import Any


class DataProducing:
    """
    Acquisition events that produce data should inherit from this class. They are responsible for putting data
    into the output queue. This class provides a method for putting data into the output queue. It must be passed
    a DataHandler object that will handle the data, and an image_coordinate_iterator object that generates the
    coordinates of each piece of data (i.e. image) that will be produced by the event. For example, {time: 0},
    {time: 1}, {time: 2} for a time series acquisition.
    """

    def __init__(self, data_coordinates_iterator: Union[DataCoordinatesIterator,
        Iterable[DataCoordinates], Iterable[Dict[str, Union[int, str]]]] = None,
                 data_handler: DataHandler = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if data_coordinates_iterator is None:
            # create a default data_coordinate_iterator that just counts up from 0
            def image_generator():
                for i in itertools.count():
                    yield {'image': i}
            data_coordinates_iterator = image_generator()
        # Handles auto-conversion of data_coordinate_iterator from dict types
        self.data_coordinate_iterator = DataCoordinatesIterator.create(data_coordinates_iterator)
        self._data_handler = data_handler


    def put_data(self, data_coordinates: DataCoordinates, image: npt.NDArray["Any"], metadata: Dict):
        """
        Put data into the output queue
        """
        # TODO: replace future weakref with just a callable?
        self._data_handler.put(data_coordinates, image, metadata, self._future_weakref())




class Stoppable:
    """
    This capability adds the ability to stop ExecutorEvents that are running or ar going to run. The implementation
    of the event is responsible for checking if is_stop_requested() returns True and stopping their execution if it
    does. When stopping, an orderly shutdown should be performed, unlike when aborting, which should be immediate.
    The details of what such an orderly shutdown entails are up to the implementation of the event.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_requested = False

    def is_stop_requested(self) -> bool:
        return self._stop_requested

    def _request_stop(self):
        self._stop_requested = True


class Abortable:
    """
    Acquisition events that can be aborted should inherit from this class. They are responsible for checking if
    is_abort_requested() returns True and aborting their execution if it does. When aborted, the event should
    immediately stop its execution.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._abort_requested = False

    def is_abort_requested(self) -> bool:
        return self._abort_requested

    def _request_abort(self):
        self._abort_requested = True




