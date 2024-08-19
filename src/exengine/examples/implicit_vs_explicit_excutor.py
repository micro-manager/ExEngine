from mmpycorex import create_core_instance, download_and_install_mm, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera, MicroManagerSingleAxisStage
from exengine.events.positioner_events import SetPosition1DEvent


# download_and_install_mm()  # If needed
# Start Micro-Manager core instance with Demo config
create_core_instance()

executor = ExecutionEngine()
z_stage = MicroManagerSingleAxisStage()

# This occurs on the executor thread. The event is submitted to the executor and its result is awaited,
# meaning the call will block until the method is executed.
z_stage.set_position(100, thread='device_setting_thread')
# it is equivalent to:
executor.submit(SetPosition1DEvent(position=100, device=z_stage)).await_execution()



executor.submit(SetPosition1DEvent(position=100, device=z_stage), thread='device_setting_thread')
executor.submit(ReadoutImages(), thread='readout_thread')



executor.shutdown()