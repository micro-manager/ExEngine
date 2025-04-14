# This is pseodo-code for a complex experiment that uses the exengine package.
# The same code is written in different forms to compare the readability and conciseness of the proposed api
from typing import Iterable, Annotated, List

# The code will show a live image of a three different cameras in the GUI, with the options to set properties like exposure time and gain
# In addition, there will be a button with the text "Calibrate" that will trigger a calibration script when clicked
# This calibration procedure is to move the XY stage by known distances and measure the distance moved using the cameras
# The calibration script will then calculate the conversion factor between pixels and micrometers for each of the cameras

import exengine
import harvesters
import openwfs
import pymmcore
import superstage
from exengine import ExecutionEngine
from exengine.interfaces import Camera, XYStage


# The calibration script
class CalibrationWidget:
    """Widget for calibrating pixel sizes of cameras.

    This widget demonstrates several concepts:
    * The use of the Annotated type hint to specify units and constraints for properties.
        ExEngine recognizes all public properties in the object and exposes them in the GUI.
        The Annotated type hint is used to specify units and constraints for the properties.
        These constraints are enforeced by ExEngine through the SetAttrEvent.
    * The use of the exengine.annotate.gui decorator to add a button to the GUI.
        The decorator takes the text of the button as an argument.
        The button is grayed out when the CalibrationWidget object is busy.
    * Storing device references (and lists thereof) as public attributes.
        These attributes are displayed as special fields, and allow making connections between devices.
        By specifying an interface type in the type hint, ExEngine can automatically validate
        values for these attributes.
    * Multi-device synchronization. The exengine.annotate.synchronized decorator indicates that
        during execution of this function all devices should be locked.
        Because of this decorator, the 'Calibrate' button is also grayed out when
        any of the the child devices (camera or stage) is busy.
    * Progress reporting. By requesting a '_progress' argument in any method, the engine
        will automatically provide a callback object that can be used to report progress.
        At every call to the 'update' method of this object, the progress bar in the GUI is updated.
        This also allows the user to cancel the operation, resulting in an asyncio.CancelledError exception.
    * Inter-object synchronization using the 'after' parameter.
    * Asynchronous programming. The 'capture' method of the camera returns a future.
        Instead of storing the frames, the futures are stored in a list. In this case, all measurements may get
        scheduled before the first one is completed.
    * on_complete callbacks. The futures that are returned by 'capture' send an 'on_complete' signal that
        we subscribe to in order to update the progress bar.
    * User interaction through a modal dialog box. The 'question' method of the engine is used to ask
        the user if the calibration results. For a text-base frontend, this will give a prompt in the console.
    """
    step_size: Annotated[float, Gt(0.0), Unit("um")]
    step_count: Annotated[int, Gt(0)]
    pixel_sizes: List[Annotated[float, Gt(0.0), Unit("um")]]
    cameras: Annotated[List[exengine.interfaces.Camera]]
    stage: Annotated[exengine.interfaces.XYStage]

    def __init__(self, cameras: List[Camera], stage: XYStage):
        self.step_size = 10.0
        self.step_count = 10
        self.cameras = cameras
        self.stage = stage

    @exengine.annotate.gui.button("Calibrate")
    @exengine.annotate.synchronized(True)
    def run(self, engine, /, *, _progress):
        _progress.total = self.step_count * 2
        _progress.description = "Calibrating camera magnifications"
        for axis in range(2):
            all_images = []
            start = stage.position[axis]
            for i in range(10):
                move_stage = stage.move_to(axis=axis, position=start + i * self.step_size)
                frames = [camera.capture(after=move_stage) for camera in cameras]
                frames[-1].on_complete.append(lambda: _progress.update(1))
                all_images.append(frames)

        # analyze the images
        ...

        # update pixels sizes on the cameras
        report = f"Calibration complete. Pixel sizes:\n"
        for camera, pixel_size in zip(self.cameras, self.pixel_sizes):
            report += f"\nCamera {camera.name}: {pixel_size} um\n"
        report += f"\nApply these values to the cameras?"
        if engine.gui.question("Calibration complete", report):
            for camera, pixel_size in zip(self.cameras, self.pixel_sizes):
                camera.pixel_size = pixel_size



# for the stage, we need to write our own wrapper:
class SuperStageWrapper(superstage.DualAxisStage):
    """Wrapper for a hypothetical stage that has two axes

    ExEngine will automatically recognize and wrap objects from the Micro-Manager, OpenWFS and Harvesters backends.
    In addition, it should be easy to write custom wrappers for other hardware.
    Wrapping involves:
    - exposing public properties and attributes in a thread-safe way (happens automatically)
    - converting all method calls to scheduled tasks, returning ExecutionFutures (happens automatically)
    - renaming methods and attributes to match the ExEngine schema (needs to be done manually)
    - implementing methods and properties that are required in the ExEngine schema (needs to be done manually)
    - adding metadata to the object for automatic validation, and for displaying the attribute in the gui.
    """

    # rename some existing methods and attributes to match the exengine schema
    # remove some that are not needed
    _exengine_name_map = {"axis1": "x", "axis2": "y", "bogus_attribute": None}

    def _x_max(self):
        return self.getAxisLimits(0)

    def _y_max(self):
        return self.getAxisLimits(1)

    # add missing metadata, using functions for dynamic or device-dependent metadata
    x: Annotated[float, Gt(0.0), Unit("mm"), Lt(_x_max)]
    y: Annotated[float, Gt(0.0), Unit("mm"), Lt(_y_max)]


def setup_hardware(engine):
    """
    Initialize back ends and hardware.

    The three camera's and the stages all require different backends
    ExEngine recognizes and translates Harvesters, OpenWFS and Micro-Manager objects·
    For the stage, we defined a custom wrapper.

    Note: ExEngine does not affect the initialization of the backends itself, allowing
    the user to use the full functionality of the backend libraries.
    """
    h = harvesters.core.Harvester()
    h.add_file('/Users/kznr/dev/genicam/bin/Maci64_x64/TLSimu.cti')
    h.update()
    camera1 = engine.register("camera1", h.create(0))

    camera2 = engine.register("camera2", openwfs.mockdevices.NoiseCamera("camera2"))

    mmc = pymmcore.CMMCore()
    mmc.setDeviceAdapterSearchPaths(["C:/Program Files/Micro-Manager-2.0.x"])
    mmc.loadSystemConfiguration("MMConfig_demo.cfg")
    camera3 = engine.register("camera3", mmc.getDeviceObject("cam"))

    stage = engine.register("xystage", SuperStageWrapper())
    return (camera1, camera2, camera3), stage


if __file__ == "__main__":
    # Initialize ExEngine
    engine = ExecutionEngine()

    # Construct a graphical user interface
    gui = exengine.gui.PyQT(engine)

    # initialize hardware components
    cameras, stage = setup_hardware(engine)

    # register the custom class. The 'Calibrate' button is automatically added to the property browser for the object
    stage = engine.register("calibration_script", CalibrationWidget(cameras, stage))

    # Run the GUI
    gui.run()

    engine.shutdown() # should not be needed?


