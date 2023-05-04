#!/usr/bin/env python

from setuptools import setup

setup(name='Minipix',
    description='Python server for Lima camera Minipix',
    url='https://gitlab.esrf.fr/limagroup/Lima-camera-minipix',
    packages=['Minipix'],
    package_dir={'Minipix': 'src/Minipix'},

    # For compatibility with older pip
    use_scm_version=True,
    setup_requires=["setuptools_scm"],      
)
