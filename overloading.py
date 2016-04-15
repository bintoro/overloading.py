"""
--------------
overloading.py
--------------

Function overloading for Python 3

* Project repository: https://github.com/bintoro/overloading.py
* Documentation: https://overloading.readthedocs.org/

Copyright © 2014–2016 Kalle Tuure. Released under the MIT License.

"""

__version__ = '0.5.0'

__all__ = ['overload', 'overloaded', 'overloads']



import ast
from collections import Counter, defaultdict, namedtuple
from functools import partial, reduce
import inspect
from itertools import chain
import operator
import re
import sys
from types import FunctionType

try:
    import typing
except ImportError:
    typing = None

if sys.version_info < (3, 2):
    raise ImportError("Module 'overloading' requires Python version 3.2 or higher.")

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
        if dispatcher.__complex_parameters:
            cache_key_pos = []
            cache_key_kw = []
            for argset in (0, 1) if kwargs else (0,):
                if argset == 0:
                    arg_pairs = enumerate(args)
                    complexity_mapping = dispatcher.__complex_positions
                else:
                    arg_pairs = kwargs.items()
                    complexity_mapping = dispatcher.__complex_parameters
                for id, arg in arg_pairs:
                    type_ = type(arg)
                    element_type = None
                    if id in complexity_mapping:
                        try:
                            element = next(iter(arg))
                        except TypeError:
                            pass
                        except StopIteration:
                            element_type = _empty
                        else:
                            complexity = complexity_mapping[id]
                            if complexity & 8 and isinstance(arg, tuple):
                                element_type = tuple(type(el) for el in arg)
                            elif complexity & 4 and hasattr(arg, 'keys'):
                                element_type = (type(element), type(arg[element]))
                            else:
                                element_type = type(element)
                    if argset == 0:
                        cache_key_pos.append((type_, element_type))
                    else:
                        cache_key_kw.append((id, type_, element_type))
        else:
            cache_key_pos = (type(arg) for arg in args)
            cache_key_kw = ((name, type(arg)) for (name, arg) in kwargs.items()) if kwargs else None

        cache_key = (tuple(cache_key_pos),
                     tuple(sorted(cache_key_kw)) if kwargs else None)

        try:
            resolved = dispatcher.__cache[cache_key]
        except KeyError:
            resolved = find(dispatcher, args, kwargs)
            if resolved:
                dispatcher.__cache[cache_key] = resolved
        if resolved:
            before = dispatcher.__hooks['before']
            after = dispatcher.__hooks['after']
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
        __hooks = {'before': None, 'after': None},
        __cache = {},
        __complex_positions = {},
        __complex_parameters = {},
        __maxlen = 0,
    )
    for attr in ('__module__', '__name__', '__qualname__', '__doc__'):
        setattr(dispatcher, attr, getattr(fn, attr, None))
    if is_void(fn):
        update_docstring(dispatcher, fn)
        return dispatcher
    else:
        update_docstring(dispatcher)
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

FunctionInfo = namedtuple('FunctionInfo', ('func', 'signature'))

Signature = namedtuple('Signature', ('parameters', 'types', 'complexity', 'defaults', 'required',
                                     'has_varargs', 'has_varkw', 'has_kwonly'))

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
    fn = unwrap(func)
    if hook:
        dp.__hooks[hook] = func
    else:
        signature = get_signature(fn)
        for i, type_ in enumerate(signature.types):
            if not isinstance(type_, type):
                raise OverloadingError(
                  "Failed to overload function '{0}': parameter '{1}' has "
                  "an annotation that is not a type."
                  .format(dp.__name__, signature.parameters[i]))
        for fninfo in dp.__functions:
            dup_sig = sig_cmp(signature, fninfo.signature)
            if dup_sig and signature.has_varargs == fninfo.signature.has_varargs:
                raise OverloadingError(
                  "Failed to overload function '{0}': non-unique signature ({1})."
                  .format(dp.__name__, str.join(', ', (_repr(t) for t in dup_sig))))
        # All clear; register the function.
        dp.__functions.append(FunctionInfo(func, signature))
        dp.__cache.clear()
        dp.__maxlen = max(dp.__maxlen, len(signature.parameters))
        if typing:
            # For each parameter position and name, compute a bitwise union of complexity
            # values over all registered signatures. Retain the result for parameters where
            # a nonzero value occurs at least twice and at least one of those values is >= 2.
            # Such parameters require deep type-checking during function resolution.
            position_values = defaultdict(lambda: 0)
            keyword_values = defaultdict(lambda: 0)
            position_counter = Counter()
            keyword_counter = Counter()
            for fninfo in dp.__functions:
                sig = fninfo.signature
                complex_positions = {i: v for i, v in enumerate(sig.complexity) if v}
                complex_keywords = {p: v for p, v in zip(sig.parameters, sig.complexity) if v}
                for i, v in complex_positions.items():
                    position_values[i] |= v
                for p, v in complex_keywords.items():
                    keyword_values[p] |= v
                position_counter.update(complex_positions.keys())
                keyword_counter.update(complex_keywords.keys())
            dp.__complex_positions = {
                i: v for i, v in position_values.items() if v >= 2 and position_counter[i] > 1}
            dp.__complex_parameters = {
                p: v for p, v in keyword_values.items() if v >= 2 and keyword_counter[p] > 1}
    if wrapper is None:
        wrapper = lambda x: x
    if func.__name__ == dp.__name__:
        # The returned function is going to be bound to the invocation name
        # in the calling scope, so keep returning the dispatcher.
        return wrapper(dispatcher)
    else:
        return wrapper(func)


