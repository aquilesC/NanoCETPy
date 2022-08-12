Module Structure
================

Every *module* - pertaining to a mode of operation of the NanoCET - has the following structure (the controllers/drivers are all assumed to be included in the experimentor or DisperPy packages):

.. code::

    .
    |---start_<module>.py
    |---config.yml
    |---<module>
        |---models
        |---views

The starting script should import a window class from the views module and an experiment class from the models module to control the device in a desired fashion and display input options and output.
It should thus contain at least the following lines:

.. code-block:: python

    >>> experiment = Experiment()
    >>> experiment.load_configuration('config.yml', yaml.UnsafeLoader)
    >>> # optional: experiment.initialize()
    >>> app = QApplication([])
    >>> window = Window(experiment=experiment)
    >>> window.show()
    >>> app.exec()
    >>> # optional: experiment.finalize()

where the initialization and finalization of the experiment can also be called from the window class depending on the logic of the intended application


Model components
-----------------

*Experiment*
    At least one file titled ``experiment.py`` or else, containing one or more classes constituting an experiment (a mode to use the NanoCET device).

*Further models* 
    It is often useful to modify base device models from the experimentor or DisperPy package to fit the use of your intended experiment.



View components
----------------

*Window*
    At least one file titled ``window.py`` or else, containing one or more classes constituting a GUI window.

*.ui-files*
    Qt is used for the GUI components in this project. In Qt designer, easily started using 

    .. code-block:: console

        designer

    one can layout windows and widgets and safe them as .ui-Files to be imported in the window class ``__init__()`` like so:

    .. code-block:: python

        >>> uic.loadUi(os.path.join(BASE_DIR_VIEW, '<Some_name>.ui'), self)
        >>> #BASE_DIR_VIEW being the absolute path of the window file 


Configuration
-------------

The ``config.yml`` file is intended to hold any information/parameters describing the experiment. 
It is read by the experiment and essentially used as dictionary.
Its precise structure is linked to with which keys certain information is accessed.
Generally it contains the following information:

* Info about the user like name, directory for saving data and related information
* Parameters for the GUI for presentation of data like refreshing time.
* Information about the identity and configuration parameters of connected component devices like the cameras and Arduino.
* Some default settings like the acquisition parameters during alignment. 


