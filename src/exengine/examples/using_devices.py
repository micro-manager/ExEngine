from mmpycorex import create_core_instance, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera, MicroManagerSingleAxisStage


# download_and_install_mm()  # If needed
# Start Micro-Manager core instance with Demo config
create_core_instance()

executor = ExecutionEngine()

# Create Micro-Manager Devices
camera = MicroManagerCamera()
z_stage = MicroManagerSingleAxisStage()

# By default, setting/getting attributes and calling methods occure on the main executor thread
# This sets the property of the Micro-Manager camera object
camera.Exposure = 100

camera.arm(1)
camera.start()
image, metadata = camera.pop_data()


print(image)

executor.shutdown()
terminate_core_instances()