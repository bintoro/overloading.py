"""
    overloading.py -- function overloading for Python 3
    Copyright: 2014–2016 Kalle Tuure
    License: MIT
"""

import ast
from collections import namedtuple
from functools import partial
import inspect
import re
import sys
import types
from weakref import WeakValueDictionary

try:
    import typing
except ImportError:
    typing = None

if sys.version_info < (3, 2):
    raise RuntimeError("Module 'overloading' requires Python version 3.2 or higher.")


__version__ = '0.5.0'

__all__ = ['overload', 'overloaded', 'overloads']

DEBUG = False

__registry = WeakValueDictionary()

_empty = object()


def overload(func):
    if sys.version_info < (3, 3):
        raise OverloadingError("The 'overload' syntax requires Python version 3.3 or higher.")
    if isinstance(func, (classmethod, staticmethod)):
        true_func = func.__func__
    else:
        true_func = func
    true_func = unwrap(true_func)
    ensure_function(true_func)
    fname = get_full_name(true_func)
    if fname.find('<locals>') >= 0:
        raise OverloadingError("The 'overload' syntax cannot be used with nested functions. "
                               "Decorators must use functools.wraps().")
    if fname in __registry:
        return register(__registry[fname], func)
    else:
        __registry[fname] = overloaded(func)
        return __registry[fname]


def overloaded(func):
    if isinstance(func, (classmethod, staticmethod)):
        true_func = func.__func__
    else:
        true_func = func
    true_func = unwrap(true_func)
    ensure_function(true_func)
    def dispatcher(*args, **kwargs):
        resolved = None
        if dispatcher.__cacheable:
            cache_key = (tuple(type(arg) for arg in args),
                         tuple(sorted((name, type(arg)) for (name, arg) in kwargs.items())))
            resolved = dispatcher.__cache.get(cache_key)
        if not resolved:
            resolved = find(dispatcher, args, kwargs) or dispatcher.__default
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
        __default = None,
        __cache = {},
        __cacheable = True
    )
    for attr in ('__module__', '__name__', '__qualname__', '__doc__'):
        setattr(dispatcher, attr, getattr(true_func, attr, None))
    void_implementation = is_void(true_func)
    argspec = inspect.getfullargspec(true_func)
    update_docstring(dispatcher, argspec, void_implementation)
    if void_implementation:
        return dispatcher
    return register(dispatcher, func)


def overloads(dispatcher, hook=None):
    return partial(register, dispatcher, hook=hook)


def register(dispatcher, func, hook=None):
    wrapper = lambda x: x
    if isinstance(func, (classmethod, staticmethod)):
        wrapper = type(func)
        func = func.__func__
    if isinstance(dispatcher, (classmethod, staticmethod)):
        dispatcher = dispatcher.__func__
    try:
        dispatcher.__functions
    except AttributeError:
        raise OverloadingError("%r has not been set up as an overloaded function."
                               % dispatcher)
    ensure_function(func)
    argspec = inspect.getfullargspec(unwrap(func))
    if hook:
        dispatcher.__hooks[hook] = func
    else:
        sig_full = get_type_signature(func)
        sig_rqd = get_type_signature(func, required_only=True)
        if argspec.varargs:
            # The presence of a catch-all variable for positional arguments
            # indicates that this function should be treated as the fallback.
            if dispatcher.__default:
                raise OverloadingError(
                  "Failed to overload function '{0}': multiple function definitions "
                  "contain a catch-all variable for positional arguments."
                  .format(dispatcher.__name__))
            dispatcher.__default = func
        else:
            for i, type_ in enumerate(sig_full):
                if not isinstance(type_, type) and type_ not in (_empty, None):
                    raise OverloadingError(
                      "Failed to overload function '{0}': parameter '{1}' has "
                      "an annotation that is not a type."
                      .format(dispatcher.__name__, argspec.args[i]))
            for f in dispatcher.__functions:
                if f[0] is dispatcher.__default:
                    continue
                if sig_cmp(sig_rqd, get_type_signature(f[0], required_only=True)):
                    msg = "non-unique signature [%s]." % \
                        str.join(', ', (repr(t) if t is not _empty else '<any type>'
                                        for t in sig_rqd))
                    raise OverloadingError("Failed to overload function '{0}': {1}"
                                           .format(dispatcher.__name__, msg))
        # All clear; register the function.
        dispatcher.__functions.append((func, argspec, sig_full))
        if typing and any((isinstance(t, typing.TypingMeta) for t in sig_rqd)):
            dispatcher.__cacheable = False
    if func.__name__ == dispatcher.__name__:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return wrapper(dispatcher)
    else:
        return wrapper(func)


