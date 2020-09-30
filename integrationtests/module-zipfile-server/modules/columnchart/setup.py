#!/usr/bin/env python

from setuptools import setup

setup(
    name="columnchart",
    version="0.0.1",
    description="Present a column chart from numeric data",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/histogram",
    packages=[""],
    py_modules=["columnchart"],
    install_requires=["pandas==0.25.0", "cjwmodule>=1.3.0"],
)
