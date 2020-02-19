#!/usr/bin/env python

from setuptools import setup

setup(
    name="converttexttonumber",
    version="0.0.1",
    description="Convert text columns to number columns",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/converttexttonumber",
    packages=[""],
    py_modules=["converttexttonumber"],
    install_requires=["pandas==0.25.0", "cjwmodule>=1.4.0"],
)
