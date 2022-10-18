# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('NanoCETPy/__init__.py', 'r') as f:
    version_line = f.readline()

version = version_line.split('=')[1].strip().replace("'", "")

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='nanocetpy',
    version=version,
    description='NanoCET Control and Analysis Software',
    packages=find_packages(),
    url='https://github.com/Dispertech/NanoCETPy',
    license='GPLv3',
    author='Dispertech and Contributors',
    author_email='info@dispertech.com',
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Development Status :: 4 - Beta',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
    ],
    include_package_data=True,
    package_data={'NanoCETPy':
        ['resources/*',]},
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "nanocet=NanoCETPy.__main__:main"
        ]
    },
    install_requires=[
    'numpy',
    'pyqtgraph',
    'scipy',
    'pyyaml',
    'experimentor',
    'scikit-image',
    'h5py',
    'pyzmq',
    'pypylon',
    'pyvisa',
    'pyserial',
    'pyqt5',
        ],
)
