#!/usr/bin/env python

from setuptools import setup

setup(
    name="formatnumbers",
    version="0.0.1",
    description="Change the way numbers are displayed in columns, leaving data intact",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/formatnumbers",
    packages=[""],
    py_modules=["formatnumbers"],
    install_requires=["pandas==0.25.0"],
)
