from exengine.kernel.executor import DeviceBase
from openwfs.utilities import get_pixel_size
from queue import Queue

class CameraSchema(DeviceBase):
    def __init__(self, *args):
        super().__init__(*args)
        self._frames = Queue()

    @staticmethod
    def map_names(class_dict):
        class_dict['exposure'] = class_dict.pop('duration')

    def arm(self):
        pass

    def start(self):
        self._frames.put(self._device.trigger())

    def pop_data(self):
        frame = self._frames.get().result()
        return frame, {"pixel_size": get_pixel_size(frame)}
