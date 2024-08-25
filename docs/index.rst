############################################################################
ExEngine: an execution engine for microscope and laboratory hardware control
############################################################################


ExEngine is a pure Python toolkit for building microscopy and laboratory hardware control software. Unlike application-specific software that provide tightly integrated device access, control logic, and user interfaces,ExEngine is a flexible intermediary which enables mixing and matching of components from different frameworks within a single application. This approach allows researchers to build custom software that meets their specific needs, without being limited to vertically integrated software stacks.

Key Features:
==============

1. **Configurable Device Backends**: Supports hundreds of hardware devices, including those provided by Micro-Manager, as well as an extensible framework for easy integration of new devices and device types.

2. **Adaptable to Multiple Frontends**: Compatible with GUIs, scripts, networked automated labs, and AI-integrated microscopy

3. :ref:`Powerful Threading Capabilities <threading>`: Utilities for parallelization, asynchronous execution, and complex, multi-device workflows.

4. **Modality Agnosticism**: Adaptable to diverse microscopy techniques thanks to general purpose design.

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
   apis
