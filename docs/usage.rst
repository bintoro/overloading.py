=====
Usage
=====


Use the ``overload`` decorator to register multiple implementations of a function. All variants must differ by parameter type or count.

Type declarations are specified as function annotations; see `PEP 484`_. ::

    from overloading import *

    @overload
    def div(r: Number, s: Number):
        return r / s

    @overload
    def div(r: int, s: int):
        return r // s

::

    >>> div(3.0, 2)
    1.5
    >>> div(3, s=2)
    1
    >>> div(3, 'a')
    TypeError: Invalid type or number of arguments when calling 'div'.

This simple example already demonstrates several key points:

* Subclass instances satisfy type requirements as one would expect.
* Abstract base classes are valid as type declarations.
* When a call matches multiple implementations, *the most specific variant* is chosen. Both of the above functions are applicable to ``div(3, 2)``, but the latter is more specific.
* Keyword arguments can be used as normal.

``from overloading import *`` imports three decorators: ``overload``, ``overloaded``, and ``overloads``. The last two are discussed in :ref:`alt-syntax`.

Here's another example::

    @overload
    def f(x, *args):
        return 1

    @overload
    def f(x, y, z):
        return 2

    @overload
    def f(x, y, z=0):
        return 3

::

    >>> f(1, 2, 3)
    2
    >>> f(1, 2)
    3
    >>> f(1)
    1

As shown here, type declarations are entirely optional. If a parameter has no expected type, then any value is accepted.

A detailed explanation of the resolution rules can be found in :doc:`matching`, but the system is intuitive enough that you can probably just start using it.


Complex types
=============

Starting with v0.5.0, **overloading.py** has preliminary support for the extended typing elements implemented in the `typing`_ module, including parameterized generic collections::

    @overload
    def f(arg: Iterable[int]):
        return 'an iterable of integers'

    @overload
    def f(arg: Tuple[Any, Any, Any]):
        return 'a three-tuple'

::

    >>> f((1, 2, 3, 4))
    'an iterable of integers'
    >>> f((1, 2, 3))
    'a three-tuple'

Type hints can be arbitrarily complex, but the overloading mechanism ignores nested parameters. That is, ``Sequence[Tuple[int, int]]`` will be simplified to ``Sequence[tuple]`` internally. ``Union`` does not count as a type in its own right, so parameterized containers inside a ``Union`` are okay.

At invocation time, if the expected type is a fixed-length ``Tuple``, every element in the supplied tuple is type-checked. By contrast, type-constrained collections of arbitrary length are supposed to be homogeneous, so only one element in the supplied value is inspected (the first one if it's a sequence).


.. _optional:

Optional parameters
===================

``None`` is not automatically considered an acceptable value for a parameter with a declared type. To extend a type constraint to include ``None``, the parameter can be designated as optional in one of two ways:

* ``arg: X = None``
* ``arg: Optional[X]`` (if using the `typing`_ module)

The difference is that in the latter case an explicit argument must still be provided. ``Optional`` simply allows it to be ``None`` as well as an instance of ``X``.


.. _alt-syntax:

Syntax alternatives
===================

The ``overload`` syntax is really a shorthand for two more specialized decorators:

* ``overloaded`` declares a new overloaded function and registers the first implementation
* ``overloads(f)`` registers a subsequent implementation on ``f``.

The full syntax must be used when an implementation's qualified name is not enough to identify the existing function it overloads. On Python 3.2, only the full syntax is available.


Classes
=======

Everything works the same when overloading methods on classes. Classmethods and staticmethods are directly supported. ::

    class C:

        @overload
        def __init__(self):
            ...

        @overload
        def __init__(self, length: int, default: Any):
            ...

        @overload
        @classmethod
        def from_iterable(cls, things: Sequence):
            ...

        @overload
        @classmethod
        def from_iterable(cls, things: Iterable, key: Callable):
            ...

When a subclass definition adds implementations to an overloaded function declared in a superclass, it is necessary to use the explicit ``overloads(...)`` syntax to refer to the correct function::

    class C:
        @overload
        def f(self, foo, bar):
            ...

    class D(C):
        @overloads(C.f)                # Note `C.f` here.
        def f(self, foo, bar, baz):
            ...

It is not yet possible to override an already registered signature in a subclass.


.. _decorators:

Decorators
==========

Overloading directives may be combined with other decorators.

The rule is to always apply the other decorator before the resulting function is passed to the overloading apparatus. This means placing the custom decorator *after* the overloading directive::

    @overload
    @decorates_int_operation
    def f(x: int):
        ...

    @overload
    @decorates_float_operation
    def f(x: float):
        ...

.. note::
   When writing decorators, remember to use ``functools.wraps()`` so that the original function can be discovered.


Errors
======

``OverloadingError`` is raised if something goes wrong when registering a function.

``TypeError`` is raised if an overloaded function is called with arguments that don't match any of the registered signatures.


.. _PEP 484:  https://www.python.org/dev/peps/pep-0484/
.. _typing:   https://docs.python.org/3/library/typing.html

