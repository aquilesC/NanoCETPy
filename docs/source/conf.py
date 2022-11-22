# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath('../../NanoCETPy'))

import _version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'NanoCETPy'
copyright = 'Dispertech © 2022'
author = 'Dispertech Authors. See AUTHORS for more information'
release = _version.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
]
autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = ['_build', '_templates']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'classic'
html_static_path = ['_static']
# Display todos by setting to True
todo_include_todos = True

autoapi_type = 'python'
autoapi_dirs = ['../../NanoCETPy']
autoapi_options = ['members', 'undoc-members', 'show-inheritance', 'show-module-summary', 'special-members', 'imported-members']