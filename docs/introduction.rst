.. _introduction:

##################
Introduction
##################


ExEngine is a general-purpose library for microscopy hardware control and data acquisition. It explicitly separates the specification of instructions from their execution, meaning it is not inherently specialized for any one type of microscopy and can be readily adapted to a variety of contexts. It is designed to balance between simplicity and expressiveness, enabling researchers to create sophisticated microscopy experiments without getting bogged down in low-level details.

.. TODO: this first paragraph can be improved


.. Key benefits:	
.. 	Larger device libraries
.. 	Existing libraries often designed for scripting/GUI. Extending to workflow manager requires custom
.. 	Reuse of code
.. Designed to enable convenience of development but scales to AI based workflows




Motivation
================


.. raw:: html

    <div style="text-align: center; max-width: 100%;">
        <object type="image/svg+xml" data="_static/exengine_bigpicture.svg" style="width: 100%; height: auto;"></object>
        <p style="font-style: italic; font-size: 0.9em; color: #555;"><b>The benefits of ExEngine</b></p>
    </div>



Advanced microscopes require sophisticated software to function effectively. As microscopy techniques evolve, so do the challenges of control software:

1. **Scalability**: 
   The evolution from proof-of-concept to production systems in microscopy creates a dynamic set of software requirements. In the early stages, prototype systems demand low-level hardware control and high customizability. As systems mature, the focus shifts: the hardware control layer needs to stabilize, while flexibility becomes crucial for higher-level experimental design.

   This transition often results in significant software discontinuities. A common pattern illustrates this challenge: many novel microscopy systems are initially developed using LabVIEW for its rapid prototyping capabilities. However, as these systems advance towards production, teams frequently find themselves completely rewriting the control software, often transitioning to platforms like Micro-Manager. 


2. **AI-driven Smart Microscopy**: 
   Most current user interfaces for microscopes are designed for human operators, AI shows promise in automating complex workflows. However, we lack standardized methods to accurately capture and describe routine and complex experimental workflows, hindering their potential for automation.

3. **Ecosystem Lock-in**: 
   Current solutions often create vertically integrated control packages, tying users to specific ecosystems. These typically include:
   
   a. A device control layer
   b. A layer for controlling and synchronizing multiple devices
   c. A graphical user interface
   
   While device layers may be reusable, the acquisition engine layer is often bespoke and hard coded for specific device libraries, limiting interoperability.




Design Philosophy
"""""""""""""""""

- **Backend-agnosticism**: While Micro-Manager is supported, ExEngine can seamlessly integrate with any (or multiple) hardware control backends, providing equal functionality and performance across different systems.
- **Non-obtrusiveness**: Minimal assumptions about hardware devices, allowing new device support to be added with maximum flexibility and minimal effort.
- **Versatility**: Multiple sets of independently usable features and levels of integration possibilities.
- **Extensibility**: Hardware setup is abstracted away from execution capabilities, allowing new capabilities with entirely different functionality to be added.


Benefits of ExEngine
""""""""""""""""""""

1. **Broad and extensible hardware support** Supports the full suite of hardware in micro-manager, but is not designed specially for them. More backends can allow more devices to be used, and used in combination

2. **Parallelization and thread safety** You need parallelism with high performance software, but this often leads to hard to diagnose problems because devices that were designed with concurrency in mind get accessed from multiple places in the software, leading to problems. ExEngine can automatically handle this by rerouting calls to devices through a common pool of threads. Significantly, this happens automatically under the hood, adding little to no complexity to writing control code.

3. **Built for humans and AI**: Enables complete tracking of commands sent to hardware and data received, without complex additional code. This facilitates tracking and automation of microscopes using AI.
