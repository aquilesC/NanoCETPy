"""
This module contains all classes to be used for the sequential operation of the NanoCET device by a customer.

For this reason the GUI components lead through the experimental workflow in a sequential fashion,
only ever displaying or giving access to a subset of the experiment.

While :class:`models.experiment.MainSetup` models all the intended functionality of one experiment, 
the sequence is actually imposed by the GUI, defined in :py:module:`views.sequential_window` 
"""