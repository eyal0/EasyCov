#!/usr/bin/env python2
"""Setup and install EasyCov."""

from setuptools import setup, find_packages

setup(
    name='EasyCov',
    version='1.0',
    packages=find_packages(exclude=["tests",]),
    license='MIT',
    long_description=open('README.md').read(),
    install_requires=['lcovparse', 'unidiff'],
)
