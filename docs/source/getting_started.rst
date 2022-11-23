Getting Started 
===============

Requirements
-------------

All requirements of the NanoCET software can be installed using this :download:`environment file </environment.yml>`, using conda:

.. code-block:: console

    conda env create -f environment.yml

Additionally it requires the `experimentor <https://github.com/aquilesC/experimentor/>`_ package.
This can be done by cloning them and then installing them by running

.. code-block:: console

    pip install -e 

in the local repository directory


How to use exisiting scripts
-----------------------------

To start the NanoCET workflow, simply run

.. code-block:: console

    python start.py

Some starting scripts can be run with a command line argument like

.. code-block:: console

    python start_sequential.py demo 

which runs the software in a demo mode not requiring any connected devices.

If the NanoCETPy is installed (either from PyPI or from the cloned directory), it will create an entry point called ``nanocet`` that can be run from the command line to trigger the start script.

To start the experiment from the command line (or a Jupyter notebook) the following lines are all what is required:


.. code-block:: python

    >>> from NanoCETPy.models.experiment import MainSetup as Experiment
    >>> from NanoCETPy.views.sequential_window import SequentialMainWindow as Window
    >>> experiment = Experiment()
    >>> experiment.load_configuration('config.yml', yaml.UnsafeLoader)
    >>> experiment.initialize()
    >>> app = QApplication([])
    >>> window = Window(experiment=experiment)
    >>> window.show()
    >>> app.exec()
    >>> experiment.finalize() #<- Once you are ready


