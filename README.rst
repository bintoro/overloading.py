==============
overloading.py
==============

.. rubric:: Function overloading for Python 3

.. image::  https://travis-ci.org/bintoro/overloading.py.svg?branch=master
   :target: https://travis-ci.org/bintoro/overloading.py
   :alt:    Build Status

.. image::  https://coveralls.io/repos/github/bintoro/overloading.py/badge.svg?branch=master
   :target: https://coveralls.io/github/bintoro/overloading.py
   :alt:    Coverage Status

|

``overloading`` is a module that provides function and method dispatching
based on the types and number of runtime arguments.

When an overloaded function is invoked, the dispatcher compares the supplied
arguments to available signatures and calls the implementation providing the
most accurate match:

.. code:: python

    @overload
    def biggest(items: Iterable[int]):
        return max(items)

    @overload
    def biggest(items: Iterable[str]):
        return max(items, key=len)

.. code:: python

    >>> biggest([2, 0, 15, 8, 7])
    15
    >>> biggest(['a', 'abc', 'bc'])
    'abc'


Features
========

* Function validation during registration and comprehensive resolution rules
  guarantee a well-defined outcome at invocation time.
* Supports the `typing`_ module introduced in Python 3.5.
* Supports optional parameters.
* Supports variadic signatures (``*args`` and ``**kwargs``).
* Supports class-/staticmethods.
* Evaluates both positional and keyword arguments.
* No dependencies beyond the standard library

.. _typing:   https://docs.python.org/3/library/typing.html


Documentation
=============

The full documentation is available at https://overloading.readthedocs.org/.


Installation
============

``pip3 install overloading``

To use extended type hints on Python versions prior to 3.5, install the `typing`_ module from PyPI:

``pip3 install typing``


Compatibility
=============

The library is primarily targeted at Python versions 3.3 and above, but Python 3.2 is still supported for PyPy compatibility.

The Travis CI test suite covers CPython 3.3/3.4/3.5 and PyPy3.

