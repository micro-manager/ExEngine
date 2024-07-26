 # Setup and examples for using the ExEngine with a micro-manager backend

 - clone the repository
 - install it, specifying which device and data storage backends
 	`pip install -e ".[micromanager, ndstorage]"`
 - install Micro-Manager

```python
from mmpycorex import download_and_install_mm 
download_and_install_mm()
```


## Running the ExEngine

```python
from mmpycorex import create_core_instance, download_and_install_mm, terminate_core_instances
from exengine.kernel.executor import ExecutionEngine
from exengine.kernel.data_coords import DataCoordinates
from exengine.kernel.ex_event_base import DataHandler
from exengine.backends.micromanager.mm_device_implementations import MicroManagerCamera, MicroManagerSingleAxisStage
from exengine.storage_backends.NDTiffandRAM import NDRAMStorage
from exengine.events.detector_events import StartCapture, ReadoutData


# Start Micro-Manager core instance with Demo config
create_core_instance()

executor = ExecutionEngine()


# get access to the micro-manager devices
camera = MicroManagerCamera()
z_stage = MicroManagerSingleAxisStage()

```


### Example 1: Use the exengine to acquire a timelapse

```python
# Capture 100 images on the camera
num_images = 100
data_handler = DataHandler(storage=NDRAMStorage())

start_capture_event = StartCapture(num_images=num_images, detector=camera)
readout_images_event = ReadoutData(num_images=num_images, detector=camera,
                                   data_coordinates_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                   data_handler=data_handler)

_ = executor.submit(start_capture_event)
future = executor.submit(readout_images_event)

# block until all images have been read out
future.await_execution()

# Tell the data handler no more images are expected
data_handler.finish()

```

### Example 2: create series of events with multi-d function
```python
from exengine.events.multi_d_events import multi_d_acquisition_events

data_handler = DataHandler(storage=NDRAMStorage())
events = multi_d_acquisition_events(z_start=0, z_end=10, z_step=2)

futures = executor.submit(events)
# wait until the final event finished
futures[-1].await_execution()

# Tell the data handler no more images are expected
data_handler.finish()
```


```python
# shutdown the engine
executor.shutdown()
# shutdown micro-manager
terminate_core_instances()
```
