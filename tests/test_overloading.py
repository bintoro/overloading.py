import collections
from functools import wraps
import sys

import pytest

import overloading
from overloading import *
from overloading import OverloadingError, typing

if typing:
    from typing import (
        Any, Callable, Generic, Optional, TypeVar, Union, Tuple,
        Sequence, Iterable)


__all__ = ['rounds', 'decorated',
           'a', 'b', 'c', 'd', 'w', 'x', 'y', 'z', 'X', 'Y', 'Z']

overloading.DEBUG = True

min33 = pytest.mark.skipif(sys.version_info < (3, 3), reason="'overload' requires __qualname__")
requires_typing = pytest.mark.skipif(not typing, reason="'typing' module required")


rounds = 100

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
        return ('any', 'optional int', 'optional str')

    @overloads(f)
    def f(foo, bar:int):
        return ('any', 'int')

    for _ in range(rounds):
        assert f(a, 1)       == ('any', 'int')
        assert f(a)          == ('any', 'optional int', 'optional str')
        assert f(a, None)    == ('any', 'optional int', 'optional str')
        assert f(a, 1, None) == ('any', 'optional int', 'optional str')
        assert f(a, None, c) == ('any', 'optional int', 'optional str')
        assert f(a, 1,    c) == ('any', 'optional int', 'optional str')


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
        assert f(z, z, z, z) == ('Y', 'Z', 'X', 'Z')


def test_type_ordering():

    assert overloading.find_most_derived([X, Z, Y, Z, X, Y]) == Z
    assert overloading.find_most_derived(
        [(X, 1), (Z, 2), (Y, 3), (Z, 4), (X, 5), (Y, 6)], index=0) == [(Z, 2), (Z, 4)]


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

    for _ in range(rounds):
        assert f({1, 2, 3}) == (Iterable,)
        assert f([1, 2, 3]) == (list,)
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


@requires_typing
def test_typing_type_var():

    N = TypeVar('N', int, float)
    M = TypeVar('M', list, str)
    T = TypeVar('T')

    class Foo(Generic[T, M]):
        pass

    @overloaded
    def f(arg: Sequence[N]):
        return N

    @overloads(f)
    def f(arg: Sequence[M]):
        return M

    @overloads(f)
    def f(arg: Foo[int, str]):
        return 'Hello'

    assert f([1, 2, 3]) == N
    assert f([a, b, c]) == M
    assert f(Foo()) == 'Hello'


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


def test_classmethods():

    class C:

        @classmethod
        @overloaded
        def f(cls, *args):
            return 'default'

        @classmethod
        @overloads(f)
        def f(cls, foo, bar:int):
            return ('any', 'int')

        @classmethod
        @overloads(f)
        def f(cls, foo, bar):
            return ('any', 'any')

    for _ in range(rounds):
        assert C.f(a, b, c) == 'default'
        assert C.f(a, 2)    == ('any', 'int')
        assert C.f(a, b)    == ('any', 'any')


def test_staticmethods():

    class C:

        @staticmethod
        @overloaded
        def f(*args):
            return 'default'

        @staticmethod
        @overloads(f)
        def f(foo, bar:int):
            return ('any', 'int')

        @staticmethod
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

        @staticmethod
        @overloads(f)
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

    # Recurring `*args`
    with pytest.raises(OverloadingError):
        @overloaded
        def f(*args):
            pass
        @overloads(f)
        def f(foo, bar:int, *args):
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