Match = namedtuple('Match', 'score, func, sig')

SP_REGULAR = 5
SP_ABSTRACT = 4
SP_TYPING = 3
SP_GENERIC = 2


def find(dispatcher, args, kwargs):
    """
    Given the arguments contained in `args` and `kwargs`, returns the best match
    from the list of implementations registered on `dispatcher`.
    """
    matches = []
    full_args = args
    full_kwargs = kwargs
    for func, sig in dispatcher.__functions:
        params = sig.parameters
        param_count = len(params)
        # Filter out arguments that will be consumed by catch-all parameters
        # or by keyword-only parameters.
        if sig.has_varargs:
            args = full_args[:param_count]
        else:
            args = full_args
        if sig.has_varkw or sig.has_kwonly:
            kwargs = {kw: full_kwargs[kw] for kw in params if kw in full_kwargs}
        else:
            kwargs = full_kwargs
        kwarg_set = set(kwargs)
        arg_count = len(args) + len(kwargs)
        optional_count = len(sig.defaults)
        required_count = param_count - optional_count
        # Consider candidate functions that satisfy basic conditions:
        # - argument count matches signature
        # - all keyword arguments are recognized.
        if not 0 <= param_count - arg_count <= optional_count:
            continue
        if kwargs and not kwarg_set <= set(params):
            continue
        if kwargs and args and kwarg_set & set(params[:len(args)]):
            raise TypeError("%s() got multiple values for the same parameter"
                            % dispatcher.__name__)
        arg_score = arg_count # >= 0
        type_score = 0
        specificity_score = [None] * dispatcher.__maxlen
        sig_score = required_count
        var_score = -sig.has_varargs
        indexed_kwargs = ((params.index(k), v) for k, v in kwargs.items()) if kwargs else ()
        for param_pos, value in chain(enumerate(args), indexed_kwargs):
            param_name = params[param_pos]
            if value is None and sig.defaults.get(param_name, _empty) is None:
                expected_type = type(None)
            else:
                expected_type = sig.types[param_pos]
            specificity = compare(value, expected_type)
            if specificity[0] == -1:
                break
            specificity_score[param_pos] = specificity
            type_score += 1
        else:
            score = (arg_score, type_score, specificity_score, sig_score, var_score)
            matches.append(Match(score, func, sig))
    if matches:
        if len(matches) > 1:
            matches.sort(key=lambda m: m.score, reverse=True)
            if DEBUG:
                assert matches[0].score > matches[1].score
        return matches[0].func
    else:
        return None


