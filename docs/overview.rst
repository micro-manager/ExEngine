.. _overview:

##################
ExEngine Overview
##################

ExEngine is designed as a general-purpose acquisition engine layer, separating hardware control execution from its specification. 


ExEngine strikes a balance between simplicity and expressiveness, enabling researchers to create sophisticated microscopy experiments without getting bogged down in low-level details. It provides a foundation for building scalable, interoperable, and future-proof microscopy control systems.


Design Principles
"""""""""""""""""

- **Backend-agnosticism**: While Micro-Manager is supported, ExEngine can seamlessly integrate with any (or multiple) hardware control backends, providing equal functionality and performance across different systems.
- **Non-obtrusiveness**: Minimal assumptions about hardware devices, allowing new device support to be added with maximum flexibility and minimal effort.
- **Versatility**: Multiple sets of independently usable features and levels of integration possibilities.
- **Extensibility**: Hardware setup is abstracted away from execution capabilities, allowing new capabilities with entirely different functionality to be added.


Key features
""""""""""""

1. **Broad and extensible hardware support** Supports the full suite of hardware in micro-manager, but is not designed specially for them. More backends can allow more devices to be used, and used in combination

2. **Parallelization and thread safety** You need parallelism with high performance software, but this often leads to hard to diagnose problems because devices that were designed with concurrency in mind get accessed from multiple places in the software, leading to problems. ExEngine can automatically handle this by rerouting calls to devices through a common pool of threads. Significantly, this happens automatically under the hood, adding little to no complexity to writing control code.

3. **Built for humans and AI**: Enables complete tracking of commands sent to hardware and data received, without complex additional code. This facilitates tracking and automation of microscopes using AI.
