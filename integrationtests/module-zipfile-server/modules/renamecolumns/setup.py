#!/usr/bin/env python

from setuptools import setup

setup(
    name="renamecolumns",
    version="0.0.1",
    description="Edit column names",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/renamecolumns",
    packages=[""],
    py_modules=["renamecolumns"],
    install_requires=["pandas==0.25.0", "cjwmodule>=1.4.0"],
)
