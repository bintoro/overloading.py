"""
    overloading.py -- function overloading for Python 3
    Copyright: 2015 Kalle Tuure
    License: MIT
"""

from collections import namedtuple
from functools import partial, wraps
import inspect
import sys

if sys.version_info[0] < 3:
    raise Exception("Module 'overloading' requires Python version 3.0 or higher.")

__all__ = ['overloaded', 'overloads']


def overloaded(func):
    name = getattr(func, '__name__', None)
    def dispatcher(*args, **kwargs):
        default = dispatcher.default or partial(error, name)
        resolved = find(dispatcher, *args, **kwargs) or default
        before = dispatcher.hooks.get('before', no_op)
        after = dispatcher.hooks.get('after', no_op)
        before(*args, **kwargs)
        result = resolved(*args, **kwargs)
        after(*args, **kwargs)
        return result
    dispatcher.functions = []
    dispatcher.hooks = {}
    dispatcher.default = None
    dispatcher.name = name
    return register(dispatcher, func)


def overloads(dispatcher, hook=None):
    return partial(register, dispatcher, hook=hook)


def register(dispatcher, func, hook=None):
    if isinstance(dispatcher, (classmethod, staticmethod)):
        dispatcher = dispatcher.__func__
    if isinstance(func, (classmethod, staticmethod)):
        name = dispatcher.name or func.__func__.__name__
        raise OverloadingError("Failed to overload function '{0}': "
                               "overloading must occur before '{1}' setup." \
                               .format(name, type(func).__name__))
    argspec = inspect.getfullargspec(getattr(func, '__wrapped__', func))
    if hook:
        dispatcher.hooks[hook] = func
    else:
        sig_full = sig_regular(argspec)
        sig_req = sig_required(argspec)
        if argspec.varargs:
            # The presence of a catch-all variable for positional arguments
            # indicates that this function should be treated as the fallback.
            if dispatcher.default:
                raise OverloadingError(
                  "Failed to overload function '{0}': multiple function definitions "
                  "contain a catch-all variable for positional arguments." \
                  .format(dispatcher.name))
            dispatcher.default = func
        else:
            for i, param in enumerate(sig_full):
                if not inspect.isclass(param) and param is not None:
                    raise OverloadingError(
                      "Failed to overload function '{0}': parameter '{1}' has "
                      "an annotation that is not a type."\
                      .format(dispatcher.name, argspec.args[i]))
            for f in dispatcher.functions:
                if f[0] is dispatcher.default:
                    continue
                # result = sig_cmp(sig_req, sig_required(f[1]))
                result = sig_req if sig_req == sig_required(f[1]) else False
                if result is not False:
                    raise OverloadingError(
                      "Failed to overload function '{0}': non-unique signature [{1}]." \
                      .format(dispatcher.name,
                              str.join(', ', (type_.__name__ if type_ else '<no type>'
                                              for type_ in result))))
        # All clear; register the function.
        dispatcher.functions.append((func, argspec, sig_full))
    if func.__name__ == dispatcher.name:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return dispatcher
    else:
        return func


Match = namedtuple('Match', 'score, func')


def find(dispatcher, *args, **kwargs):
    matches = [Match((-1,), None)]
    for func, argspec, sig in dispatcher.functions:
        # Filter out keyword arguments that will be consumed by a catch-all parameter
        # or by keyword-only parameters.
        if argspec.varkw:
            true_kwargs = {kw: kwargs[kw] for kw in argspec.args if kw in kwargs}
        else:
            true_kwargs = kwargs
            for kw in argspec.kwonlyargs:
                true_kwargs.pop(kw, None)
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
        exact_positions = [0] * arg_count
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
                        exact_positions[argspec.args.index(argname)] = 1
                else:
                    # Discard immediately on type mismatch.
                    arg_score = -2
                    break
        score = (arg_score, type_score, exact_score, exact_positions, sig_score)
        matches.append(Match(score, func))
    matches = sorted(matches, key=lambda m: m.score, reverse=True)
    top_matches = [m for m in matches if m.score == matches[0].score]
    if len(top_matches) > 1:
        # Give priority to non-default functions.
        top_matches = [m for m in top_matches if m.func is not dispatcher.default]
    if len(top_matches) > 1:
        raise OverloadingError("Could not resolve the most specific match. "
                               "This should not happen. Please file a bug at "
                               "https://github.com/bintoro/overloading.py/issues.")
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


def error(name, *args, **kwargs):
    raise TypeError("Invalid type or number of arguments{0}."\
                    .format(" when calling '%s'" % name if name else ''))


def no_op(*args, **kwargs):
    pass


class OverloadingError(Exception):
    pass

