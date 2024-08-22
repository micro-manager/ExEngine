.. _installation:

Installation and Setup
======================

ExEngine was design to support multiple device and data storage backends, either independently or in combination. Each backend has some adapter code that lives within the Exengine package, and (optionally) other dependencies that need to be installed separately.

To install ExEngine with all available backend adapters, use pip:

.. code-block:: bash

   pip install "exengine[all]"

Note that even if you install all backends, you will still may need to install additional dependencies for some backends.

Refer to :ref:`backends` for more information on additional setup needed for other Device and DataStorage backends.

If you you only want to install specific backends, you can use:

.. code-block:: bash

   pip install "exengine[backend_name1, backend_name2]"

