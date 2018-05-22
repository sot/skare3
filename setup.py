#!/usr/bin/env python
from setuptools import setup
from ska_conda import __version__
import glob

scripts = glob.glob("scripts/*")

url = 'https://github.com/sot/ska_conda/tarball/{}'.format(__version__)

setup(name='ska_conda',
      packages=['ska_conda'],
      version=__version__,
      description='Ska Conda package manager',
      author='John ZuHone',
      author_email='john.zuhone@cfa.harvard.edu',
      url='http://github.com/sot/ska_conda',
      download_url=url,
      scripts=scripts,
      install_requires=["gitpython","pyyaml"],
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.6'
      ],
      )
