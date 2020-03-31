#!/usr/bin/env python

from setuptools import setup

setup(
    name="pastecsv",
    version="0.0.1",
    description="Convert text to table",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/pastecsv",
    packages=[""],
    py_modules=["pastecsv"],
    install_requires=["cjwmodule~=1.4", "cjwparse~=0.0.3"],
    tests_require=["pytest~=5.3"],
    extras_require={"tests": ["pytest~=5.3"]},
)
