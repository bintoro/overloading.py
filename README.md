# overloading.py

###### Function overloading for Python 3

The `overloading` module provides function dispatching based on the type and number of runtime arguments.


## Installation

`pip install overloading`


## Usage

Use the `overloaded` and `overloads` decorators to register multiple implementations of a function or a method. All variants must differ by their parameter type or count. Argument types are specified as [annotations](https://www.python.org/dev/peps/pep-3107/).

When the overloaded function is called, the module invokes the correct implementation by finding the best match to the supplied arguments.

```python
from overloading import *

@overloaded
def f():
    return 'no args'

@overloads(f)
def f(foo:int, bar:int):
    return 'two ints'

@overloads(f)
def f(foo:str, bar:str):
    return 'two strings'

@overloads(f)
def f(foo, bar):
    return 'two args of any type'

>>> f()
'no args'
>>> f(100, 200)
'two ints'
>>> f('a', 'b')
'two strings'
>>> f('a', 200)
'two args of any type'
>>> f(100)
TypeError: Invalid type or number of arguments when calling overloaded function 'f'.
```

There are no restrictions on the kinds of parameters a function signature may contain. However, the argument matching algorithm only examines regular parameters (those before `*` or `*args` if present).

Keyword arguments can be used as normal:

```python
>>> f(foo=100, bar=200)
'two ints'
```

#### Specifying a default

One of the functions can be designated as a fallback that will be called in case a match is not found. This is done by including the catch-all variable for positional arguments (`*args`) in the function definition.

```python
@overloaded
def f():
    return 'no args'

@overloads(f)
def f(*args):
    # Do something with `args` or raise a custom error.
    return 'default'

>>> f(100)
'default'
```

#### Errors

The module will raise an `OverloadingError` if something goes wrong while the functions are being registered. No avoidable errors will be raised at invocation time.

#### Inheritance and arguments

Subclass instances satisfy type specifications, as one would expect:

```python
class X:    ...
class Y(X): ...

x, y = X(), Y()

@overloads(f)
def f(foo:X):
    return 'X'

>>> f(x)
'X'
>>> f(y)
'X'
```

#### Other decorators

Feel free to overload already-decorated functions, but remember to use `functools.wraps()` so that the module can find the actual function being overloaded.

#### Usage with classes

Everything works the same when overloading methods on classes:

```python
class C:

    @overloaded
    def f(self):
        ...

    @overloads(f)
    def f(self, foo:int, bar:int):
        ...
```

Classmethods and staticmethods are supported too. The only requirement is that overloading must be performed first (i.e., `classmethod` or `staticmethod` must be set as the outer decorator). Attempting to do it the wrong way around will raise an error.

```python
class C:

    @classmethod
    @overloaded
    def f(cls):
        ...

    @classmethod
    @overloads(f)
    def f(cls, foo:int, bar:int):
        ...
```

Inheritance works as expected, but it is not yet possible to override an already-registered method signature in a subclass.

When adding implementations to a subclass, remember to include the superclass name when referring to the function to be overloaded:

```python
class C:
    @overloaded
    def f(self, foo, bar):
        ...

class S(C):
    @overloads(C.f)
    def f(self, foo, bar, baz):
        ...
```

#### Hooks for shared code

Code that should be executed no matter which implementation is called can be placed in functions labeled with the identifiers `'before'` and `'after'`:

```python
@overloaded
def f(foo):
    print('one arg')

@overloads(f)
def f(foo, bar):
    print('two args')

@overloads(f, 'before')
def f(*args):
    print('before')

@overloads(f, 'after')
def f(*args):
    print('after')

>>> f(1)
before
one arg
after
>>> f(1, 2)
before
two args
after
```

All arguments are passed to the hook functions as well, so make sure they can accept them.

#### Miscellaneous

The order in which the functions are defined does not matter, and the function wrapped with the initial `overloaded` decorator is not treated any differently than the successive ones.

Whether or not the individual functions share the same name is of no consequence, but if they are given distinct names, they can also be called directly. The overloading mechanism is only invoked when calling the dispatcher that is bound to the main name:

```python
@overloaded
def f(*args):
    return 'f'

@overloads(f)
def g(foo, bar:int):
    return 'g'

>>> f(100, 200)
'g'
>>> f('a', 'b')
'f'
>>> g('a', 'b')
'g'
```


## Details

The dispatching logic is intended to be robust with no surprises. The resolution algorithm is designed so that the most specific match can always be uniquely determined. This means that

* there is no need to look out for cases where multiple functions might provide an equally good match to a set of arguments
* the function definition order does not affect the outcome.

Function signatures are validated at registration time to ensure that an ambiguous situation can never arise at runtime. Specifically, **the sequence of required parameters must form a unique signature**.

For example, attempting the following definitions will raise an error because `bar`, although it varies by type, is not a required parameter and therefore not considered part of the identifying signature.

```python

@overloaded
def f(foo, bar:int=None):
    ...

@overloads(f)
def f(foo, bar:str=None):
    ...
```

If the above code was allowed, it would be impossible to decide on the intended function when `f` is called with only one argument. However, there's nothing wrong with this:

```python

@overloaded
def f(foo, bar:int=None):
    return 'any, int'

@overloads(f)
def f(foo, bar):
    return 'any, any'

>>> f('a')
'any, int'
>>> f('a', 100)
'any, int'
>>> f('a', 'b')
'any, any'
```

Even though optional arguments are ignored when assessing signature uniqueness, they do count at invocation time when the actual argument matching is carried out.

There is also one exception to the signature uniqueness requirement. The default implementation is allowed to have a signature that also appears elsewhere. Thus, `f()` and `f(*args)` are permitted at the same time. To prevent conflicts, the default function always takes a lower priority if it matches with the same specificity as another function.

#### Limitations on argument inheritance

While a subclass/superclass distinction may serve as the only differentiating aspect between two signatures, this is only allowed for one parameter. To see why, consider a case like this:

```python
class X:    ...
class Y(X): ...

x, y = X(), Y()

@overloaded
def f(a:Y, b:X):
    ...

@overloads(f)
def f(a:X, b:Y):
    ...
```

Calling `f(y, y)` would now result in an equally explicit match with regard to both functions.

Obviously, specifying multiple parameters that vary only along the inheritance axis does not automatically lead to such ambiguity. This limitation may therefore be relaxed in the future once we have a more involved algorithm that can guarantee unique results for more complex signatures.

#### Resolution rules

The most specific match between a set of arguments and a function signature is determined as follows:

1.  Filter out any functions whose signature causes a mismatch based on argument type, count, or name.
2.  Pick the function that accepts the most arguments to fill its regular parameter slots.
3.  In case of a tie, pick the function whose signature contains the greatest number of type annotations.
4.  In case of a tie, pick the function whose signature contains the greatest number of required parameters.
5.  In case of a tie, pick the function that provides the most explicit match in terms of inheritance (i.e., one that specifies a subclass rather than a superclass).
6.  In case of a tie, one of the matches must be the default implementation, so pick the one that is not.

