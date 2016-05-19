from __future__ import absolute_import, print_function

import io
import os
import re

from setuptools import find_packages, setup


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8'),
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^version = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')

long_description = read('README.rst')

setup(
    name='dockhand',
    version=find_version('shipwright/version.py'),
    url='https://github.com/graingert/dockhand/',
    license='Apache Software License',
    author='Scott Robertson',
    tests_require=['nose'],
    install_requires=[
        'docopt',
        'zipper',
        'requests>=2.4.0',
        'docker-py>=1.6.0',
        'GitPython>=1.0.1, <2.0.0',
    ],
    author_email='scott@6sense.com',
    description=(
        'The right way to build, tag and ship shared Docker containers.'
    ),
    long_description=long_description,
    packages=find_packages(),
    include_package_data=True,
    platforms='any',

    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
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
        ],
    },
)
