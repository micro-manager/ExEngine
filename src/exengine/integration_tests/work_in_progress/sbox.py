from mmpycorex import create_core_instance, terminate_core_instances
from exengine.kernel.data_coords import DataCoordinates
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera
import os
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.acq_event_base import DataHandler
from exengine.storage_backends.NDTiffandRAM import NDRAMStorage
from exengine.events.camera_events import StartCapture, ReadoutImages

mm_install_dir = '/Users/henrypinkard/Micro-Manager'
config_file = os.path.join(mm_install_dir, 'MMConfig_demo.cfg')
create_core_instance(mm_install_dir, config_file,
               buffer_size_mb=1024, max_memory_mb=1024,  # set these low for github actions
               python_backend=True,
               debug=False)


executor = ExecutionEngine()



camera = MicroManagerCamera()

num_images = 100
data_handler = DataHandler(storage=NDRAMStorage())

start_capture_event = StartCapture(num_images=num_images, camera=camera)
readout_images_event = ReadoutImages(num_images=num_images, camera=camera,
                                     image_coordinate_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                     data_handler=data_handler)
executor.submit(start_capture_event)
future = executor.submit(readout_images_event)

future.await_execution()

data_handler.finish()

executor.shutdown()
terminate_core_instances()



# # print all threads that are still a
# import threading
#
# for thread in threading.enumerate():
#     print(thread)
# pass