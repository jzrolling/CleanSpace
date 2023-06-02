# Import necessary modules
from setuptools import setup, find_packages

# Define package name, version, and the author who doesn't know a thing about coding
name = 'momia2'
version = '0.1'
author = 'jz-rolling'

# Define package description
description = 'Mycobacteria-optimized microscopy image analysis version 2 (sort of)'

# Load README content
with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

# Define package requirements
requirements = [
    'numpy>=1.22',
    'pandas>=1.5',
    'trackpy>=0.6',
    'scikit-image>=0.20.0',
    'matplotlib>=3.7',
    'networkx==3.0',
    'numba==0.56.4',
    'tifffile==2023.3.21',
    'nd2reader==3.3.0',
]

# Define package classifiers
classifiers = [
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Operating System :: OS Independent',
]

# Define package setup
setup(
    name=name,
    version=version,
    author=author,
    author_email='juzhu@hsph.harvard.edu',
    description=description,
    long_description=long_description,
    install_requires=requirements,
    classifiers=classifiers,
    packages = find_packages(),
    python_requires = ">=3.8"
)