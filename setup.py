# -*- coding: utf-8 -*-

# Use distutils instead of setuptools
from distutils.core import setup

setup(name='oersted',
      version='1.3.0',
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

