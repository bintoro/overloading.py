"""
--------------
overloading.py
--------------

Function overloading for Python 3

* Project website: https://github.com/bintoro/overloading.py
* Documentation: https://overloading.readthedocs.org/

Copyright © 2014–2016 Kalle Tuure. Released under the MIT License.

"""

__version__ = '0.5.0'

__all__ = ['overload', 'overloaded', 'overloads']



import ast
from collections import namedtuple, deque, Mapping
from functools import partial
import inspect
from itertools import chain
import re
import sys
import types

try:
    import typing
except ImportError:
    typing = None

if sys.version_info < (3, 2):
    raise RuntimeError("Module 'overloading' requires Python version 3.2 or higher.")

DEBUG = False



######
##
##  Public interface
##


def overload(func):
    """
    May be used as a shortcut for ``overloaded`` and ``overloads(f)``
    when the overloaded function `f` can be automatically identified.
    """
    if sys.version_info < (3, 3):
        raise OverloadingError("The 'overload' syntax requires Python version 3.3 or higher.")
    fn = unwrap(func)
    ensure_function(fn)
    fname = get_full_name(fn)
    if fname.find('<locals>') >= 0:
        raise OverloadingError("The 'overload' syntax cannot be used with nested functions. "
                               "Decorators must use functools.wraps().")
    try:
        return register(__registry[fname], func)
    except KeyError:
        __registry[fname] = overloaded(func)
        return __registry[fname]


def overloaded(func):
    """
    Introduces a new overloaded function and registers its first implementation.
    """
    fn = unwrap(func)
    ensure_function(fn)
    def dispatcher(*args, **kwargs):
        resolved = None
        if dispatcher.__cacheable:
            cache_key = (tuple(type(arg) for arg in args),
                         tuple(sorted((name, type(arg)) for (name, arg) in kwargs.items())))
            resolved = dispatcher.__cache.get(cache_key)
        if not resolved:
            resolved = find(dispatcher, args, kwargs)
            if resolved and dispatcher.__cacheable:
                dispatcher.__cache[cache_key] = resolved
        if resolved:
            before = dispatcher.__hooks.get('before')
            after = dispatcher.__hooks.get('after')
            if before:
                before(*args, **kwargs)
            result = resolved(*args, **kwargs)
            if after:
                after(*args, **kwargs)
            return result
        else:
            return error(dispatcher.__name__)
    dispatcher.__dict__.update(
        __functions = [],
        __hooks = {},
        __cache = {},
        __cacheable = True,
        __maxlen = 0,
    )
    for attr in ('__module__', '__name__', '__qualname__', '__doc__'):
        setattr(dispatcher, attr, getattr(fn, attr, None))
    void_implementation = is_void(fn)
    argspec = inspect.getfullargspec(fn)
    update_docstring(dispatcher, argspec, void_implementation)
    if void_implementation:
        return dispatcher
    return register(dispatcher, func)


def overloads(dispatcher, hook=None):
    """
    Returns a callable that registers its argument as an implementation
    of a previously declared overloaded function.
    """
    return partial(register, dispatcher, hook=hook)



######
##
##  Private interface
##


__registry = {}

FunctionInfo = namedtuple('FunctionInfo', 'func, argspec, sig, defaults')

_empty = object()


def register(dispatcher, func, *, hook=None):
    """
    Registers `func` as an implementation on `dispatcher`.
    """
    wrapper = None
    if isinstance(func, (classmethod, staticmethod)):
        wrapper = type(func)
        func = func.__func__
    ensure_function(func)
    if isinstance(dispatcher, (classmethod, staticmethod)):
        wrapper = None
    dp = unwrap(dispatcher)
    try:
        dp.__functions
    except AttributeError:
        raise OverloadingError("%r has not been set up as an overloaded function." % dispatcher)
    argspec = inspect.getfullargspec(unwrap(func))
    if hook:
        dp.__hooks[hook] = func
    else:
        sig_full = get_type_signature(func)
        sig_rqd = get_type_signature(func, required_only=True)
        if argspec.defaults:
            defaults = {k: v for k, v in zip(argspec.args[-len(argspec.defaults):], argspec.defaults)}
        else:
            defaults = {}
        for i, type_ in enumerate(sig_full):
            if not isinstance(type_, type):
                raise OverloadingError(
                  "Failed to overload function '{0}': parameter '{1}' has "
                  "an annotation that is not a type."
                  .format(dp.__name__, argspec.args[i]))
        for fninfo in dp.__functions:
            dup_sig = sig_cmp(sig_rqd, get_type_signature(fninfo.func, required_only=True))
            if dup_sig and bool(argspec.varargs) == bool(fninfo.argspec.varargs):
                raise OverloadingError(
                  "Failed to overload function '{0}': non-unique signature ({1})."
                  .format(dp.__name__, str.join(', ', (_repr(t) for t in dup_sig))))
        # All clear; register the function.
        dp.__functions.append(FunctionInfo(func, argspec, sig_full, defaults))
        dp.__maxlen = max(dp.__maxlen, len(sig_full))
        if typing and dp.__cacheable and any(map(is_constrained, iter_types(sig_rqd))):
            dp.__cacheable = False
    if wrapper is None:
        wrapper = lambda x: x
    if func.__name__ == dp.__name__:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return wrapper(dispatcher)
    else:
        return wrapper(func)


