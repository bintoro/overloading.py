from functools import wraps

import pytest

from overloading import *
from overloading import OverloadingError
from test_overloading import *


@overload
@decorated(2)
@decorated(1)
def f(*args):
    return ('default',)

@overload
@decorated(4)
@decorated(3)
def f(foo, bar:int):
    return ('any', 'int')

@overload
@decorated(5)
def f(foo:int, bar):
    return ('int', 'any')

for _ in range(rounds):
    assert f(a, b, c) == ('default', 1, 2)
    assert f(a, 2)    == ('any', 'int', 3, 4)
    assert f(1, b)    == ('int', 'any', 5)

@decorated(2)
@overload
def g(*args):
    return ('default',)

@overload
@decorated(1)
def g(foo, bar:int):
    return ('any', 'int')

@decorated(3)
@overload
def g(foo:int, bar):
    return ('int', 'any')

for _ in range(rounds):
    assert g(a, b, c) == ('default', 3)
    assert g(a, 2)    == ('any', 'int', 1, 3)
    assert g(1, b)    == ('int', 'any', 3)

def bad_decorator(func):
    # no `wraps`
    def wrapper(*args):
        return func(*args) + (id,)
    return wrapper

with pytest.raises(OverloadingError):
    @overload
    @bad_decorator
    def q():
        pass

