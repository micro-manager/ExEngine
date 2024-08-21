.. _data:


=======
Data
=======

ExEngine provides a flexible system for handling acquired data, including mechanisms for identifying, processing, and storing data throughout the experimental workflow.

DataCoordinates
---------------

In microscopy and other multi-dimensional experiments, data often needs to be associated with its position in various dimensions. The ``DataCoordinates`` class is used in ExEngine to represent these positions, providing a flexible way to organize data.

Concept
^^^^^^^
``DataCoordinates`` can be thought of as a label for each piece of data in an experiment. For instance, in a time-lapse, multi-channel Z-stack experiment:

- A full 3D stack might be identified as ``(time=2, channel='GFP')``
- A single 2D image within that stack could be represented as ``(time=2, channel='GFP', z=10)``
- A specific pixel in that image might be denoted by ``(time=2, channel='GFP', z=10, x=512, y=512)``

Key Features
^^^^^^^^^^^^
1. **Flexible Axes**: Arbitrary axis names are supported, with convenience methods provided for common ones like 'time', 'channel', and 'z'.
2. **Mixed Value Types**: Coordinate values can be either integers (e.g., for time points) or strings (e.g., for channel names).
3. **Dual Access Methods**: Values can be accessed both as attributes (e.g., coords.time) and as dictionary items (e.g., coords['time'])

Usage Example
^^^^^^^^^^^^^

.. code-block:: python

    from exengine.data import DataCoordinates

    # A DataCoordinates object is created
    coords = DataCoordinates(time=3, channel="DAPI", z=5)

    # Values are accessed
    print(coords.time)       # Output: 3
    print(coords['channel']) # Output: DAPI

    # A new dimension is added
    coords.position = 2

    # It is used as a dictionary
    coord_dict = dict(coords)
    print(coord_dict)  # Output: {'time': 3, 'channel': 'DAPI', 'z': 5, 'position': 2}



.. _data_coordinates_iterator:

DataCoordinatesIterator
-----------------------

The ``DataCoordinatesIterator`` class is used to iterate over a sequence of ``DataCoordinates`` objects. It is particularly useful for defining the expected data output of an acquisition event or for iterating over a dataset.

Key features:

- Can be created from a ``list`` or ``generator`` of ``DataCoordinates`` objects or valid ``dicts``
- Both finite and infinite sequences are supported
- Methods are provided to check if specific coordinates might be produced

Generators can be utilized to create ``DataCoordinatesIterator`` instances efficiently, since the individual ``DataCoordinates`` objects are not created until needed. This essential when the total number of coordinates is unknown or very large.

Example usage:

.. code-block:: python

    from exengine.data import DataCoordinatesIterator
    import itertools

    # A finite iterator is created from a list of dictionaries
    finite_iter = DataCoordinatesIterator.create([
        {'time': 0, 'channel': 'DAPI'},
        {'time': 1, 'channel': 'DAPI'},
        {'time': 2, 'channel': 'DAPI'}
    ])

    # An infinite iterator is created using a generator function
    def infinite_coords():
        for i in itertools.count():
            yield {'time': i}

    infinite_iter = DataCoordinatesIterator.create(infinite_coords())

DataStorage
------------

ExEngine uses a flexible storage API supporting various backends for persistent data storage on disk, in memory, or over networks.

Like the ``Device`` API, different storage systems are implemented as different backends. Different storage backends can be installed as needed. As described in the :ref:`installation` section, using a particular storage backend requires installing the corresponding module. For example, to save data in the NDTiff format, ExEngine must be installed using ``pip install exengine[all]`` or ``pip install exengine[ndstorage]``.

Storage backends, like ``Device`` backends, can be installed individually. As outlined in :ref:`installation`, specific backends require their corresponding modules. For instance, NDTiff storage requires installation via ``pip install exengine[ndstorage]``. Alternatively all storage (and device) backends can be installed via ``pip install exengine[all]``.

For implementing new storage backends, refer to the :ref:`add_storage` section.


.. _data_handler:

DataHandler
-----------

The ``DataHandler`` acts as a bridge between ``DataProducing`` events and ``DataStorage`` backends in ExEngine. It efficiently manages the flow of data, providing a thread-safe interface for saving, retrieving, and (optionally) processing data. By serving as an intermediary, the ``DataHandler`` ensures efficient data access throughout the experimental pipeline.

The example below demonstrates how the ``DataHandler`` is initialized with a storage backend and used with ``DataProducing`` ``ExecutorEvents``. It also shows how data can be retrieved, whether from memory or storage, using the ``get`` method.

.. code-block:: python

    from exengine.data import DataHandler
    from exengine.storage import SomeDataStorageImplementation

    # Initialize DataHandler with a storage backend
    storage = SomeDataStorageImplementation()
    data_handler = DataHandler(storage)

    data_producing_event = SomeDataProducingEvent(data_handler=data_handler)

    # Use with a DataProducing event
    engine.submit(data_producing_event)

    # Retrieve data (from memory or storage as needed)
    data, metadata = data_handler.get(coords, return_data=True, return_metadata=True)






Data processor
---------------

A data processor function allows for optional data processing before storage, useful for tasks like image correction, feature extraction, or data compression. It operates on a separate thread and can be attached to a ``DataHandler``.

A simple processing function might look like:

.. code-block:: python

    def process_function(data_coords, data, metadata):
        # Modify data or metadata
        data[:100, :100] = 0  # Set top-left 100x100 pixels to 0
        metadata['new_key'] = 'new_value'
        return data_coords, data, metadata

The processing function can return:

1. A tuple of (coordinates, data, metadata) for a single processed image
2. A list of tuples for multiple output images
3. None to discard the data (or to accumulate it for a later call of the processor)

Example:

.. code-block:: python

    # Return multiple images
    def multi_output_process(coords, data, metadata):
        data2 = np.array(data, copy=True)
        metadata2 = metadata.copy()
        metadata2['Channel'] = 'New_Channel'
        return [(coords, data, metadata), (coords, data2, metadata2)]

    # Process multiple images at once
    def batch_process(coords, data, metadata):
        if not hasattr(batch_process, "images"):
            batch_process.images = []
        batch_process.images.append(data)
        if len(batch_process.images) == 10:  # Process every 10 images
            combined = np.stack(batch_process.images, axis=0)
            # Process combined data
            batch_process.images = []
        return coords, data, metadata

To use processor functions, attach them to the ``DataHandler``:

.. code-block:: python

    processor = DataProcessor(process_function)
    data_handler = DataHandler(storage, process_fn=processor)




