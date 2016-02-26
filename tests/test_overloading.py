import collections
from functools import wraps

import pytest

import overloading
from overloading import *
from overloading import OverloadingError


overloading.DEBUG = True

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


def test_basic():

    @overloaded
    def f(*args):
        return 'default'

    assert f.__name__ == 'f'

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


def test_classes():

    class C:

        @overloaded
        def f(self, *args):
            return 'default'

        @overloads(f)
        def f(self, foo, bar:int):
            return ('any', 'int')

        @overloads(f)
        def f(self, foo, bar):
            return ('any', 'any')

    inst = C()
    for _ in range(rounds):
        assert inst.f(a, b, c) == 'default'
        assert inst.f(a, 2)    == ('any', 'int')
        assert inst.f(a, b)    == ('any', 'any')

    class S(C):

        @overloads(C.f)
        def f(self, foo, bar, baz):
            return ('any', 'any', 'any')

    inst = S()
    for _ in range(rounds):
        assert inst.f(a, b)    == ('any', 'any')
        assert inst.f(a, b, c) == ('any', 'any', 'any')


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


def test_decorated():

    def decorated(id):
        def f(func):
            @wraps(func)
            def wrapper(*args):
                return func(*args) + (id,)
            return wrapper
        return f

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

