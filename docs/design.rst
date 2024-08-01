.. _design:

#######
Design
#######

ExEngine is built around four key abstractions: Devices, Events, Futures, and Notifications.


* :ref:`Devices <devices>`: Hardware components that can be controlled, such as cameras, stages, or light sources.
* :ref:`Events <events>`: Encapsulated units of work that represent actions to be executed, ranging from simple actions like moving a stage or capturing an image to complex ones like running an autofocus routine.
* :ref:`Futures <futures>`: Objects that represent the result of asynchronous operations, allowing for management and retrieval of event outcomes.
* :ref:`Notifications <notifications>`: Asynchronous messages that provide real-time updates on system status and progress.


.. raw:: html

    <div style="text-align: center; max-width: 100%;">
        <object type="image/svg+xml" data="_static/exengine_arch.svg" style="width: 100%; height: auto;"></object>
        <p style="font-style: italic; font-size: 0.9em; color: #555;"><b>Overview of the main components of ExEngine:</b> Events are submitted to the Execution Engine, which handles their execution on one or more internal threads. Upon execution, events can control hardware devices and produce output data. Futures allow for the management and retrieval of the results of these asynchronous operations. Notifications are produced asynchronously, enabling user applications to monitor progress and system status updates in real-time.</p>
    </div>

