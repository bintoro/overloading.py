import collections
from functools import wraps
from numbers import Number
import sys

import pytest

import overloading
from overloading import *
from overloading import OverloadingError, typing

if typing:
    from typing import (
        Any, Callable, Generic, Optional, TypeVar, Union, Tuple,
        MutableSequence, Sequence, Iterable, Mapping)
else:
    from collections import Sequence, Iterable


__all__ = ['rounds', 'decorated',
           'a', 'b', 'c', 'd', 'w', 'x', 'y', 'z', 'X', 'Y', 'Z']

overloading.DEBUG = True

min33 = pytest.mark.skipif(sys.version_info < (3, 3), reason="'overload' requires __qualname__")
requires_typing = pytest.mark.skipif(not typing, reason="'typing' module required")


rounds = 3

a, b, c, d, w = 'a', 'b', 'c', 'd', None

class M(type):
    pass

class X(metaclass=M):
    pass

class Y(X):
    pass

class Z(Y):
    pass

x, y, z = X(), Y(), Z()


def decorated(id):
    def f(func):
        @wraps(func)
        def wrapper(*args):
            return func(*args) + (id,)
        return wrapper
    return f


@min33
def test_basics_1():

    import _test_basics


def test_basics_2():

    @overloaded
    def f(*args):
        return 'default'

    @overloads(f)
    def f(foo):
        return ('any')

    @overloads(f)
    def f(foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    def f(foo, bar, baz):
        return ('any', 'any', 'any')

    @overloads(f)
    def f(foo, bar:int, baz):
        return ('any', 'int', 'any')

    @overloads(f)
    def f(foo:str, bar:int, baz):
        return ('str', 'int', 'any')

    @overloads(f)
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

    @overloaded
    def g(foo):
        return ('any')

    @overloads(g)
    def g(*args):
        return 'default'

    @overloads(g)
    def g(foo, bar:int):
        return ('any', 'int')

    assert g.__name__ == 'g'

    for _ in range(rounds):
        assert g()           == 'default'
        assert g(a)          == ('any')
        assert g(a, 2)       == ('any', 'int')

    assert len(f.__cache) == 10
    assert len(g.__cache) == 3


@pytest.mark.parametrize('typing', (None, typing))
def test_optional(typing):

    overloading.typing = typing

    @overloaded
    def f(foo, bar:int=None, baz:str=None):
        return 1

    @overloads(f)
    def f(foo, bar:int):
        return 2

    for _ in range(rounds):
        assert f(a, 1)       == 2
        assert f(a)          == 1
        assert f(a, None)    == 1
        assert f(a, 1, None) == 1
        assert f(a, None, c) == 1
        assert f(a, 1,    c) == 1

    if not typing:
        return

    @overloaded
    def f(foo, bar:Optional[int], baz:Optional[str]):
        return 1

    @overloads(f)
    def f(foo, bar:int):
        return 2

    for _ in range(rounds):
        assert f(a, 1)       == 2
        assert f(a, 1, None) == 1
        assert f(a, None, c) == 1
        assert f(a, 1,    c) == 1


def test_kwargs_1():

    @overloaded
    def f(*args, **kwargs):
        return 'default'

    @overloads(f)
    def f(foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    def f(foo, bar, baz=None):
        return ('any', 'any', 'any?')

    @overloads(f)
    def f(foo, bar=None, baz:int=None):
        return ('any', 'any?', 'int?')

    for _ in range(rounds):
        assert f(a, b, c, d)        == 'default'
        assert f(a, b, c, u=1)      == 'default'
        assert f(a, b, u=1)         == 'default'
        assert f(a, 2)              == ('any', 'int')
        assert f(a, bar=2)          == ('any', 'int')
        assert f(a, b)              == ('any', 'any', 'any?')
        assert f(foo=a, bar=b)      == ('any', 'any', 'any?')
        assert f(a, b, c)           == ('any', 'any', 'any?')
        assert f(a, 2, baz=a)       == ('any', 'any', 'any?')
        assert f(a, 2, baz=1)       == ('any', 'any?', 'int?')
        assert f(a,    baz=1)       == ('any', 'any?', 'int?')
        assert f(a, 2, baz=1, u=1)  == 'default'
        with pytest.raises(TypeError):
            f(a, bar=2, foo=1)

    assert len(f.__cache) == 12


def test_kwargs_2():

    @overloaded
    def f(foo=1, *args, **kwargs):
        return 'default'

    @overloads(f)
    def f(foo=1, **kwargs):
        return 'varkw'

    @overloads(f)
    def f(foo, bar, baz=None):
        return ('any', 'any', 'any?')

    @overloads(f)
    def f(foo, bar=None, baz:int=None, **kwargs):
        return ('any', 'any?', 'int?', 'varkw')

    for _ in range(rounds):
        assert f(a, b, c, d)       == 'default'
        assert f(a, b, c, u=1)     == 'default'
        assert f(a, b, u=1)        == ('any', 'any?', 'int?', 'varkw')
        assert f(a, 2)             == ('any', 'any', 'any?')
        assert f(a, bar=2)         == ('any', 'any', 'any?')
        assert f(a, bar=b)         == ('any', 'any', 'any?')
        assert f(a, b, c)          == ('any', 'any', 'any?')
        assert f(a, 2, baz=a)      == ('any', 'any', 'any?')
        assert f(a, 2, baz=a, u=1) == 'default'
        assert f(a, 2, baz=1, u=1) == ('any', 'any?', 'int?', 'varkw')
        assert f(a, u=1)           == ('any', 'any?', 'int?', 'varkw')
        assert f(foo=a, u=1)       == ('any', 'any?', 'int?', 'varkw')
        assert f(u=1, v=1)         == 'varkw'

    assert len(f.__cache) == 13


def test_kwargs_3():

    @overloaded
    def f(*args, **kwargs):
        return 'default'

    @overloads(f)
    def f(foo:str, bar:int, **kwargs):
        return ('str', 'int', 'varkw')

    @overloads(f)
    def f(foo, bar:int, baz=None, quux=None):
        return ('any', 'int', 'any?', 'any?')

    for _ in range(rounds):
        assert f(a, 2)        == ('str', 'int', 'varkw')
        assert f(a, 2, baz=a) == ('any', 'int', 'any?', 'any?')


def test_kwonlyargs():

    @overloaded
    def f(*args, **kwargs):
        return 'default'

    @overloads(f)
    def f(foo:str, bar:int, *, kwonly):
        return ('str', 'int')

    for _ in range(rounds):
        assert f(a, 2, kwonly=3) == ('str', 'int')

    assert len(f.__cache) == 1


def test_default_1():

    @overloaded
    def f(foo, *args):
        return 'default'

    @overloads(f)
    def f():
        return 'empty'

    @overloads(f)
    def f(foo):
        return ('any')

    @overloads(f)
    def f(foo: int):
        return ('int')

    @overloads(f)
    def f(foo, bar):
        return ('any', 'any')

    for _ in range(rounds):
        assert f()           == 'empty'
        assert f(a)          == ('any')
        assert f(1)          == ('int')
        assert f(a, b)       == ('any', 'any')
        assert f(a, b, c)    == 'default'

    assert len(f.__cache) == 5


def test_default_2():

    @overloaded
    def f(*args):
        return 'default'

    @overloads(f)
    def f():
        return 'empty'

    for _ in range(rounds):
        assert f()  == 'empty'
        assert f(1) == 'default'

    assert len(f.__cache) == 2


def test_nodefault():

    @overloaded
    def f(foo):
        return ('any')

    @overloads(f)
    def f(foo, bar):
        return ('any', 'any')

    for _ in range(rounds):
        with pytest.raises(TypeError):
            f()
        assert f(1)    == ('any')
        assert f(1, 2) == ('any', 'any')
        with pytest.raises(TypeError):
            f(1, 2, 3)

    assert len(f.__cache) == 2


def test_function_ordering_1():

    with pytest.raises(OverloadingError):

        @overloaded
        def f(foo, bar:X=None):
            pass

        @overloads(f)
        def f(foo, bar:dict=None):
            pass

    # Order can be resolved by either including `*args` or dropping the defaults.

    @overloaded
    def g(foo, bar:X=None, *args):
        return 1

    @overloads(g)
    def g(foo, bar:dict=None):
        return 2

    @overloaded
    def h(foo, bar:X):
        return 3

    @overloads(h)
    def h(foo, bar:dict):
        return 4

    for _ in range(rounds):
        assert g(1)     == 2
        assert g(1, x)  == 1
        assert g(1, y)  == 1
        assert h(1, x)  == 3
        assert h(1, {}) == 4


def test_function_ordering_2():

    @overloaded
    def f(i: X, j: Y):
        return (X, Y)

    @overloads(f)
    def f(i: Sequence, j: X):
        return (Sequence, X)

    @overloads(f)
    def f(i: Y, j: X):
        return (Y, X)

    @overloads(f)
    def f(i: int, j: X):
        return (int, X)

    @overloads(f)
    def f(i: Iterable, j: X):
        return (Iterable, X)

    @overloads(f)
    def f(i: int, j: Z):
        return (int, Z)

    @overloads(f)
    def f(i: Iterable, j: Y):
        return (Iterable, Y)

    @overloads(f)
    def f(i: X, j: Z):
        return (X, Z)

    @overloads(f)
    def f(i: int, j: Y):
        return (int, Y)

    for _ in range(rounds):
        assert f(z,  z) == (Y, X)
        assert f(y,  y) == (Y, X)
        assert f({}, z) == (Iterable, Y)
        assert f(1,  y) == (int, Y)


@requires_typing
def test_function_ordering_3():

    @overloaded
    def f(arg: Iterable[int]):
        return Iterable[int]

    @overloads(f)
    def f(arg: Tuple[Number, ...]):
        return Tuple[Number, ...]

    @overloads(f)
    def f(arg: Tuple[Any, Any, Any]):
        return Tuple[Any, Any, Any]

    for _ in range(rounds):
        assert f([1, 2, 3]) == Iterable[int]
        assert f((1, 2, 3)) == Tuple[Number, ...]
        assert f((1, 2, None)) == Tuple[Any, Any, Any]


def test_arg_subtyping_1():

    @overloaded
    def f(foo:X, bar):
        return ('X', 'any')

    @overloads(f)
    def f(foo:Y, bar):
        return ('Y', 'any')

    assert f(x, 1) == ('X', 'any')
    assert f(y, 1) == ('Y', 'any')

    @overloaded
    def f(foo:collections.Iterable):
        return ('Iterable')

    @overloads(f)
    def f(arg:dict):
        return ('dict')

    for _ in range(rounds):
        assert f([1, 2, 3]) == ('Iterable')
        assert f(collections.defaultdict()) == ('dict')


def test_arg_subtyping_2():

    @overloaded
    def f(foo, bar:X=None):
        return ('any', 'X')

    @overloads(f)
    def f(foo, bar:Y=None, *args):
        return ('any', 'Y')

    for _ in range(rounds):
        assert f(1)    == ('any', 'X')
        assert f(1, x) == ('any', 'X')
        assert f(1, y) == ('any', 'Y')


def test_arg_subtyping_3():

    @overloaded
    def f(n:int, foo:X, bar:Y):
        return ('X', 'Y')

    @overloads(f)
    def f(n:int, foo:Y, bar:X):
        return ('Y', 'X')

    for _ in range(rounds):
        assert f(1, y, y) == ('Y', 'X')


def test_arg_subtyping_4():

    @overloaded
    def f(foo:int, bar:X, baz:X):
        return ('int', 'X', 'X')

    @overloads(f)
    def f(foo:int, bar:X, baz:Y):
        return ('int', 'X', 'Y')

    @overloads(f)
    def f(foo:int, bar:Y, baz:X):
        return ('int', 'Y', 'X')

    for _ in range(rounds):
        assert f(1, z, z) == ('int', 'Y', 'X')

    @overloaded
    def f(foo:X, bar:X, baz:X, quux:X):
        return ('X', 'X', 'X', 'X')

    @overloads(f)
    def f(foo:Z, bar:X, baz:Y, quux:Y):
        return ('Z', 'X', 'Y', 'Y')

    @overloads(f)
    def f(foo:Y, bar:Z, baz:X, quux:Z):
        return ('Y', 'Z', 'X', 'Z')

    for _ in range(rounds):
        assert f(z, z, z, z) == ('Z', 'X', 'Y', 'Y')


def test_abc():

    Iterable = collections.Iterable
    Sequence = collections.Sequence
    MutableSequence = collections.MutableSequence

    @overloaded
    def f(u:Iterable, x:int, y:Iterable, z:int):
        return (Iterable, int, Iterable, int)

    @overloads(f)
    def f(u:Iterable, x:int, y:Sequence, z:int):
        return (Iterable, int, Sequence, int)

    for _ in range(rounds):
        assert f((1, 2), 1, {1, 2, 3}, 9) == (Iterable, int, Iterable, int)
        assert f((1, 2), 1, [1, 2, 3], 9) == (Iterable, int, Sequence, int)

    @overloaded
    def f(x:Iterable, y:Iterable, z:Sequence):
        return (Iterable, Iterable, Sequence)

    @overloads(f)
    def f(x:Iterable, y:Sequence, z:Sequence):
        return (Iterable, Sequence, Sequence)

    @overloads(f)
    def f(x:Iterable, y:MutableSequence, z:Sequence):
        return (Iterable, MutableSequence, Sequence)

    @overloads(f)
    def f(x:Iterable, y:MutableSequence, z:Iterable):
        return (Iterable, MutableSequence, Iterable)

    for _ in range(rounds):
        assert f([1, 2, 3], [1, 2, 3], [1, 2, 3]) == (Iterable, MutableSequence, Sequence)


@requires_typing
def test_typing_basics():

    @overloaded
    def f(u:Iterable, x:int, y:Iterable, z:int):
        return (Iterable, int, Iterable, int)

    @overloads(f)
    def f(u:Iterable, x:int, y:Sequence, z:int):
        return (Iterable, int, Sequence, int)

    for _ in range(rounds):
        assert f((1, 2), 1, {1, 2, 3}, 9) == (Iterable, int, Iterable, int)
        assert f((1, 2), 1, [1, 2, 3], 9) == (Iterable, int, Sequence, int)

    @overloaded
    def f(foo:Iterable):
        return (Iterable,)

    @overloads(f)
    def f(arg:Sequence):
        return (Sequence,)

    @overloads(f)
    def f(arg:Mapping):
        return (Mapping,)

    @overloads(f)
    def f(arg:list):
        return (list,)

    @overloads(f)
    def f(x:Iterable, y:list):
        return (Iterable, list)

    @overloads(f)
    def f(x:list, y: Sequence):
        return (list, Sequence)

    @overloads(f)
    def f(x:Iterable, y:Sequence):
        return (Iterable, Sequence)

    assert f.__cacheable is True

    for _ in range(rounds):
        assert f({1, 2, 3}) == (Iterable,)
        assert f([1, 2, 3]) == (list,)
        assert f({1: 2})    == (Mapping,)
        assert f([1, 2, 3], [1, 2, 3]) == (list, Sequence)
        assert f({1, 2, 3}, [1, 2, 3]) == (Iterable, list)


@requires_typing
def test_typing_tuple():

    @overloaded
    def f(arg: Tuple[int, str]):
        return int, str

    @overloads(f)
    def f(arg: Tuple[str, int]):
        return str, int

    for _ in range(rounds):
        assert f((1, b)) == (int, str)
        assert f((a, 2)) == (str, int)
        with pytest.raises(TypeError):
            f((1, 2))
        with pytest.raises(TypeError):
            f(())

    @overloads(f)
    def f(arg: Tuple):
        return ()

    for _ in range(rounds):
        assert f((1, b)) == (int, str)
        assert f((a, 2)) == (str, int)
        assert f((1, 2)) == ()
        assert f(())     == ()

    @overloaded
    def f(arg: Tuple[int, ...]):
        return int

    @overloads(f)
    def f(arg: Tuple[str, ...]):
        return str

    for _ in range(rounds):
        assert f((1, 2, 3)) == int
        assert f((a, b, c)) == str
        with pytest.raises(TypeError):
            f((1, b, 3))
        with pytest.raises(AssertionError):
            f(())

    @overloads(f)
    def f(arg: Tuple):
        return ()

    for _ in range(rounds):
        assert f((1, 2, 3)) == int
        assert f((a, b, c)) == str
        assert f((1, b, 3)) == ()
        with pytest.raises(AssertionError):
            f(())


@requires_typing
def test_typing_type_var():

    N = TypeVar('N', int, float)
    M = TypeVar('M', list, str)
    T = TypeVar('T')

    class Foo(Generic[T, M]):
        pass

    class Bar(Foo[int, str]):
        pass

    @overloaded
    def f(arg: Sequence[N]):
        return N

    @overloads(f)
    def f(arg: Sequence[M]):
        return M

    @overloads(f)
    def f(arg: Foo):
        return Foo

    @overloads(f)
    def f(arg: Bar):
        return Bar

    assert f([1, 2, 3]) == N
    assert f([a, b, c]) == M
    assert f(Foo()) == Foo
    assert f(Bar()) == Bar


@requires_typing
def test_typing_parameterized_collections():

    @overloaded
    def f(arg: Iterable[int]):
        return Iterable[int]

    @overloads(f)
    def f(arg: Iterable[str]):
        return Iterable[str]

    @overloads(f)
    def f(arg: Sequence[int]):
        return Sequence[int]

    @overloads(f)
    def f(arg: Sequence[str]):
        return Sequence[str]

    @overloads(f)
    def f(arg: Mapping[str, int]):
        return Mapping[str, int]

    assert f.__cacheable is False

    for _ in range(rounds):
        assert f({1, 2, 3}) == Iterable[int]
        assert f({a, b, c}) == Iterable[str]
        assert f([1, 2, 3]) == Sequence[int]
        assert f([a, b, c]) == Sequence[str]
        assert f({a: 1}) == Mapping[str, int]
        assert f({a: 1.0}) == Iterable[str]
        with pytest.raises(TypeError):
            f({1.0: a})

    @overloaded
    def f(arg: Iterable[X]):
        return Iterable[X]

    @overloads(f)
    def f(arg: Iterable[Y]):
        return Iterable[Y]

    for _ in range(rounds):
        assert f({x, x, x}) == Iterable[X]
        assert f({y, y, y}) == Iterable[Y]
        assert f([z, z, z]) == Iterable[Y]
        assert f([])        == Iterable[Y]

    V = TypeVar('V', bound=X, covariant=True)

    class XIterable(Iterable[V], set):
        pass

    @overloaded
    def f(arg: XIterable):
        return XIterable

    @overloads(f)
    def f(arg: Iterable[Y]):
        return Iterable[Y]

    for _ in range(rounds):
        assert f(XIterable({x, x, x})) == XIterable
        assert f(XIterable({y, y, y})) == XIterable
        assert f(XIterable([z, z, z])) == XIterable

    T = TypeVar('T')

    @overloaded
    def f(arg: Iterable[X]):
        return X

    @overloads(f)
    def f(arg: Iterable[T][Y]):
        return Y

    for _ in range(rounds):
        assert f([x, x, x]) == X
        assert f([y, y, y]) == Y
        assert f([z, z, z]) == X
        assert f([])        == Y


@requires_typing
def test_typing_mapping():

    K = TypeVar('K', covariant=True)
    T = TypeVar('T')

    CovariantKeyDict = Mapping[K, T]
    AnyValueDict = Mapping[int, T]

    class MyInt(int): pass
    three = MyInt(3)

    class MyString(str): pass
    hello = MyString('hello')

    @overloaded
    def f(arg: Mapping[int, str]):
        return Mapping[int, str]

    assert f({3: 'hey'}) == Mapping[int, str]
    assert f({3: hello}) == Mapping[int, str]
    with pytest.raises(TypeError):
        f({three: 'hey'})

    @overloaded
    def f(arg: AnyValueDict):
        return AnyValueDict

    @overloads(f)
    def f(arg: CovariantKeyDict[int, str]):
        return CovariantKeyDict[int, str]

    for _ in range(rounds):
        assert f({3: 'hey'})     == CovariantKeyDict[int, str]
        assert f({3: hello})     == AnyValueDict
        assert f({three: 'hey'}) == CovariantKeyDict[int, str]
        assert f({3: x})         == AnyValueDict
        assert f({})             == CovariantKeyDict[int, str]
        with pytest.raises(TypeError):
            f({'hi': 'hey'})


@requires_typing
def test_typing_union():

    @overloaded
    def f(arg: Union[Tuple[int, ...], int]):
        return 1

    @overloads(f)
    def f(arg: Sequence[int]):
        return 2

    for _ in range(rounds):
        assert f((1, 2, 3)) == 1

    @overloaded
    def f(arg: Sequence):
        return 1

    @overloads(f)
    def f(arg: Union[Sequence[int], Tuple[int]]):
        return 2

    @overloads(f)
    def f(arg: Union[Iterable[int], MutableSequence[int]]):
        return 3

    for _ in range(rounds):
        assert f((1, 2, 3)) == 2
        assert f([1, 2, 3]) == 3

    @overloaded
    def f(arg: Tuple[Union[int, float], int]):
        return 1

    @overloads(f)
    def f(arg: Tuple[str, int]):
        return 2

    for _ in range(rounds):
        assert f((1, 2)) == 1
        assert f((a, 2)) == 2


def test_named():

    @overloaded
    def f(*args):
        return 'default'

    @overloads(f)
    def g(foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    def h(foo, bar):
        return ('any', 'any')

    for _ in range(rounds):
        assert f(a, b, c) == 'default'
        assert f(a, 2)    == ('any', 'int')
        assert f(a, b)    == ('any', 'any')
        assert g(w, w)    == ('any', 'int')
        assert h(w, w)    == ('any', 'any')
        with pytest.raises(TypeError):
            h(w)


def test_hooks():

    called = []

    def test(func, args, expected):
        func(*args)
        assert called == expected
        del called[:]

    @overloaded
    def f(*args):
        called.append('default')

    @overloads(f, 'before')
    def f(*args):
        called.append('before')

    @overloads(f, 'after')
    def f(*args):
        called.append('after')

    @overloads(f)
    def f(foo, bar:int):
        called.append(('any', 'int'))

    @overloads(f)
    def f(foo, bar):
        called.append(('any', 'any'))

    for _ in range(rounds):
        test(f, (a,  ), ['before', 'default', 'after'])
        test(f, (a, b), ['before', ('any', 'any'), 'after'])
        test(f, (a, 2), ['before', ('any', 'int'), 'after'])


@min33
def test_classes():

    import _test_classes


@min33
def test_classmethods():

    import _test_classmethods


def test_staticmethods():

    class C:

        @staticmethod
        @overloaded
        def f(*args):
            return 'default'

        @overloads(f)
        def f(foo, bar:int):
            return ('any', 'int')

        @overloads(f)
        def g(foo, bar):
            return ('any', 'any')

    for obj in (C, C()):
        for _ in range(rounds):
            assert obj.f(a, b, c) == 'default'
            assert obj.f(a, 2)    == ('any', 'int')
            assert obj.f(a, b)    == ('any', 'any')

    class C:

        @overloaded
        @staticmethod
        def f(*args):
            return 'default'

        @overloads(f)
        @staticmethod
        def f(foo, bar:int):
            return ('any', 'int')

        @overloads(f)
        @staticmethod
        def f(foo:int, bar):
            return ('int', 'any')

        @overloads(f)
        @staticmethod
        def g(foo, bar):
            return ('any', 'any')

    for obj in (C, C()):
        for _ in range(rounds):
            assert obj.f(a, b, c) == 'default'
            assert obj.f(a, 2)    == ('any', 'int')
            assert obj.f(1, b)    == ('int', 'any')
            assert obj.f(a, b)    == ('any', 'any')


@min33
def test_decorated_1():

    import _test_decorated


def test_decorated_2():

    @overloaded
    @decorated(2)
    @decorated(1)
    def f(*args):
        return ('default',)

    @overloads(f)
    @decorated(4)
    @decorated(3)
    def f(foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    @decorated(5)
    def f(foo:int, bar):
        return ('int', 'any')

    for _ in range(rounds):
        assert f(a, b, c) == ('default', 1, 2)
        assert f(a, 2)    == ('any', 'int', 3, 4)
        assert f(1, b)    == ('int', 'any', 5)

    @decorated(2)
    @overloaded
    def f(*args):
        return ('default',)

    @overloads(f)
    @decorated(1)
    def f(foo, bar:int):
        return ('any', 'int')

    @decorated(3)
    @overloads(f)
    def f(foo:int, bar):
        return ('int', 'any')

    for _ in range(rounds):
        assert f(a, b, c) == ('default', 2, 3)
        assert f(a, 2)    == ('any', 'int', 1, 2, 3)
        assert f(1, b)    == ('int', 'any', 2, 3)

    @decorated(3)
    @decorated(2)
    @overloaded
    def f(*args):
        return ('default',)

    @overloads(f)
    @decorated(1)
    def g(foo, bar:int):
        return ('any', 'int')

    @decorated(4)
    @overloads(f)
    def h(foo:int, bar):
        return ('int', 'any')

    for _ in range(rounds):
        assert f(a, b, c) == ('default', 2, 3)
        assert f(a, 2)    == ('any', 'int', 1, 2, 3)
        assert f(1, b)    == ('int', 'any', 2, 3)
        assert h(1, b)    == ('int', 'any', 4)


def test_void_implementation():

    doc = \
        """f(a, b, x: int, y: float)

        Just
        a
        docstring
        """

    @overloaded
    def f(a, b, x : int, y : float):
        """
        Just
        a
        docstring
        """

    assert f.__doc__ == doc

    @overloaded
    def f(foo: 0):
        """f(a, b, x: int, y: float)

        Just
        a
        docstring
        """

    assert f.__doc__ == doc

    @overloaded
    # aaa
    def g(self,
          x: int) -> None:    

        # xzxz

        ... # qweqwe

    assert g.__doc__ == 'g(x: int) -> None\n\n'

    @overloaded
    def h(): ...

    assert h.__doc__ == 'h(...)\n\n'

    assert len(f.__functions) == 0
    assert len(g.__functions) == 0
    assert len(h.__functions) == 0


def test_errors():

    # Invalid signature
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo: 1):
            pass

    # Recurring signature
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo):
            pass
        @overloads(f)
        def f(foox):
            pass

    # Recurring signature
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo:int, bar, baz=None):
            pass
        @overloads(f)
        def f(foo:int, bar):
            pass

    # Recurring signature with `*args`
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo, *args):
            pass
        @overloads(f)
        def f(foo, bar=None, *args):
            pass

    # `overloads` without `overloaded`
    with pytest.raises(OverloadingError):
        def f(*args):
            pass
        @overloads(f)
        def f(foo):
            pass

    # Invalid object
    with pytest.raises(OverloadingError):
        @overloaded
        class Foo:
            pass
    with pytest.raises(OverloadingError):
        @overloaded
        def f(*args):
            pass
        @overloads(f)
        class Foo:
            pass


@requires_typing
def test_errors_typing():

    # Recurring signature with `Union`
    with pytest.raises(OverloadingError):
        @overloaded
        def f(arg: Union[str, Iterable[int]]):
            pass
        @overloads(f)
        def f(arg: Union[int, Iterable[int]]):
            pass

    # Recurring signature with `Optional`
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo, bar:Optional[int]):
            pass
        @overloads(f)
        def f(foo, bar:int):
            pass

    # Recurring signature with `Optional`
    with pytest.raises(OverloadingError):
        @overloaded
        def f(foo, bar:Optional[int]):
            pass
        @overloads(f)
        def f(foo, bar:Optional[str]):
            pass