def compare(value, expected_type):
    if expected_type is AnyType:
        return (0,)
    type_ = type(value)
    if not issubclass(type_, expected_type):
        # Discard immediately on type mismatch.
        return (-1,)
    type_tier = SP_REGULAR
    type_specificity = 0
    param_specificity = 0
    mro_rank = 0
    params = None
    if typing and isinstance(expected_type, typing.UnionMeta):
        types = [t for t in expected_type.__union_params__ if issubclass(type_, t)]
        if len(types) > 1:
            return max(map(partial(compare, value), types))
        else:
            expected_type = types[0]
    if typing and isinstance(expected_type, (typing.TypingMeta, GenericWrapperMeta)):
        type_tier = SP_TYPING
        match = False
        if isinstance(expected_type, typing.TupleMeta):
            params = expected_type.__tuple_params__
            if params:
                if expected_type.__tuple_use_ellipsis__:
                    match = len(value) == 0 or issubclass(type(value[0]), params[0])
                else:
                    match = len(value) == len(params) and \
                            all(issubclass(type(v), t) for v, t in zip(value, params))
                    param_specificity = 100
            else:
                match = True
        elif isinstance(expected_type, GenericWrapperMeta):
            type_tier = SP_GENERIC
            type_specificity = len(expected_type.type.__mro__)
            interface = expected_type.interface
            params = expected_type.parameters
            if expected_type.complexity > 1:
                # Type-check the contents.
                if interface is typing.Mapping:
                    if len(value) == 0:
                        match = True
                    else:
                        key = next(iter(value))
                        item_types = (type(key), type(value[key]))
                elif interface is typing.Iterable:
                    try:
                        item_types = (type(next(iter(value))),)
                    except StopIteration:
                        match = True
                else:
                    # Type-checking not implemented.
                    match = True
                if not match:
                    type_vars = expected_type.type_vars
                    for item_type, param, type_var in zip(item_types, params, type_vars):
                        if isinstance(param, typing.TypeVar):
                            type_var = param
                            if type_var.__constraints__:
                                param = type_var.__constraints__
                                direct_match = item_type in param
                            elif type_var.__bound__:
                                param = type_var.__bound__
                                direct_match = item_type is param
                            else:
                                direct_match = True
                        elif param is AnyType:
                            direct_match = True
                        else:
                            direct_match = item_type is param
                        match = direct_match or \
                                type_var.__covariant__ and issubclass(item_type, param) or \
                                type_var.__contravariant__ and issubclass(param, item_type)
                        if not match:
                            break
            else:
                # No constrained parameters
                match = True
        else:
            match = True
        if not match:
            return (-1,)
        if params:
            param_specificity += (sum(len(p.__mro__) for p in params if p is not AnyType)
                                  / len(params))
    if inspect.isabstract(expected_type):
        type_tier = SP_ABSTRACT
    try:
        mro_rank = 100 - type_.__mro__.index(expected_type)
    except ValueError:
        pass
    if type_specificity == 0:
        type_specificity = len(expected_type.__mro__)
    if params:
        return (mro_rank, type_tier, type_specificity, param_specificity)
    else:
        return (mro_rank, type_tier, type_specificity)


def get_signature(func):
    """
    Gathers information about the call signature of `func`.
    """
    code = func.__code__

    # Names of regular parameters
    parameters = tuple(code.co_varnames[:code.co_argcount])

    # Flags
    has_varargs = bool(code.co_flags & inspect.CO_VARARGS)
    has_varkw = bool(code.co_flags & inspect.CO_VARKEYWORDS)
    has_kwonly = bool(code.co_kwonlyargcount)

    # A mapping of parameter names to default values
    default_values = func.__defaults__ or ()
    defaults = dict(zip(parameters[-len(default_values):], default_values))

    # Type annotations for all parameters
    type_hints = typing.get_type_hints(func) if typing else func.__annotations__
    types = tuple(normalize_type(type_hints.get(param, AnyType)) for param in parameters)

    # Type annotations for required parameters
    required = types[:-len(defaults)] if defaults else types

    # Complexity
    complexity = tuple(map(type_complexity, types)) if typing else None

    return Signature(parameters, types, complexity, defaults, required,
                     has_varargs, has_varkw, has_kwonly)


def iter_types(types):
    for type_ in types:
        if type_ is AnyType:
            pass
        elif issubclass(type_, typing.Union):
            for t in iter_types(type_.__union_params__):
                yield t
        else:
            yield type_


def normalize_type(type_, level=0):
    """
    Reduces an arbitrarily complex type declaration into something manageable.
    """
    if not typing or not isinstance(type_, typing.TypingMeta) or type_ is AnyType:
        return type_
    if isinstance(type_, typing.TypeVar):
        if type_.__constraints__ or type_.__bound__:
            return type_
        else:
            return AnyType
    if issubclass(type_, typing.Union):
        if not type_.__union_params__:
            raise OverloadingError("typing.Union must be parameterized")
        return typing.Union[tuple(normalize_type(t, level) for t in type_.__union_params__)]
    if issubclass(type_, typing.Tuple):
        params = type_.__tuple_params__
        if level > 0 or params is None:
            return typing.Tuple
        elif type_.__tuple_use_ellipsis__:
            return typing.Tuple[normalize_type(params[0], level + 1), ...]
        else:
            return typing.Tuple[tuple(normalize_type(t, level + 1) for t in params)]
    if issubclass(type_, typing.Callable):
        return typing.Callable
    if isinstance(type_, typing.GenericMeta):
        base = find_base_generic(type_)
        if base is typing.Generic:
            return type_
        else:
            return GenericWrapper(type_, base, level > 0)
    raise OverloadingError("%r not supported yet" % type_)


