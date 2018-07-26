#!/usr/bin/env python

from setuptools import setup

setup(
    name='histogram',
    version='0.0.1',
    description='Present a columnful of numbers as a histogram',
    author='Adam Hooper',
    author_email='adam@adamhooper.com',
    url='https://github.com/CJWorkbench/histogram',
    packages=[''],
    py_modules=['columnchart'],
    install_requires=['pandas==0.23.1']
)
