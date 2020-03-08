#!/usr/bin/env python

from setuptools import setup

setup(
    name="loadurl",
    version="0.0.1",
    description="Download CSV, Excel or JSON files from Web servers",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/loadurl",
    packages=[""],
    py_modules=["loadurl"],
    install_requires=["cjwparse~=0.0.2", "cjwmodule~=1.4.2", "cjwparquet~=1.0.2"],
    extras_require={"tests": ["pytest~=5.3.0"]},
)
