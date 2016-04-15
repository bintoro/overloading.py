=================
Function matching
=================


Although real-life use cases are typically quite straightforward, the function resolution algorithm is equipped to deal with any combination of simultaneously matching functions and rank them by match quality. A core goal of this library is to eliminate situations where a call to an overloaded function fails due to multiple implementations providing an equally good fit to a set of arguments.

In compiled languages, such ambiguous cases can often be identified and rejected at compile time. This possibility doesn't exist in Python, leaving us with two options: either prepare to raise an ambiguous call exception on invocation, or devise a set of rules that guarantee the existence of a preferred match every time. **overloading.py** takes the latter approach.


Validation
==========

Function signatures are validated on registration to ensure that a truly ambiguous situation cannot arise at invocation time. Specifically, **the required regular parameters must form a unique signature**. In addition, a catch-all parameter for positional arguments is considered a further identifying feature, allowing ``f(x)`` and ``f(x, *args)`` to coexist.

For example, attempting the following definitions will immediately raise an error::

    @overload
    def f(a: str, b: int, c: int = 100):
        ...

    @overload
    def f(a: str, b: int, c: str = None):
        ...

The reason should be obvious: were ``f`` called with only the first two arguments, inferring the correct function would be impossible.


Resolution
==========

The closest match between a set of arguments and a group of implementations is selected as follows:

1.  Identify candidate functions based on parameter count and names.
2.  Of those, identify applicable functions by comparing argument types to expected types.

If there are multiple matches, the rest of the rules are applied until a single function remains:

3.  Choose the function that accepts the most arguments to fill its regular parameter slots.
4.  Choose the function whose signature matches the most arguments due to specific type declarations (as opposed to arguments that match because *any* type is allowed).
5.  Choose the function that, in terms of parameter order, is the first to produce a unique most specific match.
6.  Choose the function that accepts the greatest number of required parameters.
7.  Choose the function that is of fixed arity (does not declare ``*args``).

.. note:: Even though optional parameters are ignored when assessing signature uniqueness, they do matter at invocation time when the actual argument matching is carried out.

.. note:: The matching algorithm only examines regular parameters (those before ``*args``). While variable-argument parameters (``*`` and ``**``) and keyword-only parameters are allowed, arguments consumed by them don't count towards match quality.

There are two kinds of situations where the algorithm may not produce an unequivocal winner:

The declared types for a particular parameter might include a group of abstract base classes with a type hierarchy that is either inconsistent or divided into multiple disjoint parts. This is mostly a theoretical concern.

A more practically relevant case arises when an empty container is passed to a function that is overloaded on the type parameter of a generic collection::

    @overload
    def f(x: Iterable[int]): ...

    @overload
    def f(x: Iterable[str]): ...

::

    >>> f([])

Clearly, it is impossible to infer anything about the type of elements that aren't there. However, since applying overloading to generics is potentially useful, such a setup is allowed.

The current solution is to fall back on the function definition order as a last resort: an earlier declaration takes precedence. In the future, a specialized type hint could be used to explicitly designate a function as a preferred handler for empty collections.

Apart from these special cases, function definition order is of no consequence to the dispatch logic.


Example: Argument subtyping
---------------------------

Consider a case like this::

    @overload
    def f(x: Iterable, y: Sequence):
        ...

    @overload
    def f(x: Sequence, y: Iterable):
        ...

::

    >>> f([0, 1], [2, 3])

The call would seem to result in an equally explicit match with regard to both functions, and indeed many languages, such as Java, would reject such a call as ambiguous. The resolution rules address this by dictating that the first parameter to produce a ranking will determine the winner. Therefore, in this case, the second function would be chosen, as it provides a more specific match at the initial position. Intuitively, a list is closer to ``Sequence`` than to ``Iterable`` in the type hierarchy, even though it doesn't really inherit from either.

