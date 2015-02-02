# overloading.py

###### Function overloading for Python 3

The `overloading` module provides function and method dispatching based on the type and number of runtime arguments.

#### First example

Original code:

```python
class DB:

    def get(self, *args):
        if len(args) == 1 and isinstance(args[0], Query):
            return self.get_by_query(args[0])
        elif len(args) == 2:
            return self.get_by_id(id=args[0], model=args[1])
        else:
            raise TypeError()

    def get_by_query(self, query):
        ...

    def get_by_id(self, id, model):
        ...
```

The same thing with overloading:

```python
class DB:

    @overloaded
    def get(self, query: Query):
        ...

    @overloads(get)
    def get(self, id, model):
        ...
```


## Installation

`pip install overloading`


## Usage

Use the `overloaded` and `overloads` decorators to register multiple implementations of a function that differ by their parameter type or count. Argument types are specified as [annotations](https://www.python.org/dev/peps/pep-3107/).

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
>>> f(100)
TypeError: Invalid type or number of arguments when calling 'f'.
>>> f(100, 200)
'two ints'
>>> f('a', 'b')
'two strings'
>>> f('a', 200)
'two args of any type'
```

Keyword arguments can be used as normal:

```python
>>> f(foo=100, bar=200)
'two ints'
```

#### Specifying a default

One of the functions can be designated as a fallback that will be called in case a match is not found. This is done by including the catch-all variable for positional arguments (`*args`).

```python
@overloaded
def f(x:str):
    return 'string'

@overloads(f)
def f(*args, **kwargs):
    return 'default'

>>> f()
'default'
>>> f('a')
'string'
>>> f(100)
'default'
```

#### Errors

The module will raise an `OverloadingError` if something goes wrong while the functions are being registered. No avoidable errors will be raised at invocation time.

#### Inheritance and arguments

Subclass instances will satisfy type specifications, as one would expect:

```python
class Animal:      ...
class Dog(Animal): ...

@overloads(f)
def f(creature:Animal):
    return 123

>>> f(Animal())
123
>>> f(Dog())
123
```

#### Other decorators

Feel free to overload already-decorated functions, but remember to use `functools.wraps()` so that the module can find the actual function being overloaded.

#### Usage with classes

Everything works the same when overloading methods on classes:

```python
class C:

    @overloaded
    def __init__(self):
        ...

    @overloads(__init__)
    def __init__(self, foo:list):
        ...
```

Classmethods and staticmethods are supported too. The only requirement is that overloading must be performed first (i.e., `classmethod` or `staticmethod` must be set as the outer decorator):

```python
class C:

    @classmethod
    @overloaded
    def f(cls):
        ...
```

Inheritance works as expected, but it is not yet possible to override an already-registered method signature in a subclass.

When adding implementations to a subclass, remember to refer to the dispatcher that is defined in the parent class:

```python
class C:
    @overloaded
    def f(self, foo, bar):
        ...

class S(C):
    @overloads(C.f)                # Observe `C.f` here.
    def f(self, foo, bar, baz):
        ...
```

#### Hooks for shared code

Code that should be executed no matter which implementation is called can be placed in functions labeled with the identifiers `'before'` and `'after'`. They are particularly useful in connection with `__init__` methods.

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

>>> f(100)
before
one arg
after
>>> f(100, 200)
before
two args
after
```

All arguments are passed to the hook functions as well, so make sure they can accept them.

#### Miscellaneous

The order in which the functions are defined does not matter, and the function wrapped with the initial `overloaded` decorator is not treated any differently than the successive ones, except that it determines the name by which the overloaded function is invoked.

Whether or not the other functions share the same name is of no consequence, but if they are given distinct names, they can also be called directly. A direct call will bypass the overloading mechanism, since the dispatcher is bound to the invocation name only.

```python
@overloaded
def f(foo:str):
    return 'f'

@overloads(f)
def g(foo):
    return 'g'

>>> f(100)
'g'
>>> f('a')
'f'
>>> g('a')  # Bypass overloading.
'g'
```

There are no restrictions on the kinds of parameters a function signature may contain. However, the argument matching algorithm only examines regular parameters (those before `*` or `*args` if present). In other words, arguments consumed by catch-all variables or Py3-style keyword-only arguments do not count towards match quality.


## Details

The dispatching logic is intended to be robust with no surprises. The resolution algorithm is designed so that the most specific match can always be uniquely determined. This means that

* there is no need to look out for cases where multiple functions might provide an equally good match to a set of arguments
* the function definition order does not affect the outcome.

Function signatures are validated at registration time to ensure that an ambiguous situation can never arise at runtime. Specifically, **the sequence of required parameters must form a unique signature**.

For example, attempting the following definitions will raise an error because `bar`, although it varies by type, is not a required parameter and therefore not considered part of the identifying signature.

```python
@overloaded
def f(foo, bar:int=100):
    ...

@overloads(f)
def f(foo, bar:str=None):
    ...
```

If the above code was allowed, it would be impossible to decide on the intended function when `f` is called with only one argument. However, there's nothing wrong with this:

```python
@overloaded
def f(foo, bar:int=100):
    return 'any, int'

@overloads(f)
def f(foo, bar:str):    # `bar` no longer optional
    return 'any, str'

>>> f('a')
'any, int'
>>> f('a', 200)
'any, int'
>>> f('a', 'b')
'any, str'
```

There is one exception to the signature uniqueness requirement. The default implementation is allowed to have a signature that also appears elsewhere. Thus, `f()` and `f(*args)` are permitted at the same time. To prevent conflicts, the default function always takes a lower priority if it matches with the same specificity as another function.

#### More on optional parameters

Even though optional parameters are ignored when assessing signature uniqueness, they do matter at invocation time when the actual argument matching is carried out. Here is an artificial example that demonstrates this:

```python
@overloaded
def f(*args):
    return 'f'

@overloads(f)
def g(foo, bar, baz=None):
    return 'g'

@overloads(f)
def h(foo, bar=None, baz:int=None):
    return 'h'

@overloads(f)
def i(foo=None, bar=None, baz=None, **kwargs):
    return 'i'

>>> f()
'i'
>>> f(100)
'h'
>>> f(100, 200)
'g'
>>> f(100, 200, 'a')
'g'
>>> f(100, 200, 300)
'h'
>>> f(100, 200, quux=1)
'i'
```

Above, `f(100)` resolved to `h(100)` because, other things equal, a signature with fewer optional parameters is considered to be more specific. However, if `i` were defined as
````python
def i(foo:int=None, bar=None, baz=None, **kwargs): ...
````
then `f(100)` would resolve to `i(100)` instead. This is because a type-based match always takes precedence.

#### Limitations on argument inheritance

While a subclass/superclass distinction is allowed to serve as the only differentiating aspect between two signatures, there can be at most one such parameter. To see why, consider a case like this:

```python
class Animal:      ...
class Dog(Animal): ...

class Vehicle:      ...
class Car(Vehicle): ...

@overloaded
def f(creature:Dog, thing:Vehicle):
    ...

@overloads(f)
def f(creature:Animal, thing:Car):
    ...
```

Calling `f(Dog(), Car())` would now result in an equally explicit match with regard to both functions; one argument would match directly and the other via inheritance.

This limitation may be relaxed in the future once the validation algorithm is equipped to recognize cases that are not susceptible to this problem.

#### Resolution rules

The most specific match between a set of arguments and a group of function signatures is determined by applying the following rules until a single function remains:

1.  Filter out any functions that cause a mismatch based on argument type, count, or name.
2.  Pick the function that accepts the most arguments to fill its regular parameter slots.
3.  Pick the function whose signature matches the greatest number of argument types.
4.  Pick the function whose signature contains the greatest number of required parameters.
5.  Pick the function that provides the most explicit match in terms of inheritance (i.e., one that specifies a subclass rather than a superclass).
6.  Pick the function that is not the default implementation.

