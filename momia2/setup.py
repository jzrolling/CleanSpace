# Import necessary modules
from setuptools import setup, find_packages

# Define package name, version, and the author who doesn't know a thing about coding
name = 'momia2'
version = '0.0.2.dev5'
author = 'jz-rolling'
author_emails = ['juzhu@hsph.harvard.edu', 'zhujh@im.ac.cn']

# Define package description
description = 'Mycobacteria-optimized microscopy image analysis version 2 (sort of)'

# Load README content
with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

# Define package requirements
requirements = [
    'numpy==1.25.2',
    'trackpy==0.6.1',
    'pandas==2.1.1',
    'scikit-image==0.21.0',
    'scikit-learn==1.3.1',
    'scipy==1.11.3',
    'matplotlib>=3.7',
    'networkx==3.1',
    'numba==0.58.0',
    'tifffile==2023.9.26',
    'nd2reader==3.3.0',
    'networkx==3.1',
    'seaborn==0.13.0',
    'opencv-python==4.8.1.78',
    'Pillow==10.0.1',
    'PyWavelets==1.4.1',
    'PyYAML==6.0.1',
    'read-roi==1.6.0',
    'tqdm==4.66.1',
]

# Define package classifiers
classifiers = [
    'License :: OSI Approved :: MIT License',
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    'Operating System :: OS Independent'
]

# Define package setup
setup(
    name=name,
    version=version,
    author=author,
    author_email=', '.join(author_emails),
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    classifiers=classifiers,
    packages = find_packages(),
    python_requires = ">=3.8"
)