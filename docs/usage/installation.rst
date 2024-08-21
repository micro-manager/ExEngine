.. _installation:

Installation and Setup
======================

Basic Installation
------------------
To install ExEngine with all available backends, use pip:

.. code-block:: bash

   pip install "exengine[all]"

The ``[all]`` option installs ExEngine with all available device and storage backend dependencies.

Alternatively, if you only want to install specific backends, you can use:

.. code-block:: bash

   pip install "exengine[micromanager]"

This will install ExEngine with only the Micro-Manager device backend.


Backend-Specific Setup
----------------------
Some backends may require additional setup:

Micro-Manager
^^^^^^^^^^^^^
1. Install Micro-Manager:

   .. code-block:: python

      from mmpycorex import download_and_install_mm
      download_and_install_mm()

2. Configure your devices:
   
   After installation, you need to open Micro-Manager and create a configuration file for your devices. This process involves setting up and saving the hardware configuration for your specific microscope setup.

   For detailed instructions on creating a Micro-Manager configuration file, please refer to the `Micro-Manager Configuration Guide <https://micro-manager.org/Micro-Manager_Configuration_Guide>`_.

3. Launch Micro-Manager pointing to the instance you installed and load the config file you made:

   .. code-block:: python

      from mmpycorex import create_core_instance

      create_core_instance(mm_app_path='/path/to/micro-manager', mm_config_path='name_of_config.cfg')

   For testing purposes, if you call ``create_core_instance()`` with no arguments it will default to the default installation path of ``download_and_install_mm()`` and the Micro-Manager demo configuration file.


4. Verify the setup:

   .. code-block:: python

      from mmpycorex import Core

      core = Core()

      print(core.get_loaded_devices())

   This should print a list of all devices loaded from your configuration file.
