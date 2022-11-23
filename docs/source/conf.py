# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import sphinx_rtd_theme

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
    "sphinx.ext.napoleon",
    ]
autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = ['_build', '_templates']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_theme_options = {"logo_only": True}
html_favicon = "favicon.ico"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']
# Display todos by setting to True
todo_include_todos = True

autoapi_type = 'python'
autoapi_dirs = ['../../NanoCETPy']
autoapi_options = ['members', 'undoc-members', 'show-inheritance', 'show-module-summary', 'special-members',
                   'imported-members']

favicons = [{
    "href": "https://secure.example.com/favicon/favicon-32x32.png",
    },
    ]