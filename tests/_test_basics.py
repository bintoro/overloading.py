import overloading
from overloading import *
from test_overloading import *


@overload
def f(*args):
    return 'default'

@overload
def f(foo):
    return ('any')

@overload
def f(foo, bar:int):
    return ('any', 'int')

@overload
def f(foo, bar, baz):
    return ('any', 'any', 'any')

@overload
def f(foo, bar:int, baz):
    return ('any', 'int', 'any')

@overload
def f(foo:str, bar:int, baz):
    return ('str', 'int', 'any')

@overload
def f(foo:str, bar:int, baz: X):
    return ('str', 'int', 'X')

assert f.__name__ == 'f'
assert f.__doc__  == 'f(...)\n\n'

for _ in range(rounds):
    assert f()           == 'default'
    assert f(a)          == ('any')
    assert f(a, b)       == 'default'
    assert f(a, b, c, d) == 'default'
    assert f(a, 2)       == ('any', 'int')
    assert f(a, b, c)    == ('any', 'any', 'any')
    assert f(1, 2, c)    == ('any', 'int', 'any')
    assert f(a, 2, c)    == ('str', 'int', 'any')
    assert f(a, 2, x)    == ('str', 'int', 'X')
    assert f(a, 2, y)    == ('str', 'int', 'X')

@overload
def g(foo):
    return ('any')

@overload
def g(*args):
    return 'default'

@overload
def g(foo, bar:int):
    return ('any', 'int')

assert g.__name__ == 'g'

for _ in range(rounds):
    assert g()           == 'default'
    assert g(a)          == ('any')
    assert g(a, 2)       == ('any', 'int')

assert len(f.__cache) == 10
assert len(g.__cache) == 3

assert len(overloading.__registry) == 2

