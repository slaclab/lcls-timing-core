#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Sphinx configuration for the lcls-timing-core documentation."""

import subprocess

project = 'lcls-timing-core'
author = 'SLAC National Accelerator Laboratory'
copyright = '2026, SLAC National Accelerator Laboratory'

try:
    release = subprocess.check_output(
        ['git', 'describe', '--tags', '--abbrev=0'],
        stderr=subprocess.DEVNULL,
    ).decode().strip()
except Exception:
    release = 'dev'
version = release

extensions = ['sphinx.ext.extlinks', 'sphinx_copybutton']

extlinks = {
    'repo': ('https://github.com/slaclab/lcls-timing-core/blob/main/%s', '%s'),
    'issue': ('https://github.com/slaclab/lcls-timing-core/issues/%s', '#%s'),
}

templates_path = ['_templates']
exclude_patterns = ['_build', '_data', '_generated', 'Thumbs.db', '.DS_Store']
source_suffix = '.rst'
master_doc = 'index'
language = 'en'

html_theme = 'sphinx_rtd_theme'
html_theme_options = {'titles_only': True, 'navigation_depth': -1}
html_title = 'lcls-timing-core'
html_baseurl = 'https://slaclab.github.io/lcls-timing-core/'
html_static_path = ['_static']