Match = namedtuple('Match', 'score, func, sig')

def find(dispatcher, args, kwargs):
    matches = [Match((-1,), None, None)]
    for func, argspec, sig in dispatcher.__functions:
        # Filter out keyword arguments that will be consumed by a catch-all parameter
        # or by keyword-only parameters.
        if argspec.varkw or argspec.kwonlyargs:
            true_kwargs = {kw: kwargs[kw] for kw in argspec.args if kw in kwargs}
        else:
            true_kwargs = kwargs
        arg_count = len(args) + len(true_kwargs)
        optional_count = len(argspec.defaults) if argspec.defaults else 0
        required_count = len(argspec.args) - optional_count
        # Consider candidate functions that satisfy basic conditions:
        # - argument count matches signature
        # - all keyword arguments are recognized.
        if not (0 <= len(argspec.args) - arg_count <= optional_count):
            continue
        if not set(true_kwargs) <= set(argspec.args):
            continue
        arg_score = arg_count # >= 0
        type_score = 0
        exact_score = 0
        mro_scores = [0] * len(sig)
        sig_score = required_count
        args_by_key = {argspec.args[idx]: val for (idx, val) in enumerate(args)}
        args_by_key.update(true_kwargs)
        for argname, value in args_by_key.items():
            match = False
            param_pos = argspec.args.index(argname)
            expected_type = sig[param_pos]
            if expected_type is not _empty:
                _type = type(value)
                if issubclass(_type, expected_type):
                    if typing and isinstance(expected_type, typing.TypingMeta):
                        if issubclass(expected_type, typing.Union):
                            match = True
                            types = [t for t in expected_type.__union_params__ if issubclass(_type, t)]
                            if len(types) > 1:
                                expected_type = find_most_derived(types)
                            else:
                                expected_type = types[0]
                        elif issubclass(expected_type, typing.Tuple):
                            params = expected_type.__tuple_params__
                            if expected_type.__tuple_use_ellipsis__:
                                match = all(issubclass(type(v), params[0]) for v in value)
                            elif len(value) == len(params):
                                match = all(issubclass(type(v), t) for v, t in zip(value, params))
                        elif issubclass(expected_type, typing.Iterable):
                            if issubclass(type(next(iter(value))), expected_type.__parameters__[0]):
                                match = True
                        else:
                            match = True
                        if not match:
                            arg_score = -2
                            break
                    else:
                        match = True
                    if match:
                        type_score += 1
                    if _type is expected_type:
                        exact_score += 1
                    # Compute a rank for how close the match is in terms of
                    # the type hierarchy.
                    try:
                        mro_index = _type.__mro__.index(expected_type)
                    except ValueError:
                        # The expected type was not part of the MRO. This can only
                        # happen when the declared type has a metaclass with a custom
                        # implementation of `__subclasscheck__()`. The position is
                        # given a rank of -99, and a possible tie is resolved later.
                        mro_index = 99
                    mro_scores[param_pos] = -mro_index
                else:
                    # Discard immediately on type mismatch.
                    arg_score = -2
                    break
        score = (arg_score, type_score, exact_score, mro_scores, sig_score)
        matches.append(Match(score, func, sig))
    matches = sorted(matches, key=lambda m: m.score, reverse=True)
    matches = [m for m in matches if m.score == matches[0].score]
    # print(tuple((m.func.__name__, m.score) for m in matches if m.func))
    if len(matches) > 1:
        # A tie may occur because some of the argument matches are not due to concrete
        # inheritance, i.e., when the declared types have overridden `__subclasscheck__()`.
        # We'll establish a ranking among the declared types at each applicable parameter
        # position, and the function whose signature produces a unique most derived type
        # at the earliest position wins.
        type_matrix = list(filter(bool,
                        ([ (match_idx, match.sig[param_pos])
                           for param_pos, mro_score in enumerate(match.score[3])
                           if mro_score == -99
                         ] for match_idx, match in enumerate(matches))))
        if type_matrix:
            match_indices = set(range(len(type_matrix)))
            for types_ in zip(*type_matrix):
                # We're iterating over argument positions.
                # Elements in `types_` are (<match index>, <type>) tuples.
                match_indices &= set([t[0] for t in find_most_derived(types_, index=1)])
                if len(match_indices) == 1:
                    break
            matches = [matches[i] for i in match_indices]
    if len(matches) > 1:
        # Give priority to non-default functions.
        matches = [m for m in matches if m.func is not dispatcher.__default]
    if DEBUG:
        assert len(matches) == 1, [(m.sig, m.score) for m in matches]
    return matches[0].func


