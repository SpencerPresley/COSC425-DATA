# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath("../../src/academic_metrics/"))

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
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "langchain": ("https://python.langchain.com/api_reference/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "pylatexenc": ("https://pylatexenc.readthedocs.io/en/latest/", None),
}

# Add extlinks config
extlinks = {
    "pypi": ("https://pypi.org/project/%s/", "%s"),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# THIS IS THE DEFAULT THEME
# html_theme = 'alabaster'

# html_theme = 'sphinx_rtd_theme'
# html_theme = "piccolo_theme"
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": "https://github.com/spencerpresley/COSC425-DATA",
    "navbar_start": ["navbar-logo"],
    "logo": {"text": "Academic Metrics"},
    "navbar_align": "left",
    # "navigation_with_keys": True,
    "navigation_depth": 1,
    "show_toc_level": 2,
    "show_nav_level": 1,
    "primary_sidebar_end": ["indices"],
}

html_sidebars = {
    "**": [
        "searchbox.html",
        "relations.html",
        "globaltoc.html",
        "sourcelink.html",
    ],
    "index": [],
}

# html_sidebars = {
#     "*.html": ["sidebar-nav-bs.html"]
# }

html_static_path = ["_static"]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# add_module_names = False
toc_object_entries_show_parents = "hide"

autodoc_member_order = "bysource"
