from __future__ import absolute_import, print_function

import io
import os

from setuptools import find_packages, setup


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8'),
    ) as fp:
        return fp.read()


readme = open('README.rst').read()
history = open('CHANGES.rst').read().replace('.. :changelog:', '')


setup(
    name='shipwright',
    version='0.9.0-alpha',
    url='https://github.com/6si/shipwright/',
    license='Apache Software License',
    author='Scott Robertson',
    tests_require=['nose'],
    install_requires=[
        'docker>=2.0.1, <3.0.0',
        'GitPython>=2.0.5, <3.0.0',
    ],
    extras_require={
        'registry': ['docker-registry-client>=0.5.1, <0.6.0'],
    },
    author_email='scott@6sense.com',
    description=(
        'The right way to build, tag and ship shared Docker images.'
    ),
    long_description=readme + '\n\n' + history,
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
        'Programming Language :: Python :: 3.6',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    entry_points={
        'console_scripts': [
            'shipwright = shipwright._lib.cli:main',
        ],
    },
)
