# -*- coding: utf-8 -*-
#
# scanpointgenerator documentation build configuration file

import os
import re
import sys


def get_version():
    """
    Extracts the version number from the version.py file.
    """
    VERSION_FILE = '../scanpointgenerator/version.py'
    mo = re.search(
        r'^__version__ = [\'"]([^\'"]*)[\'"]', open(VERSION_FILE, 'rt').read(), re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError(
            'Unable to find version string in {0}.'.format(VERSION_FILE))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
try:
    from pkg_resources import require
except:
    pass
else:
    require("matplotlib")
    require("scipy")
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'matplotlib.sphinxext.plot_directive'
]

napoleon_use_ivar = True

autoclass_content = "both"

autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'scanpointgenerator'
copyright = u'2015, Diamond Light Source'
author = u'Tom Cobb'

# The short X.Y version.
version = get_version()
# The full version, including alpha/beta/rc tags.
release = version

exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# intersphinx_mapping = {
#    'python': ('http://python.readthedocs.org/en/v2.7.2/', None),
#}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# on_rtd is whether we are on readthedocs.org
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'scanpointgeneratordoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'scanpointgenerator.tex', u'scanpointgenerator Documentation',
     u'Tom Cobb', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'scanpointgenerator', u'scanpointgenerator Documentation',
     [u'Tom Cobb'], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'scanpointgenerator', u'scanpointgenerator Documentation',
     u'Tom Cobb', 'scanpointgenerator', 'A short description',
     'Miscellaneous'),
]