class GenericWrapperMeta(type):

    def __new__(mcs, name, bases, attrs, type_=None, base=None, simplify=False):
        cls = super().__new__(mcs, name, bases, attrs)
        if type_ is None:
            return cls
        if base is None:
            base = find_base_generic(type_)
        if simplify:
            type_ = first_origin(type_)
        cls.type = type_
        cls.base = base
        if issubclass(base, typing.Mapping):
            cls.interface = typing.Mapping
        elif issubclass(base, typing.Iterable):
            cls.interface = typing.Iterable
        else:
            cls.interface = None
        cls.derive_configuration()
        cls.complexity = type_complexity(cls)
        return cls

    def __init__(cls, *_):
        pass

    def __call__(cls, type_, base=None, simplify=False):
        return cls.__class__(cls.__name__, (), {}, type_, base, simplify)

    def __eq__(cls, other):
        if isinstance(other, GenericWrapperMeta):
            return cls.type == other.type
        elif isinstance(other, typing.GenericMeta):
            return cls.type == other
        else:
            return False

    def __hash__(cls):
        return hash(cls.type)

    def __repr__(cls):
        return repr(cls.type)

    def __instancecheck__(cls, obj):
        return cls.type.__instancecheck__(obj)

    def __subclasscheck__(cls, other):
        return cls.type.__subclasscheck__(other)

    def derive_configuration(cls):
        """
        Collect the nearest type variables and effective parameters from the type,
        its bases, and their origins as necessary.
        """
        base_params = cls.base.__parameters__
        if hasattr(cls.type, '__args__'):
            # typing as of commit abefbe4
            tvars = {p: p for p in base_params}
            types = {}
            for t in iter_generic_bases(cls.type):
                if t is cls.base:
                    type_vars = tuple(tvars[p] for p in base_params)
                    parameters = (types.get(tvar, tvar) for tvar in type_vars)
                    break
                if t.__args__:
                    for arg, tvar in zip(t.__args__, t.__origin__.__parameters__):
                        if isinstance(arg, typing.TypeVar):
                            tvars[tvar] = tvars.get(arg, arg)
                        else:
                            types[tvar] = arg
        else:
            # typing 3.5.0
            tvars = [None] * len(base_params)
            for t in iter_generic_bases(cls.type):
                for i, p in enumerate(t.__parameters__):
                    if tvars[i] is None and isinstance(p, typing.TypeVar):
                        tvars[i] = p
                if all(tvars):
                    type_vars = tvars
                    parameters = cls.type.__parameters__
                    break
        cls.type_vars = type_vars
        cls.parameters = tuple(normalize_type(p, 1) for p in parameters)


class GenericWrapper(metaclass=GenericWrapperMeta):
    pass


def type_complexity(type_):
    """Computes an indicator for the complexity of `type_`.

    If the return value is 0, the supplied type is not parameterizable.
    Otherwise, set bits in the return value denote the following features:
    - bit 0: The type could be parameterized but is not.
    - bit 1: The type represents an iterable container with 1 constrained type parameter.
    - bit 2: The type represents a mapping with a constrained value type (2 parameters).
    - bit 3: The type represents an n-tuple (n parameters).
    Since these features are mutually exclusive, only a `Union` can have more than one bit set.
    """
    if (not typing
      or not isinstance(type_, (typing.TypingMeta, GenericWrapperMeta))
      or type_ is AnyType):
        return 0
    if issubclass(type_, typing.Union):
        return reduce(operator.or_, map(type_complexity, type_.__union_params__))
    if issubclass(type_, typing.Tuple):
        if type_.__tuple_params__ is None:
            return 1
        elif type_.__tuple_use_ellipsis__:
            return 2
        else:
            return 8
    if isinstance(type_, GenericWrapperMeta):
        type_count = 0
        for p in reversed(type_.parameters):
            if type_count > 0:
                type_count += 1
            if p is AnyType:
                continue
            if not isinstance(p, typing.TypeVar) or p.__constraints__ or p.__bound__:
                type_count += 1
        return 1 << min(type_count, 2)
    return 0


def first_origin(type_):
    while type_.__origin__:
        type_ = type_.__origin__
    return type_


def find_base_generic(type_):
    """Locates the underlying generic whose structure and behavior are known.

    For example, the base generic of a type that inherits from `typing.Mapping[T, int]`
    is `typing.Mapping`.
    """
    for t in type_.__mro__:
        if t.__module__ == typing.__name__:
            return first_origin(t)


