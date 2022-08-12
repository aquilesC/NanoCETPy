Getting Started 
===============

Requirements
-------------

All requirements of the NanoCET software can be installed using this :download:`environment file </environment.yml>`, using conda:

.. code-block:: console

    conda env create -f environment.yml

Additionally it requires the `experimentor <https://github.com/aquilesC/experimentor/>`_ and `DisperPy <https://github.com/aquilesC/DisperPy/>`_ packages to be installed.
This can be done by cloning them and then installing them by running

.. code-block:: console

    pip install -e 

in the local repository directory


How to use exisiting scripts
-----------------------------

To use existing modules, e.g. the sequential version of the software covering the whole NanoCET workflow, simply run 

.. code-block:: console

    python start_sequential.py

or any other starting script in the root directory. Some starting scripts can be run with a command line argument like

.. code-block:: console

    python start_sequential.py demo 

which runs the sequential software in a demo mode not requiring any connected devices.



