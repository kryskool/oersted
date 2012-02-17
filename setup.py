import sys
sys.path.append('.')

import client

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

setup(name='oersted',
      version=client.__version__,
      author='PCSol',
      author_email='info@pcsol.be',
      url='http://www.pcsol.be',
      license='GPL-3',
      package_dir={'oersted': 'client'},
      description='Module to access OpenERP objects pythonically',
      long_description=open('README.rst').read(),
      classifiers=[
         'Development Status :: 5 - Production/Stable',
         'Environment :: Plugins',
         'Intended Audience :: Developers',
         'Intended Audience :: Financial and Insurance Industry',
         'Intended Audience :: Information Technology',
         'License :: OSI Approved :: GNU General Public License (GPL)',
         'Operating System :: OS Independent',
         'Programming Language :: Python',
         'Topic :: Office/Business',
      ],
      packages=['oersted'],
      install_requires=['lxml'],
     )

