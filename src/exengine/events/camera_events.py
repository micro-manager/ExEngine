# TODO: may want to abstract this to data-producing device_implementations in general, not just cameras
from typing import Iterable, Optional, Union
from dataclasses import dataclass, field
import itertools
from exengine.kernel.ex_event_base import ExecutorEvent
from exengine.kernel.device_types_base import Detector
from exengine.kernel.data_coords import DataCoordinates
from exengine.kernel.notification_base import Notification, NotificationCategory
from exengine.capabilities.stop_and_abort import Stoppable
from exengine.capabilities.data_producing import DataProducing

class DataAcquired(Notification[DataCoordinates]):
    category = NotificationCategory.Data
    description = "Data has been acquired by a camera or other data-producing device and is now available"
    # payload is the data coordinates of the acquired data

@dataclass
class ReadoutImages(ExecutorEvent):
    """
    Readout one or more images (and associated metadata) from a camera

    Attributes:
        num_images (int): The number of images to read out. If None, the readout will continue until the
            image_coordinate_iterator is exhausted or the camera is stopped and no more images are available.
        camera (Detector): The camera object to read images from.
        stop_on_empty (bool): If True, the readout will stop when the camera is stopped when there is not an
            image available to read
        image_coordinate_iterator (Iterable[DataCoordinates]): An iterator or list of ImageCoordinates objects, which
            specify the coordinates of the images that will be read out, should be able to provide at least num_images
            elements.
    """
    image_coordinate_iterator: Iterable[DataCoordinates] = field(default=(DataCoordinates.construct(),))
    camera: Optional[Union[Detector, str]] = field(default=None)
    # TODO: should this change to a buffer object?
    num_images: int = field(default=None)
    stop_on_empty: bool = field(default=False)
    notification_types = [DataAcquired]
    capabilities = [Stoppable, DataProducing]


    def execute(self, context) -> None:
        # TODO a more efficient way to do this is with callbacks from the camera
        #  but this is not currently implemented, at least for Micro-Manager cameras
        image_counter = itertools.count() if self.num_images is None else range(self.num_images)
        for image_number, image_coordinates in zip(image_counter, self.image_coordinate_iterator):
            while True:
                # check if event.stop has been called
                if context.is_stop_requested():
                    return
                image, metadata = self.camera.pop_image(timeout=0.01) # only block for 10 ms so stop event can be checked
                if image is None and self.stop_on_empty:
                    return
                elif image is not None:
                    context.put_data(image_coordinates, image, metadata)
                    self.publish_notification(DataAcquired(image_coordinates))
                    break



@dataclass
class StartCapture(ExecutorEvent):
    """
    Special device instruction that captures images from a camera
    """
    num_images: int
    camera: Optional[Detector]

    def execute(self):
        """
        Capture images from the camera
        """
        try:
            self.camera.arm(self.num_images)
            self.camera.start()
        except Exception as e:
            self.camera.stop()
            raise e

@dataclass
class StartContinuousCapture(ExecutorEvent):
    """
    Tell data-producing device to start capturing images continuously, until a stop signal is received
    """
    camera: Optional[Detector]

    def execute(self):
        """
        Capture images from the camera
        """
        try:
            self.camera.arm()
            self.camera.start()
        except Exception as e:
            self.camera.stop()
            raise e

@dataclass
class StopCapture(ExecutorEvent):
    """
    Tell data-producing device to start capturing images continuously, until a stop signal is received
    """
    camera: Optional[Detector]

    def execute(self):
        self.camera.stop()
