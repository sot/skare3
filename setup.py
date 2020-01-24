# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

# requirements:
#
setup(name='skare3',
      author='Javier Gonzalez',
      description='Tools for skare3 package management',
      author_email='javier.gonzalez@cfa.harvard.edu',
      packages=['skare3'],
      license=("New BSD/3-clause BSD License\nCopyright (c) 2020"
               " Smithsonian Astrophysical Observatory\nAll rights reserved."),
      download_url='http://pypi.python.org/pypi/skare3/',
      url='http://cxc.harvard.edu/mta/ASPECT/tool_doc/pydocs/skare3.html',
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      tests_require=['pytest'],
      cmdclass=cmdclass,
      entry_points = {'console_scripts':
                      ['skare3_dashboard=skare3.dashboard.dashboard:main',
                       'skare3_github_info=skare3.dashboard.ska_github_info:main']}
      )
