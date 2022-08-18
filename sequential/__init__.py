"""
This module contains all classes to be used for the sequential operation of the NanoCET device by a customer.

For this reason the GUI components lead through the experimental workflow in a sequential fashion,
only ever displaying or giving access to a subset of the experiment.

While :class:`models.experiment.MainSetup` models all the intended functionality of one experiment, 
the sequence is actually imposed by the GUI, defined in :py:module:`views.sequential_window` 

The intended sequence is as follows:

#. A connections checkpoint, runnning in a loop until both cameras and the Arduino are detected.
#. Entering the user data
#. Setting up the cartrigde by 

    * Placing it into the devices
    * Focusing the microscope camera on it using transmission from the top LED
    * Aligning the laser to couple it into the fiber core

#. Entering the experiment parameters
#. Observing the measurement (video and waterfall)
#. Removing the cartrigde once finished

.. todo:: A popup with a more extensive set of configuration parameters or even for steering the piezos to manually correct alignment would perhaps be useful.
"""