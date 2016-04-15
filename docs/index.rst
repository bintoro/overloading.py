.. include:: ../README.rst
   :end-line: 14

.. include:: ../README.rst
   :start-line: 15
   :end-before: Documentation


Current release
===============

**overloading.py** v0.5 was released on 16 April 2016.

Notable changes since v0.4
--------------------------

**Breaking change notice:** The treatment of ``classmethod`` and ``staticmethod`` has been harmonized with that of other :ref:`decorators <decorators>`. They must now appear **after** the overloading directive.

* Added support for extended type hints as specified in `PEP 484`_.
* Remaining restrictions on the use of abstract base classes have been lifted.
* The number of exact type matches is no longer a separate factor in :doc:`function ranking <matching>`.
* :ref:`Optional parameters <optional>` now accept an explicit ``None``.
* Multiple implementations may now declare ``*args``, so the concept of a default implementation no longer exists.
* Better decorator support

.. _PEP 484:  https://www.python.org/dev/peps/pep-0484/


.. include:: ../README.rst
   :start-after: https://overloading.readthedocs.org/.


Links
=====

* `Project repository at GitHub <https://github.com/bintoro/overloading.py>`_
* `PyPI entry <https://pypi.python.org/pypi/overloading>`_


Motivation
==========

**Why use overloading instead of \*args / \*\*kwargs?**

* Reduces the need for mechanical argument validation.
* Promotes explicit call signatures, making for cleaner, more self-documenting code.
* Enables the use of full type declarations and type checking tools.

Consider::

    class DB:

        def get(self, *args):
            if len(args) == 1 and isinstance(args[0], Query):
                return self.get_by_query(args[0])
            elif len(args) == 2:
                return self.get_by_id(*args)
            else:
                raise TypeError(...)

        def get_by_query(self, query):
            ...

        def get_by_id(self, id, model):
            ...

The same thing with overloading::

    class DB:

        @overload
        def get(self, query: Query):
            ...

        @overload
        def get(self, id, model):
            ...

**Why use overloading instead of functions with distinct names?**

* Function names may not always be chosen freely; just consider ``__init__()`` or any other externally defined interface.
* Sometimes you just *want* to expose a single function, particularly when different names don't add semantic value::

    def feed(creature: Human):
        ...
    def feed(creature: Dog):
        ...

  vs::

    def feed_human(human):
        ...
    def feed_dog(dog):
        ...

