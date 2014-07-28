from __future__ import print_function
from setuptools import setup, find_packages

import io
import codecs
import os
import sys


here = os.path.abspath(os.path.dirname(__file__))

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.md')


setup(
    name='shipwright',
    version="0.0.1",
    url='http://github.com/6si/shipwright/',
    license='Apache Software License',
    author='Scott Robertson',
    tests_require=['nose'],
    install_requires=[
        'docopt',
        'zipper',
        'docker-py',
        'GitPython',

    ],
    author_email='scott@6sense.com',
    description='Multi docker image build management',
    long_description=long_description,
    packages=find_packages(),
    include_package_data=True,
    platforms='any',

    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    extras_require={
        'testing': ['nose'],
    },
    entry_points={
        'console_scripts': [
            'shipwright = shipwright.cli:main',
        ]
    }

)