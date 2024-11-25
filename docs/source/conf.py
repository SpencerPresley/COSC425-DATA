# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "Academic Metrics"
copyright = "2024, Spencer Presley, Cole Barbes"
author = "Spencer Presley, Cole Barbes"
release = "0.1.0-beta"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.doctest",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# THIS IS THE DEFAULT THEME
# html_theme = 'alabaster'

# html_theme = 'sphinx_rtd_theme'
html_theme = "piccolo_theme"
html_static_path = ["_static"]

# Napoleon settings
napoleon_google_docstring = True
napoleon_include_private_with_doc = True
autodoc_member_order = "bysource"
