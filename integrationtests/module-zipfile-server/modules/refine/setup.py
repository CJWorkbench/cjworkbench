#!/usr/bin/env python

from setuptools import setup

setup(
    name="refine",
    version="0.0.1",
    description="Clean inconsistencies and typos across values in seconds using algorithms, or standardize values manually",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/refine",
    packages=[""],
    py_modules=["refine"],
    install_requires=["pandas==0.25.0"],
)
