# overloading.py

###### Function overloading for Python 3

`overloading` is a module that provides function dispatching based on the types and number of runtime arguments.

#### Features

* Function validation upon registration and detailed resolution rules guarantee a unique, well-defined outcome at runtime.
* Supports optional parameters in function signatures.
* Evaluates both positional and keyword arguments when resolving the best match.
* Supports fallback functions and execution of shared code.
* Supports argument polymorphism.
* Supports classes and inheritance, including classmethods and staticmethods.

#### First example

Sample code without overloading:

```python
class DB:

    def get(self, *args):
        if len(args) == 1 and isinstance(args[0], Query):
            return self.get_by_query(args[0])
        elif len(args) == 2:
            return self.get_by_id(id=args[0], model=args[1])
        else:
            raise TypeError(...)

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

#### Basics

Use the `overloaded` and `overloads` decorators to register multiple implementations of a function. All variants must differ by parameter type or count. Argument types are specified as [annotations](https://www.python.org/dev/peps/pep-3107/).

When the overloaded function is called, the module invokes the correct implementation by finding the best match to the supplied arguments.

```python
from overloading import *

@overloaded
def f():
    return 'no args'

@overloads(f)
def f(foo):
    return 'one arg of any type'

@overloads(f)
def f(foo:int, bar:int):
    return 'two ints'

>>> f()
'no args'
>>> f('a')
'one arg of any type'
>>> f(100, 200)
'two ints'
>>> f('a', 200)
TypeError: Invalid type or number of arguments when calling 'f'.
```

Keyword arguments can be used as normal:

```python
>>> f(foo=100, bar=200)
'two ints'
```

#### Specifying a default handler

One of the functions can be designated as a fallback that will be called in case a match is not found. This is done by including the catch-all variable for positional arguments (`*args`).

Continuing with the previous example:

```python
@overloads(f)
def f(*args, **kwargs):
    return 'default'

>>> f('a', 200)
'default'
```

#### Argument subtyping

Subclass instances will satisfy type specifications as one would expect:

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

The overloading system can be used together with other decorators, but remember to use `functools.wraps()` so that the module can find the inner function. The order in which the decorators are applied generally does not matter (but classmethods and staticmethods are a notable exception; see below).

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

Classmethods and staticmethods must be defined by wrapping an already-overloaded function — i.e., by using an outer decorator:

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
    @overloads(C.f)                # Note `C.f` here.
    def f(self, foo, bar, baz):
        ...
```

#### Hooks for shared code

Code that should be executed no matter which implementation is called can be placed in functions labeled with the identifiers `'before'` and `'after'`. They are particularly useful in connection with `__init__` methods.

```python
@overloaded
def f(foo):
    ...

@overloads(f)
def g(foo, bar):
    ...

@overloads(f, 'before')
def pre(*args):
    ...

@overloads(f, 'after')
def post(*args):
    ...
```

The call `f(1, 2)` would now be equivalent to `pre(1, 2); g(1, 2); post(1, 2);`.

## Details

The dispatching logic is intended to be robust with no surprises. The resolution algorithm is designed so that the most specific match can always be uniquely determined. This means that

* there is no need to look out for cases where multiple functions might provide an equally good match to a set of arguments
* the function definition order does not affect the outcome.

Function signatures are validated at registration time to ensure that an ambiguous situation can never arise at runtime. Specifically, **the sequence of required parameters must form a unique signature**.

For example, attempting the following definitions will raise an error because `bar`, although it varies on type, is not a required parameter and therefore not considered part of the identifying signature.

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
>>> f('a', 'b')
'any, str'
```

There is one exception to the signature uniqueness requirement. The default implementation is allowed to have a signature that also appears elsewhere. Thus, `f()` and `f(*args)` are permitted at the same time. To prevent conflicts, the default function takes a lower priority when needed.

#### Resolution rules

The most specific match between a set of arguments and a group of function signatures is determined by applying the following rules until a single function remains:

1.  Filter out any functions that cause a mismatch based on argument type, count, or name.
2.  Pick the function that accepts the most arguments to fill its regular parameter slots.
3.  Pick the function whose signature matches the most argument types.
4.  Pick the function with the greatest number of exact matches in the previous step (as opposed to matches due to subtyping).
5.  Pick the function with an exactly matching type at the earliest parameter position where the competing functions do not have such a match.
6.  Pick the function whose signature contains the greatest number of required parameters.
7.  Pick the function that is not the default implementation.

#### Errors

The module will raise an `OverloadingError` if something goes wrong while the functions are being registered, with the intention that no avoidable errors would have to be raised at invocation time.

#### Miscellaneous

The function wrapped with the initial `overloaded` decorator is not treated any differently than the successive ones, except that it determines the name by which the overloaded function is invoked.

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

#### Advanced example: Optional parameters

Even though optional parameters are ignored when assessing signature uniqueness, they do matter at invocation time when the actual argument matching is carried out.

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

#### Advanced example: Argument subtyping

Consider a case like this:

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

Calling `f(Dog(), Car())` would seem to result in an equally explicit match with regard to both functions; one of the arguments matches exactly and the other due to inheritance. The resolution rules address this by directing that the first parameter to match exactly will determine the winner. Therefore in this case the first function would be invoked.

