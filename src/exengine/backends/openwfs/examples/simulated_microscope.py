import numpy as np
from openwfs.plot_utilities import imshow
from openwfs.simulation import StaticSource, Microscope
import astropy.units as u

from exengine import ExecutionEngine
from exengine.backends.openwfs import CameraSchema

# construct a microscope with a random image
img = (np.random.rand(100, 100) > 0.99) * 1.0
pixel_size = 0.1 * u.micrometer
specimen = StaticSource(img, pixel_size=pixel_size)
microscope = Microscope(specimen, wavelength=0.5 * u.micrometer, numerical_aperture=0.8)

engine = ExecutionEngine()
camera = engine.register("camera", microscope, schema=CameraSchema)

# test the start/pop_next protocol
camera.arm() # does nothing, OpenWFS camera is always armed
camera.start()
frame, metadata = camera.pop_data()
engine.shutdown()
imshow(frame)
input()


