from overloading import *
from test_overloading import *


class C:

    @overload
    def f(self, *args):
        return 'default'

    @overload
    def f(self, foo, bar:int):
        return ('any', 'int')

    @overload
    def f(self, foo, bar):
        return ('any', 'any')

assert C.f.__doc__ == 'f(...)\n\n'

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

