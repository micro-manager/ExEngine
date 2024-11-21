# TODO: may want to abstract this to data-producing device_implementations in general, not just cameras
from typing import Iterable, Optional, Union, Dict
import itertools
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.device_types import Detector
from exengine.kernel.data_coords import DataCoordinates, DataCoordinatesIterator
from exengine.kernel.notification_base import Notification, NotificationCategory
from exengine.kernel.ex_event_capabilities import Stoppable, DataProducing
from exengine.kernel.data_handler import DataHandler
from exengine import ExecutionEngine


class DataAcquiredNotification(Notification[DataCoordinates]):
    category = NotificationCategory.Data
    description = "Data has been acquired by a detector or other data-producing device and is now available"
    # payload is the data coordinates of the acquired data

class ReadoutData(Stoppable, DataProducing, ExecutorEvent):
    """
    Readout one or more blocks of data (e.g. images) and associated metadata from a Detector device (e.g. a camera)

    Parameters:
    ------------
    data_coordinate_iterator: Iterable[DataCoordinates]
            An iterator or list of DataCoordinates objects, which
            specify the coordinates of the data that will be read out, should be able to provide at least num_images
            elements (or indefinitely if num_images is None)
    detector: Union[Detector, str]
            The Detector object to read data from. Can be the object itself,
            or the name of the object in the ExecutionEngine's device registry.
    num_blocks: int
            The number of pieces of data (e.g. images) to read out. If None, the readout will continue until
            the data_coordinate_iterator is exhausted or the Detector is stopped and no more images are available.
    stop_on_empty: bool
            (Experimental) If True, the readout will stop when the detector is stopped when there is no data
            available to read
    data_handler: DataHandler
            The DataHandler object that will handle the data read out by this event
    """
    notification_types = [DataAcquiredNotification]

    def __init__(self,
                 data_coordinates_iterator: Union[DataCoordinatesIterator,
                                                  Iterable[DataCoordinates],
                                                  Iterable[Dict[str, Union[int, str]]]],
                 detector: Optional[Union[Detector, str]] = None,
                 data_handler: DataHandler = None,
                 num_blocks: int = None,
                 stop_on_empty: bool = False):
        super().__init__(data_coordinates_iterator=data_coordinates_iterator, data_handler=data_handler)
        self.detector = detector  # TODO: why does IDE not like this type hint?
        self.num_blocks = num_blocks
        self.stop_on_empty = stop_on_empty


    def execute(self) -> None:
        # if detector is a string, look it up in the device registry
        self.detector: Detector = (self.detector if isinstance(self.detector, Detector)
                                      else ExecutionEngine.get_device(self.detector))
        # TODO a more efficient way to do this is with callbacks from the detector
        # but this is not currently implemented, at least for Micro-Manager cameras
        image_counter = itertools.count() if self.num_blocks is None else range(self.num_blocks)
        for image_number, image_coordinates in zip(image_counter, self.data_coordinate_iterator):
            while True:
                # check if event.stop has been called
                if self.is_stop_requested():
                    return
                image, metadata = self.detector.pop_data(timeout=0.01) # only block for 10 ms so stop event can be checked
                if image is None and self.stop_on_empty:
                    return
                elif image is not None:
                    self.put_data(image_coordinates, image, metadata)
                    self.publish_notification(DataAcquiredNotification(image_coordinates))
                    break



class StartCapture(ExecutorEvent):
    """
    Special device instruction that captures images from a Detector device (e.g. a camera)
    """

    def __init__(self, num_blocks: int, detector: Optional[Detector] = None):
        """
        Args:
            num_blocks (int): The of pieces of data to capture (i.e. images on a camera)
            detector (Union[Detector, str]): The Detector object to capture images from. Can be the object itself,
                or the name of the object in the ExecutionEngine's device registry. If None, it will be inferred at
                runtime
        """
        super().__init__()
        self.num_blocks = num_blocks
        self.detector = detector

    def execute(self):
        """
        Capture images from the detector
        """
        try:
            self.detector.arm(self.num_blocks)
            self.detector.start()
        except Exception as e:
            self.detector.stop()
            raise e

class StartContinuousCapture(ExecutorEvent):
    """
    Tell Detector device to start capturing images continuously, until a stop signal is received
    """

    def __init__(self, detector: Optional[Detector] = None):
        super().__init__()
        self.detector = detector

    def execute(self):
        """
        Capture images from the detector
        """
        try:
            self.detector.arm()
            self.detector.start()
        except Exception as e:
            self.detector.stop()
            raise e

class StopCapture(ExecutorEvent):
    """
    Tell Detector device to start capturing data continuously, until a stop signal is received
    """

    def __init__(self, detector: Optional[Detector] = None):
        super().__init__()
        self.detector = detector

    def execute(self):
        self.detector.stop()