def iter_generic_bases(type_):
    """Iterates over all generics `type_` derives from, including origins.

    This function is only necessary because, in typing 3.5.0, a generic doesn't
    get included in the list of bases when it constructs a parameterized version
    of itself. This was fixed in aab2c59; now it would be enough to just iterate
    over the MRO.
    """
    for t in type_.__mro__:
        if not isinstance(t, typing.GenericMeta):
            continue
        yield t
        t = t.__origin__
        while t:
            yield t
            t = t.__origin__


def sig_cmp(sig1, sig2):
    """
    Compares two normalized type signatures for validation purposes.
    """
    types1 = sig1.required
    types2 = sig2.required
    if len(types1) != len(types2):
        return False
    dup_pos = []
    dup_kw = {}
    for t1, t2 in zip(types1, types2):
        match = type_cmp(t1, t2)
        if match:
            dup_pos.append(match)
        else:
            break
    else:
        return tuple(dup_pos)
    kw_range = slice(len(dup_pos), len(types1))
    kwds1 = sig1.parameters[kw_range]
    kwds2 = sig2.parameters[kw_range]
    if set(kwds1) != set(kwds2):
        return False
    kwtypes1 = dict(zip(sig1.parameters, types1))
    kwtypes2 = dict(zip(sig2.parameters, types2))
    for kw in kwds1:
        match = type_cmp(kwtypes1[kw], kwtypes2[kw])
        if match:
            dup_kw[kw] = match
        else:
            break
    else:
        return tuple(dup_pos), dup_kw
    return False


def type_cmp(t1, t2):
    if t1 is AnyType and t2 is not AnyType:
        return False
    if t2 is AnyType and t1 is not AnyType:
        return False
    if t1 == t2:
        return t1
    if typing:
        if isinstance(t1, typing.UnionMeta) and isinstance(t2, typing.UnionMeta):
            common = t1.__union_set_params__ & t2.__union_set_params__
            if common:
                return next(iter(common))
        elif isinstance(t1, typing.UnionMeta) and t2 in t1.__union_params__:
            return t2
        elif isinstance(t2, typing.UnionMeta) and t1 in t2.__union_params__:
            return t1
    return False


class AnyTypeMeta(type):
    def __subclasscheck__(cls, other):
        if not isinstance(other, type):
            return super().__subclasscheck__(other)
        return True


class AnyType(metaclass=AnyTypeMeta):
    pass


if typing:
    AnyType = typing.Any


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
    if not isinstance(func, FunctionType):
        raise OverloadingError("%r is not a function." % func)


def is_void(func):
    """
    Determines if a function is a void function, i.e., one whose body contains
    nothing but a docstring or an ellipsis. A void function can be used to introduce
    an overloaded function without actually registering an implementation.
    """
    try:
        source = dedent(inspect.getsource(func))
    except (OSError, IOError):
        return False
    fdef = next(ast.iter_child_nodes(ast.parse(source)))
    return (
      type(fdef) is ast.FunctionDef and len(fdef.body) == 1 and
      type(fdef.body[0]) is ast.Expr and
      type(fdef.body[0].value) in {ast.Str, ast.Ellipsis})


def update_docstring(dispatcher, func=None):
    """
    Inserts a call signature at the beginning of the docstring on `dispatcher`.
    The signature is taken from `func` if provided; otherwise `(...)` is used.
    """
    doc = dispatcher.__doc__ or ''
    if inspect.cleandoc(doc).startswith('%s(' % dispatcher.__name__):
        return
    sig = '(...)'
    if func and func.__code__.co_argcount:
        argspec = inspect.getfullargspec(func) # pylint: disable=deprecated-method
        if argspec.args and argspec.args[0] in {'self', 'cls'}:
            argspec.args.pop(0)
        if any(argspec):
            sig = inspect.formatargspec(*argspec) # pylint: disable=deprecated-method
            sig = re.sub(r' at 0x[0-9a-f]{8,16}(?=>)', '', sig)
    sep = '\n' if doc.startswith('\n') else '\n\n'
    dispatcher.__doc__ = dispatcher.__name__ + sig + sep + doc


def get_full_name(obj):
    return obj.__module__ + '.' + obj.__qualname__


def _repr(type_):
    if type_ is AnyType:
        return '<any type>'
    return repr(type_)


def dedent(text):
    indent = re.match(r'\s*', text).group()
    if indent:
        text = re.sub('^' + indent, '', text, flags=re.M)
    return text

