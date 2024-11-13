from mmpycorex import create_core_instance, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_coords import DataCoordinates
from exengine.kernel.notification_base import Notification, NotificationCategory
from exengine.data import DataHandler
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera, MicroManagerSingleAxisStage
from exengine.storage_backends.ndtiff_and_ndram import NDRAMStorage
from exengine.events.detector_events import StartCapture, ReadoutData

def callback(notification: Notification) -> None:
    print(f"Notification received: {notification.category} - {notification.payload}")

# download_and_install_mm()  # If needed
# Start Micro-Manager core instance with Demo config
create_core_instance()

executor = ExecutionEngine()

# Create Micro-Manager Devices
camera = MicroManagerCamera()
z_stage = MicroManagerSingleAxisStage()

# Capture 100 images on the camera
num_images = 5
data_handler = DataHandler(storage=NDRAMStorage())

start_capture_event = StartCapture(num_blocks=num_images, detector=camera)
readout_images_event = ReadoutData(num_blocks=num_images, detector=camera,
                                   data_coordinates_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                   data_handler=data_handler)

executor.subscribe_to_notifications(callback, NotificationCategory.Data)

executor.submit(start_capture_event)
future = executor.submit(readout_images_event)

future.await_execution()
executor.check_exceptions()

data_handler.finish()

executor.shutdown()
terminate_core_instances()

