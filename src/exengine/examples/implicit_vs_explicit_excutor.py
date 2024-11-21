from mmpycorex import create_core_instance, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.notification_base import Notification
from exengine.backends.micromanager.mm_device_implementations import MicroManagerSingleAxisStage
from exengine.events.positioner_events import SetPosition1DEvent

def event_complete(notification: Notification) -> None:
    print(f"Event complete, notification: {notification.category} - {notification.description} - {notification.payload}")

# download_and_install_mm()  # If needed
# Start Micro-Manager core instance with Demo config
try:
    create_core_instance()

    executor = ExecutionEngine()
    z_stage = MicroManagerSingleAxisStage()

    executor.subscribe_to_notifications(event_complete)

    # explicit
    z_stage.set_position(100)
    # it is equivalent to:
    # executor.submit(SetPosition1DEvent(position=100, device=z_stage), thread_name='device_setting_thread').await_execution()
    # but the execution thread is the main thread

    # implicit
    # start capture first; we use await execution in order to make sure that the camera has finished acquisition
    executor.submit(SetPosition1DEvent(position=100, device=z_stage), thread_name='device_setting_thread')

    executor.shutdown()
    terminate_core_instances()
except Exception as e:
    print(f"An error occurred: {e}")
    terminate_core_instances()