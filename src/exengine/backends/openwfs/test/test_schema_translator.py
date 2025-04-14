from exengine import ExecutionEngine
from openwfs.simulation import StaticSource
from openwfs.plot_utilities import imshow
from openwfs.simulation.microscope import Microscope
import astropy.units as u
import numpy as np
import matplotlib.pyplot as plt
from exengine.backends.openwfs import CameraSchema


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
    camera.arm() # does nothing, OpenWFS camera is always armed
    camera.start()
    frame, metadata = camera.pop_data()
    print(camera.exposure) # test if the property is present
    assert np.all(frame == img)
    assert np.allclose(metadata["pixel_size"], pixel_size * np.ones((1,2)))
    engine.shutdown()
