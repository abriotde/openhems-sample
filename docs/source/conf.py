"""
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
"""
import sys
from pathlib import Path
PATH = str(Path(__file__).resolve().parents[2]/"src")
sys.path.insert(0, PATH)
sys.path.insert(0, PATH+"/openhems")

# pylint: disable=invalid-name, redefined-builtin
project = 'OpenHEMS'
copyright = 'GPLv3'
author = 'Albéric de la Crochais'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

intersphinx_disabled_domains = ['std']
templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []

# -- Options for EPUB output
epub_show_urls = 'footnote'
