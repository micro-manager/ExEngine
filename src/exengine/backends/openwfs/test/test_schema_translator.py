from queue import Queue

from openwfs.simulation import StaticSource
from openwfs.utilities import get_pixel_size
from exengine import ExecutionEngine
import astropy.units as u
import numpy as np

from exengine.kernel.executor import DeviceBase


class CameraSchema(DeviceBase):
    def __init__(self, *args):
        super().__init__(*args)
        self._frames = Queue()

    @staticmethod
    def map_names(class_dict):
        class_dict['exposure'] = class_dict.pop('duration')

    def start(self):
        self._frames.put(self._device.trigger())

    def pop_data(self):
        frame = self._frames.get().result()
        return frame, {"pixel_size": get_pixel_size(frame)}

def test_schema():
    # construct a camera with a random image
    img = np.random.rand(100, 100)
    pixel_size = 5 * u.micrometer
    camera = StaticSource(img, pixel_size=pixel_size)
    assert np.all(camera.read() == img)

    # wrap in ExEngine
    engine = ExecutionEngine()
    camera = engine.register("camera", camera, schema=CameraSchema)

    # test the start/pop_next protocol
    camera.start()
    frame, metadata = camera.pop_data()
    print(camera.exposure) # test if the property is present
    assert np.all(frame == img)
    assert np.allclose(metadata["pixel_size"], pixel_size * np.ones((1,2)))
    engine.shutdown()
