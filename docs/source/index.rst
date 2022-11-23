.. NanoCETPy documentation master file, created by
   sphinx-quickstart on Wed Aug 10 16:45:49 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. title:: NanoCETPy: Instrument control software for high-accuracy nanoparticle size measurements

.. image:: _static/logo.png

NanoCETPy
=========

NanoCETPy is a Python program to control the instruments developed and built by [Dispertech](https://www.dispertech.com). The main focus is the auto-alignment of the laser to the hollow-core fiber, accepting parameters from the user, and saving data.

The program follows the **MVC** pattern strictly, separating the Models, Views, and Controllers into different modules. The controllers is where the custom drivers for the different components can be found, the models specify the usage logic, including how to save data, how to perform the alignment, etc. The view holds the user interface elements.

This documentation is intended for those users who want to dive deeper into how the [NanoCET](https://www.dispertech.com/products) is controlled, help with troubleshooting, or extending the functionality. Any issues with the code should be reported using the [issue tracker at Github](https://github.com/Dispertech/NanoCETPy/issues), or the [contact form](https://www.dispertech.com/contact).

General discussions about the usage of the software, potential improvements, etc. can be submitted to the [discussion forum hosted on Github](https://github.com/Dispertech/NanoCETPy/discussions).


Contents
--------
.. toctree::
   :maxdepth: 1
   :caption: Contents:

   getting_started
   todo
   NanoCETPy/index

