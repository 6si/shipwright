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


@curry
def fmap(fn, sequence):
    return itertools_imap(fn, sequence)


# (a -> [b]) -> [a] -> [b]
@curry
def flat_map(f, arr):
    return chain.from_iterable(fmap(f, arr))


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
