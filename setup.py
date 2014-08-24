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

exec(open('shipwright/version.py').read())

setup(
    name='shipwright',
    version=version,
    url='http://github.com/6si/shipwright/',
    license='Apache Software License',
    author='Scott Robertson',
    tests_require=['nose'],
    install_requires=[
        'docopt',
        'zipper',
        'docker-py>=0.4.1-dev',
        'GitPython==0.3.2.RC1',

    ],
    dependency_links = [
        # we need the version of docker-py that respectst the exclude directive
        # switch this to the appropriate docker-py version when something greater than
        # 0.4.1 is released.
        'git+https://github.com/docker/docker-py.git@c76fd8d91481d33cee6fcfaa61025c12caa95b98#egg=docker-py-0.4.1-dev'
    ],
    author_email='scott@6sense.com',
    description='Multi docker image build management',
    long_description=long_description,
    packages=find_packages(),
    include_package_data=True,
    platforms='any',

    classifiers = [
        'Programming Language :: Python :: 2.7',
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