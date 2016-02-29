"""
    overloading.py -- function overloading for Python 3
    Copyright: 2016 Kalle Tuure
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

if sys.version_info < (3, 2):
    raise RuntimeError("Module 'overloading' requires Python version 3.2 or higher.")


__version__ = '0.5.0'

__all__ = ['overload', 'overloaded', 'overloads']

DEBUG = False

__registry = WeakValueDictionary()


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
        cache_key = (tuple(type(arg) for arg in args),
                     tuple(sorted((name, type(arg)) for (name, arg) in kwargs.items())))
        resolved = dispatcher.__cache.get(cache_key)
        if not resolved:
            resolved = find(dispatcher, args, kwargs) or dispatcher.__default
            if resolved:
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
        sig_full = sig_regular(argspec)
        sig_rqd = sig_required(argspec)
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
            for i, param in enumerate(sig_full):
                if not inspect.isclass(param) and param is not None:
                    raise OverloadingError(
                      "Failed to overload function '{0}': parameter '{1}' has "
                      "an annotation that is not a type."
                      .format(dispatcher.__name__, argspec.args[i]))
            for f in dispatcher.__functions:
                if f[0] is dispatcher.__default:
                    continue
                duplicate = sig_cmp(sig_rqd, sig_required(f[1]))
                if duplicate:
                    msg = "non-unique signature [%s]." % \
                            str.join(', ', (type_.__name__ if type_ else '<no type>'
                                            for type_ in duplicate))
                    raise OverloadingError("Failed to overload function '{0}': {1}"
                                           .format(dispatcher.__name__, msg))
        # All clear; register the function.
        dispatcher.__functions.append((func, argspec, sig_full))
    if func.__name__ == dispatcher.__name__:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return wrapper(dispatcher)
    else:
        return wrapper(func)


Match = namedtuple('Match', 'score, func')

def find(dispatcher, args, kwargs):
    matches = [Match((-1,), None)]
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
            expected_type = argspec.annotations.get(argname)
            if expected_type:
                if isinstance(value, expected_type):
                    type_score += 1
                    if type(value) is expected_type:
                        exact_score += 1
                    # Compute a rank for how close the match is in terms of
                    # the type hierarchy.
                    try:
                        mro_index = type(value).__mro__.index(expected_type)
                    except ValueError:
                        # The expected type was not part of the MRO. This can only
                        # happen when the type has a metaclass with a custom
                        # implementation of `__instancecheck__`. For now, deal with
                        # it by simply giving the match a low rank.
                        mro_index = 99
                    mro_scores[argspec.args.index(argname)] = -mro_index
                else:
                    # Discard immediately on type mismatch.
                    arg_score = -2
                    break
        score = (arg_score, type_score, exact_score, mro_scores, sig_score)
        matches.append(Match(score, func))
    matches = sorted(matches, key=lambda m: m.score, reverse=True)
    top_matches = [m for m in matches if m.score == matches[0].score]
    # print(tuple((m.func.__name__, m.score) for m in matches if m.func))
    if len(top_matches) > 1:
        # Give priority to non-default functions.
        top_matches = [m for m in top_matches if m.func is not dispatcher.__default]
    if DEBUG:
        assert len(top_matches) == 1
    return top_matches[0].func


def sig_regular(argspec):
    return tuple(argspec.annotations.get(arg) for arg in argspec.args)


def sig_required(argspec):
    return tuple(argspec.annotations.get(arg) for arg in required_args(argspec))


def required_args(argspec):
    if argspec.defaults:
        return argspec.args[:-len(argspec.defaults)]
    else:
        return argspec.args


def sig_cmp(sig1, sig2):
    """
    Compare two parameter signatures.

    The comparator considers all abstract base classes to be equal. This implies
    that two function signatures may not contain an ABC at the same parameter
    position if that is their only difference. Such signatures will be considered
    duplicates.

    If the signatures represent a match, return the shared signature.
    On mismatch return `False`.
    """
    sig = []
    if len(sig1) != len(sig2):
        return False
    for idx, (type1, type2) in enumerate(zip(sig1, sig2)):
        if type1 is type2 \
          or inspect.isabstract(type1) and inspect.isabstract(type2):
            sig.append(type1)
        else:
            return False
    return tuple(sig)


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