Match = namedtuple('Match', 'score, func, sig')

SP_ANY = 0
SP_TYPE = 200
SP_ABSTRACT = 100
SP_TYPING = 100
SP_TYPING_TUPLE = 150


def find(dispatcher, args, kwargs):
    """
    Given the arguments contained in `args` and `kwargs`, returns the best match
    from the list of implementations registered on `dispatcher`.
    """
    matches = []
    for func_index, (func, argspec, sig, defaults) in enumerate(dispatcher.__functions):
        # Filter out arguments that will be consumed by catch-all parameters
        # or by keyword-only parameters.
        if argspec.varargs:
            _args = args[:len(sig)]
        else:
            _args = args
        if argspec.varkw or argspec.kwonlyargs:
            _kwargs = {kw: kwargs[kw] for kw in argspec.args if kw in kwargs}
        else:
            _kwargs = kwargs
        kwarg_set = set(_kwargs)
        arg_count = len(_args) + len(_kwargs)
        optional_count = len(defaults)
        required_count = len(argspec.args) - optional_count
        # Consider candidate functions that satisfy basic conditions:
        # - argument count matches signature
        # - all keyword arguments are recognized.
        if not 0 <= len(argspec.args) - arg_count <= optional_count:
            continue
        if not kwarg_set <= set(argspec.args):
            continue
        args_by_key = {k: v for k, v in zip(argspec.args, _args)}
        if set(args_by_key) & kwarg_set:
            raise TypeError("%s() got multiple values for the same parameter"
                            % dispatcher.__name__)
        args_by_key.update(_kwargs)
        arg_score = arg_count # >= 0
        type_score = 0
        specificity_score = [None] * dispatcher.__maxlen
        sig_score = required_count
        var_score = -bool(argspec.varargs)
        for argname, value in args_by_key.items():
            param_pos = argspec.args.index(argname)
            if value is None and defaults.get(argname, _empty) is None:
                expected_type = type(None)
            else:
                expected_type = sig[param_pos]
            match, specificity = compare(value, expected_type)
            specificity_score[param_pos] = specificity
            if match == -1:
                break
            if match:
                type_score += 1
        else:
            score = (arg_score, type_score, specificity_score, sig_score, var_score)
            matches.append(Match(score, func, sig))
    if matches:
        matches = sorted(matches, key=lambda m: m.score, reverse=True)
        if DEBUG and len(matches) > 1:
            assert matches[0].score > matches[1].score
        return matches[0].func
    else:
        return None


