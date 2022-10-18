"""
    The module containing all GUI elements of the sequential software.
    
    The main part is the sequential window module containing the PyQT classes used in the GUI.
    Those are a main window and several widgets that are added/removed from it.

    The layout of the used PyQT widgets is created in designer and set to the widget, like so:
    >>> uic.loadUi(os.path.join(BASE_DIR_VIEW, '<Some_name>.ui'), self)
    >>> #BASE_DIR_VIEW being the absolute path of the window file 
"""
import pathlib


BASE_DIR_VIEW = pathlib.Path(__file__).parent