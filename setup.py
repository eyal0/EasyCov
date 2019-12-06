from setuptools import setup

setup(
    name='EasyCov',
    version='1.0',
    packages=['easycov',],
    license='MIT',
    long_description=open('README.md').read(),
    install_requires=['lcovparse'],
)
