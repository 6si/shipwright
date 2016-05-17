# Collection of our favorite functional idioms
# Note in many cases you'll see normal python functions
# with the arguments reversed. Have a look at
# http://functionaltalks.org/2013/05/27/brian-lonsdorf-hey-underscore-youre-doing-it-wrong/
# to understand why

from __future__ import absolute_import, print_function

import inspect
from functools import reduce as ft_reduce
from functools import partial, wraps
from itertools import chain

try:
    import builtins as __builtin__
except ImportError:
    import __builtin__


try:
    from itertools import imap as itertools_imap
except ImportError:
    itertools_imap = map


def curry(f):
    """
    Decorator to autocurry a function.

    >>> @curry
    ... def f(x,y,z):
    ...   return x+y+z

    >>> 6 ==  f(1,2,3) == f(1)(2,3) == f(1)(2)(3) == f(1)()(2)()(3)
    True
    """
    if isinstance(f, partial):
        num_args = len(inspect.getargspec(f.func)[0]) - len(f.args)
        args = f.args
        f = f.func
    else:
        num_args = len(inspect.getargspec(f)[0])
        args = []

    @wraps(f)
    def curry_(*a, **k):
        if len(a) == num_args:
            return f(*chain(args, a), **k)
        else:
            return curry(partial(f, *chain(args, a), **k))
    return curry_


def compose(*fns):
    """
    Given a list of functions such as f, g, h, that each take a single value
    return a function that is equivalent of f(g(h(v)))
    """

    ordered = list(reversed(fns))
    reduce = ft_reduce

    def apply_(v, f):
        return f(v)

    def compose_(v):
        return reduce(apply_, ordered, v)
    return compose_


def juxt(*fns):
    """
    >>> juxt(len)("blah")
    [4]

    >>> juxt(len, lambda o: o.capitalize())("blah")
    [4, 'Blah']

    """
    def _(val):
        return [fn(val) for fn in fns]
    return _


@curry
def catch(fn, on_error, value):
    """
    Given a function and an error handler  returns a function
    that invokes the function with the given value. Returns
    the results of the invoked function if there were no errors
    otherwise returns the results of invoking the error handler.
    """

    try:
        return fn(value)
    except Exception as e:
        return on_error(e, value)


@curry
def not_(fn, a):
    return not fn(a)


# binary comparisons
@curry
def eq(a, b):
    return a == b


@curry
def ne(a, b):
    return a != b


@curry
def lt(a, b):
    return a < b


@curry
def lte(a, b):
    return a <= b


@curry
def gt(a, b):
    return a > b


@curry
def gte(a, b):
    return a >= b


@curry
def contains(a, b):
    return b in a


@curry
def is_(a, b):
    return a is b

# logic functions


@curry
def maybe(fn, value):
    """
    Given a function and a value. If the value is not None
    apply the value to the function and return the result.
    """
    if value is None:
        return None
    else:
        return fn(value)


def when(*tests):
    def when_(value):
        for test, fn in tests:
            if test(value):
                return fn(value)
        raise RuntimeError('Nothing matched {}'.format(value))
    return when_


# string funcs
@curry
def rsplit(sep, num, s):
    return s.rsplit(sep, num)


@curry
def split(sep, s):
    return s.split(sep)


@curry
def strip(chars, s):
    return s.strip(chars)


@curry
def endswith(s1, s2):
    """
    Returns true if s2 ends with s1
    """

    return s2.endswith(s1)


@curry
def startswith(s1, s2):
    """
    Returns true if s2 starts with s1
    """
    return s2.startswith(s1)


# sequence funcs
flatten = chain.from_iterable


@curry
def map(fn, sequence):
    return list(__builtin__.map(fn, sequence))


@curry
def fmap(fn, sequence):
    return itertools_imap(fn, sequence)


# (a -> [b]) -> [a] -> [b]
@curry
def flat_map(f, arr):
    return flatten(fmap(f, arr))


# Dict functions
@curry
def getitem(key, hashmap):
    return hashmap[key]


@curry
def merge(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d


# object functions


@curry
def getattr(attr, obj):
    return __builtin__.getattr(obj, attr)


@curry
def setattr(attr, value, obj):
    __builtin__.setattr(obj, attr, value)
    return obj
