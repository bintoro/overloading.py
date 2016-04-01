from overloading import *
from test_overloading import *


class B:

    @classmethod
    @overloaded
    def f(cls, *args):
        return 'default'

    @overloads(f)
    def f(cls, foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    def f(cls, foo, bar):
        return ('any', 'any')

for obj in (B, B()):
    for _ in range(rounds):
        assert obj.f(a, b, c) == 'default'
        assert obj.f(a, 2)    == ('any', 'int')
        assert obj.f(a, b)    == ('any', 'any')

class C:

    @overloaded
    @classmethod
    def f(cls, *args):
        return 'default'

    @overloads(f)
    @classmethod
    def f(cls, foo, bar:int):
        return ('any', 'int')

    @overloads(f)
    @classmethod
    def f(cls, foo, bar):
        return ('any', 'any')

for obj in (C, C()):
    for _ in range(rounds):
        assert obj.f(a, b, c) == 'default'
        assert obj.f(a, 2)    == ('any', 'int')
        assert obj.f(a, b)    == ('any', 'any')

class D:

    @overload
    @classmethod
    def f(cls, *args):
        return 'default'

    @overload
    @classmethod
    def f(cls, foo, bar:int):
        return ('any', 'int')

    @overload
    @classmethod
    def f(cls, foo, bar):
        return ('any', 'any')

for obj in (D, D()):
    for _ in range(rounds):
        assert obj.f(a, b, c) == 'default'
        assert obj.f(a, 2)    == ('any', 'int')
        assert obj.f(a, b)    == ('any', 'any')