def compare(value, expected_type):
    if expected_type is AnyType:
        return (0, (SP_ANY, SP_ANY))
    type_ = type(value)
    type_param = None
    if not issubclass(type_, expected_type):
        # Discard immediately on type mismatch.
        return (-1, None)
    type_specificity = SP_TYPE
    param_specificity = SP_ANY
    if typing and issubclass(expected_type, typing.Union):
        types = [t for t in expected_type.__union_params__ if issubclass(type_, t)]
        if len(types) > 1:
            types = sorted(types, key=partial(compare, value), reverse=True)
        expected_type = types[0]
    if typing and isinstance(expected_type, typing.TypingMeta):
        type_specificity = SP_TYPING
        match = False
        if issubclass(expected_type, typing.Tuple):
            type_specificity = SP_TYPING_TUPLE
            params = expected_type.__tuple_params__
            if params:
                type_param = params[0]
                if expected_type.__tuple_use_ellipsis__:
                    match = all(issubclass(type(v), params[0]) for v in value)
                elif len(value) == len(params):
                    match = all(issubclass(type(v), t) for v, t in zip(value, params))
            else:
                match = True
        elif isinstance(expected_type, typing.GenericMeta):
            for base in expected_type.__mro__:
                if base.__module__ == 'typing':
                    base_generic = first_origin(base)
                    break
            if issubclass(base_generic, typing.Mapping):
                key_param, type_param = expected_type.__parameters__
                if len(value) == 0:
                    match = True
                else:
                    k, v = next(iter(value.items()))
                    if issubclass(type(k), key_param) and issubclass(type(v), type_param):
                        match = True
            elif issubclass(base_generic, typing.Iterable):
                type_param = expected_type.__parameters__[0]
                if len(value) == 0 \
                  or issubclass(type(next(iter(value))), type_param):
                    match = True
            else:
                match = True
                if expected_type.__parameters__:
                    type_param = expected_type.__parameters__[0]
        else:
            match = True
        if not match:
            return (-1, None)
        if type_param and type_param is not AnyType:
            if isinstance(type_param, typing.TypeVar):
                param_specificity = SP_TYPING
            else:
                param_specificity = SP_TYPE
    elif inspect.isabstract(expected_type):
        type_specificity = SP_ABSTRACT
    type_specificity += len(expected_type.__mro__)
    if type_param:
        param_specificity += len(type_param.__mro__)
    return (1, (type_specificity, param_specificity))


def get_type_signature(func, *, required_only=False):
    """
    Returns a tuple of type annotations representing the call signature of `func`.
    """
    fn = unwrap(func)
    argspec = inspect.getfullargspec(fn)
    type_hints = argspec.annotations
    if typing:
        type_hints = typing.get_type_hints(fn)
    if required_only and argspec.defaults:
        params = argspec.args[:-len(argspec.defaults)]
    else:
        params = argspec.args
    return tuple(normalize_type(type_hints.get(param, AnyType)) for param in params)


def iter_types(types):
    for type_ in types:
        if type_ is AnyType:
            pass
        elif issubclass(type_, typing.Union):
            for t in iter_types(type_.__union_params__):
                yield t
        else:
            yield type_


def normalize_type(type_, _level=0):
    """
    Reduces an arbitrarily complex type declaration into something manageable.
    """
    _level += 1
    if not typing or not isinstance(type_, typing.TypingMeta) or type_ is AnyType:
        return type_
    if isinstance(type_, typing.TypeVar):
        return type_
    if issubclass(type_, typing.Union):
        if not type_.__union_params__:
            raise OverloadingError("typing.Union must be parameterized")
        return typing.Union[tuple(normalize_type(t, _level - 1) for t in type_.__union_params__)]
    if issubclass(type_, typing.Tuple):
        if _level > 1:
            return typing.Tuple
        if not type_.__tuple_params__:
            return typing.Tuple
        elif type_.__tuple_use_ellipsis__:
            return typing.Tuple[normalize_type(type_.__tuple_params__[0], _level), ...]
        else:
            return typing.Tuple[tuple(normalize_type(t, _level) for t in type_.__tuple_params__)]
    if issubclass(type_, typing.Callable):
        return typing.Callable
    if isinstance(type_, typing.GenericMeta):
        origin = type_.__origin__ or type_
        if _level == 1 and is_constrained(type_):
            return origin[tuple(normalize_type(t, _level) for t in type_.__parameters__)]
        else:
            return origin
    raise OverloadingError("%r not supported yet" % type_)


def is_constrained(type_):
    return (issubclass(type_, typing.Tuple) and type_.__tuple_params__ or
            isinstance(type_, typing.GenericMeta)
              and any(not isinstance(p, typing.TypeVar) or p.__constraints__
                      for p in type_.__parameters__))


def first_origin(type_):
    while type_.__origin__:
        type_ = type_.__origin__
    return type_


