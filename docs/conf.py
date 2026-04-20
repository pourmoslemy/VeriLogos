# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
project = 'VeriLogos'
copyright = '2025, Alireza Pourmoslemi'
author = 'Alireza Pourmoslemi'
version = '0.1.0'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'show_powered_by': False,
}
html_context = {
    'extra_footer': '<p>Created by <a href="mailto:apmath99@gmail.com">Alireza Pourmoslemi</a></p>',
}

# -- Extension configuration -------------------------------------------------

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
}

# Type hint configuration
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Class documentation
autoclass_content = "both"
autodoc_class_signature = "separated"

# Member ordering
autodoc_member_order = "bysource"

# Mock imports for modules not available during doc build
autodoc_mock_imports = ['numpy', 'aiohttp', 'websockets', 'ccxt']

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
}

# MyST parser configuration
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
]
