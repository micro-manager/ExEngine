.. _micro-manager_backend:

##################################################################
Micro-Manager Backend
##################################################################

The Micro-Manager Device backend provides access to Micro-Manager devices, such as cameras and stages,
for use with the ExEngine.

Installation
------------

1. Install ExEngine, including the `micromanager` backends:

    .. code-block:: bash

        pip install "exengine[micromanager]"


2. Install Micro-Manager, either by downloding a nightly build from the `Micro-Manager website <https://micro-manager.org/wiki/Micro-Manager_Nightly_Builds>`_, or through python by typing:

    .. code-block:: python

        from mmpycorex import download_and_install_mm
        download_and_install_mm()


3. Configure your devices:

   After installation, you need to open Micro-Manager and create a configuration file for your devices. This process involves setting up and saving the hardware configuration for your specific microscope setup.

   For detailed instructions on creating a Micro-Manager configuration file, please refer to the `Micro-Manager Configuration Guide <https://micro-manager.org/Micro-Manager_Configuration_Guide>`_.

4. Launch Micro-Manager pointing to the instance you installed and load the config file you made:

   .. code-block:: python

      from mmpycorex import create_core_instance

      create_core_instance(mm_app_path='/path/to/micro-manager', mm_config_path='name_of_config.cfg')

   For testing purposes, if you call ``create_core_instance()`` with no arguments it will default to the default installation path of ``download_and_install_mm()`` and the Micro-Manager demo configuration file.


5. Verify the setup:

   .. code-block:: python

      from mmpycorex import Core

      core = Core()

      print(core.get_loaded_devices())

   This should print a list of all devices loaded from your configuration file.




Running ExEngine with Micro-Manager
-----------------------------------

This section shows how to use ExEngine with the Micro-Manager backend. Data is stored in RAM using,
the NDstorage, the backend for which must be installed with:

.. code-block:: bash

    pip install "exengine[ndstorage]"

First, start by launching Micro-Manager and getting access to the loaded devices

.. code-block:: python

   # Micro-Manager backend-specific functions
   from mmpycorex import create_core_instance, download_and_install_mm, terminate_core_instances

   from exengine import ExecutionEngine
   from exengine.data import DataCoordinates, DataHandler
   from exengine.backends.micromanager import MicroManagerCamera, MicroManagerSingleAxisStage
   from exengine.storage_backends.ndtiff_and_ndram import NDRAMStorage
   from exengine.events.detector_events import StartCapture, ReadoutData

   # Start Micro-Manager core instance with Demo config
   create_core_instance()
   executor = ExecutionEngine()

   # Get access to the micro-manager devices
   camera = MicroManagerCamera()
   z_stage = MicroManagerSingleAxisStage()

Example 1: Use the ExEngine to Acquire a Timelapse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Capture 100 images on the camera
   num_images = 100
   data_handler = DataHandler(storage=NDRAMStorage())
   start_capture_event = StartCapture(num_blocks=num_images, detector=camera)
   readout_images_event = ReadoutData(num_blocks=num_images, detector=camera,
                                      data_coordinates_iterator=[DataCoordinates(time=t) for t in range(num_images)],
                                      data_handler=data_handler)
   _ = executor.submit(start_capture_event)
   future = executor.submit(readout_images_event)
   
   # Block until all images have been read out
   future.await_execution()
   
   # Tell the data handler no more images are expected
   data_handler.finish()

Example 2: Create Series of Events with Multi-D Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from exengine.events.multi_d_events import multi_d_acquisition_events
   
   data_handler = DataHandler(storage=NDRAMStorage())
   events = multi_d_acquisition_events(z_start=0, z_end=10, z_step=2)
   futures = executor.submit(events)
   
   # Wait until the final event finished
   futures[-1].await_execution()
   
   # Tell the data handler no more images are expected
   data_handler.finish()

Shutdown
^^^^^^^^

.. code-block:: python

   # Shutdown the engine
   executor.shutdown()
   
   # Shutdown micro-manager
   terminate_core_instances()