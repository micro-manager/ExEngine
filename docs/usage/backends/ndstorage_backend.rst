.. _ndstorage_backend:

##################################################################
NDTiff and RAM backend
##################################################################

`NDTiff <https://github.com/micro-manager/NDStorage>`_ is a high-performance indexed Tiff format used to save image data in Micro-Manager. NDRAM is a light-weight in-memory storage class. Both implementations provide the same API for in-memory (NDRAMStorage) or file-based (NDTiffStorage) storage.

To install this backend:

.. code-block:: bash

    pip install exengine[ndstorage]

No further setup is required.


Usage
``````
.. code-block:: python

    from exengine.storage_backends.ndtiff_and_ndram import NDRAMStorage, NDTiffStorage
    from exengine.kernel.data_coords import DataCoordinates
    import numpy as np

    # Choose storage type
    storage = NDRAMStorage()  # In-memory
    # OR
    storage = NDTiffStorage(directory="/path/to/save")  # File-based

    # Store data
    coords = DataCoordinates(time=1, channel="DAPI", z=0)
    data = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    metadata = {"exposure": 100}
    storage.put(coords, data, metadata)

    # Retrieve data
    retrieved_data = storage.get_data(coords)
    retrieved_metadata = storage.get_metadata(coords)

    # Check existence
    if coords in storage:
        print("Data exists")

    # Finalize and close
    storage.finish()
    storage.close()