def get_type_signature(func, *, required_only=False):
    """
    Returns a tuple of type annotations representing the call signature of `func`.
    """
    func = unwrap(func)
    argspec = inspect.getfullargspec(func)
    type_hints = argspec.annotations
    if typing:
        type_hints = typing.get_type_hints(func)
    if required_only and argspec.defaults:
        params = argspec.args[:-len(argspec.defaults)]
    else:
        params = argspec.args
    return tuple(normalize_type(type_hints.get(param, _empty)) for param in params)


def normalize_type(type_, _level=0):
    """Reduces an arbitrarily complex type declaration into something manageable."""
    _level += 1
    if not typing or not isinstance(type_, typing.TypingMeta) or type_ is typing.Any:
        return type_
    if isinstance(type_, typing.TypeVar):
        return type_
    if issubclass(type_, typing.Union):
        return typing.Union[tuple(normalize_type(t, _level) for t in type_.__union_params__)]
    if issubclass(type_, typing.Tuple):
        if _level > 1:
            return typing.Tuple
        if type_.__tuple_use_ellipsis__:
            return typing.Tuple[normalize_type(type_.__tuple_params__[0], _level), ...]
        else:
            return typing.Tuple[tuple(normalize_type(t, _level) for t in type_.__tuple_params__)]
    if issubclass(type_, typing.Callable):
        return typing.Callable
    if isinstance(type_, typing.GenericMeta):
        origin = type_.__origin__ or type_
        params = type_.__parameters__
        if issubclass(type_, typing.Iterable) and len(params) == 1 \
          and _level == 1:
            return origin[normalize_type(params[0], _level)]
        else:
            return origin
    raise OverloadingError("%r not supported yet" % type_)


def sig_cmp(sig1, sig2):
    """
    Compares two normalized type signatures for validation purposes.
    """
    return sig1 == sig2


def error(name):
    raise TypeError("Invalid type or number of arguments{0}."
                    .format(" when calling '%s'" % name if name else ''))


class OverloadingError(Exception):
    pass


def unwrap(func):
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


def ensure_function(func):
    if not isinstance(func, types.FunctionType):
        raise OverloadingError("%r is not a function." % func)


def is_void(func):
    try:
        source = inspect.getsource(func)
    except (OSError, IOError):
        return False
    indent = re.match('\s*', source).group()
    if indent:
        source = re.sub('^' + indent, '', source, flags=re.M)
    fdef = next(ast.iter_child_nodes(ast.parse(source)))
    if (
      type(fdef) is ast.FunctionDef and len(fdef.body) == 1 and
      type(fdef.body[0]) is ast.Expr and
      type(fdef.body[0].value) in {ast.Str, ast.Ellipsis}):
        return True
    else:
        return False


def update_docstring(dispatcher, argspec, use_argspec):
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


def find_most_derived(items, index=None):
    """Finds the most derived type in `items`.

    `items` may also consist of tuples, in which case `index` must indicate
    the position of the type within each tuple.
    """
    best = object
    if index is None:
        for type_ in items:
            if type_ is not best and issubclass(type_, best):
                best = type_
        return best
    else:
        result = []
        for e in items:
            type_ = e[index]
            if issubclass(type_, best):
                if type_ is not best:
                    result = []
                    best = type_
                result.append(e)
        return result