def sig_cmp(sig1, sig2):
    """
    Compares two normalized type signatures for validation purposes.
    """
    if not typing:
        if sig1 == sig2:
            return sig1
        else:
            return False
    if len(sig1) != len(sig2):
        return False
    sig = []
    for idx, (t1, t2) in enumerate(zip(sig1, sig2)):
        if t1 is AnyType and t2 is not AnyType:
            return False
        if t2 is AnyType and t1 is not AnyType:
            return False
        if t1 == t2:
            sig.append(t1)
        elif issubclass(t1, typing.Union) and issubclass(t2, typing.Union):
            common = t1.__union_set_params__ & t2.__union_set_params__
            if common:
                sig.append(next(iter(common)))
        elif issubclass(t1, typing.Union) and t2 in t1.__union_params__:
            sig.append(t2)
        elif issubclass(t2, typing.Union) and t1 in t2.__union_params__:
            sig.append(t1)
        else:
            return False
    return tuple(sig)


class AnyTypeMeta(type):
    def __subclasscheck__(self, cls):
        if not isinstance(cls, type):
            return super().__subclasscheck__(cls)
        return True


class AnyType(metaclass=AnyTypeMeta):
    pass


if typing:
    AnyType = typing.Any


class NoTypeMeta(type):
    def __subclasscheck__(self, cls):
        if not isinstance(cls, type):
            return super().__subclasscheck__(cls)
        return False


class NoType(metaclass=NoTypeMeta):
    pass


def error(name):
    """
    Raises a `TypeError` when a call to an overloaded function
    doesn't match any implementation.
    """
    raise TypeError("Invalid type or number of arguments{0}."
                    .format(" when calling '%s'" % name if name else ''))


class OverloadingError(Exception):
    """Raised during function setup when something goes wrong"""
    pass


def unwrap(func):
    while hasattr(func, '__func__'):
        func = func.__func__
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


def ensure_function(func):
    if not isinstance(func, types.FunctionType):
        raise OverloadingError("%r is not a function." % func)


def is_void(func):
    """
    Determines if a function is a void function, i.e., one whose body contains
    nothing but a docstring or an ellipsis. A void function can be used to introduce
    an overloaded function without actually registering an implementation.
    """
    try:
        source = inspect.getsource(func)
    except (OSError, IOError):
        return False
    indent = re.match(r'\s*', source).group()
    if indent:
        source = re.sub('^' + indent, '', source, flags=re.M)
    fdef = next(ast.iter_child_nodes(ast.parse(source)))
    return (
      type(fdef) is ast.FunctionDef and len(fdef.body) == 1 and
      type(fdef.body[0]) is ast.Expr and
      type(fdef.body[0].value) in {ast.Str, ast.Ellipsis})


def update_docstring(dispatcher, argspec, use_argspec):
    """
    Inserts a call signature at the beginning of the docstring on `dispatcher`.
    If `use_argspec` is true, the signature is that given by `argspec`; otherwise
    `(...)` is used.
    """
    doc = dispatcher.__doc__ or ''
    if inspect.cleandoc(doc).startswith('%s(' % dispatcher.__name__):
        return
    sig = '(...)'
    if argspec.args and argspec.args[0] in {'self', 'cls'}:
        argspec.args.pop(0)
    if use_argspec and any(argspec):
        sig = inspect.formatargspec(*argspec)
        sig = re.sub(r' at 0x[0-9a-f]{8,16}(?=>)', '', sig)
    sep = '\n' if doc.startswith('\n') else '\n\n'
    dispatcher.__doc__ = dispatcher.__name__ + sig + sep + doc


def get_full_name(obj):
    return obj.__module__ + '.' + obj.__qualname__


__subclass_check_cache = {}

def _issubclass(t1, t2, use_origin=False):
    """An enhanced version of ``issubclass()``.

    Specifying ``use_origin=True`` causes the relation to be evaluated using
    the types' origins if available. Essentially this means deparameterizing
    constrained generics back into their type variable -using forms.
    """
    cache_key = (t1, t2, use_origin)
    try:
        return __subclass_check_cache[cache_key]
    except KeyError:
        if t1 is AnyType:
            res = False
        elif t1 is NoType:
            res = True
        else:
            if use_origin:
                t1 = getattr(t1, '__origin__', None) or t1
                t2 = getattr(t2, '__origin__', None) or t2
            res = issubclass(t1, t2)
        __subclass_check_cache[cache_key] = res
        return res


def _repr(type_):
    if type_ is AnyType:
        return '<any type>'
    return repr(type_)

