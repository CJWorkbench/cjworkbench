#!/usr/bin/env python

from setuptools import setup

setup(
    name="upload",
    version="0.0.1",
    description="Upload CSV, Excel or JSON files from your computer",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/upload",
    packages=[""],
    py_modules=["upload"],
    install_requires=["cjwparse~=0.0.2", "cjwmodule~=1.4.2"],
    extras_require={"tests": ["pytest~=5.3.0"]},
)
