.. _add_storage:

###############################
Adding New Storage Backends
###############################

We welcome the addition of new storage backends to ExEngine! If you've created a storage backend that could benefit others, please consider opening a Pull Request.

This guide outlines the process of creating new data storage backends.

Code Organization and Packaging
===============================

When adding a new storage backend to ExEngine, follow this directory structure:

.. code-block:: text

    src/exengine/
    └── storage_backends/
        └── your_new_storage/
            ├── __init__.py
            ├── your_storage_implementation.py
            └── test/
                ├── __init__.py
                └── test_your_storage.py

Replace ``your_new_storage`` with an appropriate name for your storage backend.

You may also want to edit the ``__init__.py`` file in the ``your_new_storage`` directory to import the Class from your storage implementation file (see the NDStorage backend for an example of this).

Additional Dependencies
-----------------------

If your storage backend requires additional dependencies, add them to the ``pyproject.toml`` file:

1. Open the ``pyproject.toml`` file in the root directory of the project.
2. Add a new optional dependency group for your storage backend:

   .. code-block:: toml

      [project.optional-dependencies]
      your_new_storage = ["your_dependency1", "your_dependency2"]

3. Update the ``all`` group to include your new storage backend:

   .. code-block:: toml

      all = [
          "mmpycorex",
          "ndstorage",
          "your_dependency1",
          "your_dependency2"
      ]

4. Add it to the ``storage backends`` group:

   .. code-block:: toml

      # storage backends
      your_new_storage = ["your_dependency1", "your_dependency2"]

Implementing a New Storage Backend
==================================

All new storage backends should inherit from the ``DataStorage`` abstract base class. This ensures compatibility with the ExEngine framework.

The ``DataStorage`` abstract base class is defined in ``exengine/kernel/data_storage_base.py``. You can find the full definition and method requirements there.

Here's a basic structure for implementing a new storage backend:

.. code-block:: python

   from exengine.kernel.data_storage_base import DataStorage

   class YourNewStorage(DataStorage):
       def __init__(self):
           super().__init__()
           # Your storage-specific initialization code here

       # Implement the abstract methods from DataStorage
       # Refer to data_storage_base.py for the full list of methods to implement

When implementing your storage backend, make sure to override all abstract methods from the ``DataStorage`` base class. These methods define the interface that ExEngine expects from a storage backend.

Adding Tests
------------

1. Create a ``test_your_storage.py`` file in the ``test/`` directory of your storage backend.
2. Write pytest test cases for your storage backend functionality. For example:

   .. code-block:: python

      import pytest
      import numpy as np
      from exengine.storage_backends.your_new_storage import YourNewStorage

      def test_your_storage_initialization():
          storage = YourNewStorage()
          assert isinstance(storage, YourNewStorage)

      def test_put_and_get_data():
          storage = YourNewStorage()
          data = np.array([1, 2, 3])
          metadata = {"key": "value"}
          coordinates = {"time": 0, "channel": "DAPI"}

          storage.put(coordinates, data, metadata)

          assert coordinates in storage
          np.testing.assert_array_equal(storage.get_data(coordinates), data)
          assert storage.get_metadata(coordinates) == metadata

      # Add more test cases as needed

Running Tests
-------------

To run tests for your new storage backend:

1. Install the test dependencies. In the ExEngine root directory, run:

   .. code-block:: bash

      pip install -e ".[test,your_new_storage]"

2. Run pytest for your storage backend:

   .. code-block:: bash

      pytest -v src/exengine/storage_backends/your_new_storage/test

Adding Documentation
--------------------

1. Add documentation for your new storage backend in the ``docs/`` directory.
2. Create a new RST file, e.g., ``docs/usage/backends/your_new_storage.rst``, describing how to use your storage backend.
3. Update ``docs/usage/backends.rst`` to include your new storage backend documentation.

To build the documentation locally, you may need to install the required dependencies. In the ``exengine/docs`` directory, run:

.. code-block:: bash

   pip install -r requirements.txt

Then, to build, in the ``exengine/docs`` directory, run:

.. code-block:: bash

   make clean && make html

then open ``_build/html/index.html`` in a web browser to view the documentation.

