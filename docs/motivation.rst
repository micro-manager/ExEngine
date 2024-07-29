.. _motivation:

###########
Motivation
###########

Challenges in Modern Microscopy
===============================

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


