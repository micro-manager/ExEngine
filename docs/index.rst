#####################################################
ExEngine: An execution engine for microscope control
#####################################################


ExEngine is a versatile toolkit for microscopy hardware control and data acquisition, bridging low-level hardware control with high-level experiment design and user interfaces. It empowers researchers to create sophisticated microscopy experiments without getting bogged down in details, while scaling to support advanced automated and AI-driven workflows across various microscopy applications.

Key Features:
==============

1. **Configurable Device Backends**: Supports hundreds of hardware devices, including those provided by Micro-Manager, as well as an extensible framework for easy integration of new devices and device types.

2. **Adaptable to Multiple Frontends**: Compatible with GUIs, scripts, networked automated labs, and AI-integrated microscopy

3. **Advanced Threading Capabilities**: Utilities for parallelization, asynchronous execution, and complex, multi-device workflows.

4. **Modality Agnostic**: Adaptable to diverse microscopy techniques thanks to general purpose design.

5. **Modular, Reusable Device Instructions**: Building blocks that can be combined to create complex workflows, in order to promote code reuse and simplify experiment design



.. raw:: html

    <div style="text-align: center; max-width: 100%;">
        <object type="image/svg+xml" data="_static/exengine_bigpicture.svg" style="width: 100%; height: auto;"></object>
        <p style="font-style: italic; font-size: 0.9em; color: #555;"><b></b></p>
    </div>



.. toctree::
   :maxdepth: 3
   :caption: Contents:

   design
   usage
   extending
