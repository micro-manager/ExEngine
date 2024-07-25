from mmpycorex import create_core_instance, download_and_install_mm, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_coords import DataCoordinates
from exengine.kernel.ex_event_base import DataHandler
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera, MicroManagerSingleAxisStage
from exengine.storage_backends.NDTiffandRAM import NDRAMStorage
from exengine.events.detector_events import StartCapture, ReadoutData


# download_and_install_mm()  # If needed
# Start Micro-Manager core instance with Demo config
create_core_instance()

executor = ExecutionEngine()


# Create Micro-Manager Devices
camera = MicroManagerCamera()
z_stage = MicroManagerSingleAxisStage()


# Capture 100 images on the camera
num_images = 100
data_handler = DataHandler(storage=NDRAMStorage())

start_capture_event = StartCapture(num_images=num_images, camera=camera)
readout_images_event = ReadoutData(num_images=num_images, camera=camera,
                                   data_coordinate_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                   data_handler=data_handler)
executor.submit(start_capture_event)
future = executor.submit(readout_images_event)

future.await_execution()
executor.check_exceptions()

data_handler.finish()

executor.shutdown()
terminate_core_instances()

