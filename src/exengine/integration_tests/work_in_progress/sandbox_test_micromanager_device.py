from exengine.kernel.data_coords import DataCoordinates
import os
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.ex_event_base import DataHandler
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera
from exengine.storage_backends.NDTiffandRAM import NDRAMStorage
from exengine.events.detector_events import StartCapture, ReadoutData
from mmpycorex import create_core_instance, terminate_core_instances

mm_install_dir = '/Users/henrypinkard/Micro-Manager'
config_file = os.path.join(mm_install_dir, 'MMConfig_demo.cfg')
create_core_instance(mm_install_dir, config_file,
               buffer_size_mb=1024, max_memory_mb=1024,  # set these low for github actions
               python_backend=True,
               debug=False)


executor = ExecutionEngine()



camera = MicroManagerCamera()

num_images = 100
# Create a data handle to manage the handoff of data from the camera to the storage backend
storage = NDRAMStorage()
data_handler = DataHandler(storage=storage)

start_capture_event = StartCapture(num_images=num_images, camera=camera)
readout_images_event = ReadoutData(num_images=num_images, camera=camera,
                                   data_coordinate_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                   data_handler=data_handler)
executor.submit(start_capture_event)
future = executor.submit(readout_images_event)

# Wait for all images to be readout
future.await_execution()
executor.check_exceptions()

data_handler.finish()
executor.shutdown()
terminate_core_instances()
