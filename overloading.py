"""
    overloading.py -- function overloading for Python 3
    Copyright: 2015 Kalle Tuure
    License: MIT
"""

from collections import namedtuple
from functools import partial, wraps
from itertools import chain
import inspect
import sys

if sys.version_info[0] < 3:
    raise Exception("Module 'overloading' requires Python version 3.0 or higher.")

__all__ = ['overloaded', 'overloads']


Match = namedtuple('Match', 'score, func, sig')


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
        sig = required_args_sig(argspec)
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
            for i, param in enumerate(sig):
                if not inspect.isclass(param) and param is not None:
                    raise OverloadingError(
                      "Failed to overload function '{0}': parameter '{1}' has "
                      "an annotation that is not a type."\
                      .format(dispatcher.name, argspec.args[i]))
            for f in dispatcher.functions:
                if f[0] is dispatcher.default:
                    continue
                result = sig_cmp(sig, required_args_sig(f[1]))
                if result is not False:
                    raise OverloadingError(
                      "Failed to overload function '{0}': non-unique signature [{1}]." \
                      .format(dispatcher.name,
                              str.join(', ', (type_.__name__ if type_ else '<no type>'
                                              for type_ in result))))
        # All clear; register the function.
        dispatcher.functions.append((func, argspec, sig))
    if func.__name__ == dispatcher.name:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return dispatcher
    else:
        return func


def find(dispatcher, *args, **kwargs):
    matches = [Match((-1, 0, 0), None, None)]
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
        sig_score = required_count
        args_by_key = {argspec.args[idx]: val for (idx, val) in enumerate(args)}
        for argname, value in chain(args_by_key.items(), true_kwargs.items()):
            expected_type = argspec.annotations.get(argname)
            if expected_type:
                if isinstance(value, expected_type):
                    type_score += 1
                else:
                    # Discard immediately on type mismatch.
                    arg_score, type_score, sig_score = -2, 0, 0
                    break
        score = (arg_score, type_score, sig_score)
        matches.append(Match(score, func, sig))
    matches = sorted(matches, key=lambda m: m.score, reverse=True)
    top_matches = [m for m in matches if m.score == matches[0].score]
    if len(top_matches) > 1:
        # Give priority to non-default functions.
        top_matches = [m for m in top_matches if m.func is not dispatcher.default]
    if len(top_matches) > 1:
        # The only situation where a tie should occur is if there's a parameter that
        # expects the type X in one implementation and a subclass of X in another.
        sig_len = min(len(m.sig) for m in top_matches)
        for i in range(sig_len):
            for match in top_matches:
                issubclass_all = tuple(issubclass(match.sig[i], m.sig[i])
                                       for m in top_matches if m.sig[i])
                if issubclass_all and all(issubclass_all):
                    return match.func
        raise OverloadingError("Could not resolve the most specific match. "
                               "This should not happen. Please file a bug at "
                               "https://github.com/bintoro/overloading.py/issues.")
    return top_matches[0].func


def required_args(argspec):
    if argspec.defaults:
        return argspec.args[:-len(argspec.defaults)]
    else:
        return argspec.args


def required_args_sig(argspec):
    return tuple(argspec.annotations.get(arg) for arg in required_args(argspec))


def sig_cmp(sig1, sig2):
    """
    Compare two parameter signatures. If they match, return the shared signature.
    On mismatch return `False`. Inheritance can serve as a distinguishing factor
    for up to one parameter, but for subsequent occurrences the comparator considers 
    a class and its subclass to be equal. The returned signature is normalized to always
    include the superclass.
    """
    sig = []
    subclass_count = 0
    if len(sig1) != len(sig2):
        return False
    for type1, type2 in zip(sig1, sig2):
        if type1 is type2:
            sig.append(type1)
        elif type1 and type2 \
          and (issubclass(type1, type2) or issubclass(type2, type1)):
            sig.append(type1 if type1 in type2.__mro__ else type2)
            subclass_count += 1
        else:
            return False
    if subclass_count == 1:
        return False
    else:
        return tuple(sig)


def error(name, *args, **kwargs):
    raise TypeError("Invalid type or number of arguments when calling overloaded "
                    "function{0}.".format(" '%s'" % name if name else ''))


def no_op(*args, **kwargs):
    pass


class OverloadingError(Exception):
    pass

