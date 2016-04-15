from itertools import takewhile
import os

from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = str.join('', takewhile(lambda l: not l.startswith('Installation'), f.readlines()[15:]))

setup(
    name = 'overloading',
    version = '0.5.0',
    description = 'Function overloading for Python 3',
    long_description = '\n' + readme,
    url = 'https://github.com/bintoro/overloading.py',
    author = 'Kalle Tuure',
    author_email = 'kalle@goodtimes.fi',
    license = 'MIT',
    py_modules = ['overloading'],
    install_requires = [],
    keywords = 'overload function method dispatch',
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License'
    ]
)
