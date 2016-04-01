# Collection of our favorite functional idioms
# Note in many cases you'll see normal python functions
# with the arguments reversed. Have a look at
# http://functionaltalks.org/2013/05/27/brian-lonsdorf-hey-underscore-youre-doing-it-wrong/
# to understand why

from __future__ import absolute_import
from __future__ import print_function

try:
    import builtins as __builtin__
except ImportError:
    import __builtin__


from itertools import chain

try:
    from itertools import imap as itertools_imap
except ImportError:
    itertools_imap = map

from functools import partial, wraps, reduce as ft_reduce
import inspect

import re


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


def composed(*fns):
    """
    Decorater to compose functions and write a doc test at the same time.
    The function being decorated exists simply to document the composition.

    For example if we have these 3 functions

    >>> def first(a):
    ...   return a + 2

    >>> def second(b):
    ...   return b + 10

    >>> def third(c):
    ...   return c - 5


    We can compose them with decorator, note the body of bogus_func
    is never called.

    >>> @composed(first, second, third)
    ... def bogus_func(int):
    ...    "... insert a doc test here ..."


    """
    def dec(f):
        return wraps(f)(compose(*fns))
    return dec


def apply(fn):
    @wraps(fn)
    def _(arr):
        return fn(*arr)
    return _


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
def tap(fn, val):
    fn(val)
    return val

show = tap(print)

print_fun = print


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


def search(pattern, string=None):
    def search(string):
        m = re.search(pattern, string)
        if m:
            return m.groups()

    if string is None:
        return search
    else:
        return search(string)


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


@curry
def filter(fn, sequence):
    return list(__builtin__.filter(fn, sequence))


def empty(seq):
    return len(seq) == 0


def first(arr):
    """
    >>> first([1,2,3])
    1
    """
    return arr[0]


def last(arr):
    """
    >>> last([1,2,3])
    3
    """
    return arr[-1]


@curry
def slice(start, stop, seq):
    return seq[start:stop]


@curry
def get(index, arr):
    """
    Returns the item in the array at the given index or None.
    """
    if index > len(arr) - 1:
        return None
    else:
        return arr[index]


def const(val):
    return lambda x: val

# Convienance getters
_0 = get(0)
_1 = get(1)
_2 = get(2)
_3 = get(3)
_4 = get(4)
_5 = get(5)
_6 = get(6)
_7 = get(7)
_8 = get(8)
_9 = get(9)


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


def identity(obj):
    return obj


@curry
def getattr(attr, obj):
    return __builtin__.getattr(obj, attr)


@curry
def setattr(attr, value, obj):
    __builtin__.setattr(obj, attr, value)
    return obj


# namedtuples
def replace(**kw):
    def _replace(nt):
        return nt._replace(**kw)
    return _replace


@curry
def debug(fn, value):
    """
    Pause the python interpreter prior to calling a funtion. Useful
    during development to inspect composed functions.

    Imagine you have some long chain of composed functions

    composed_fun = compose(some, long, function, chain)

    You can stick a debug in the middle of it to inspect the result
    before and after the function to the left is called.

    So in this case wrapping function with a debug alows us to
    inspect the input and output of it prior to being passed
    to the long function.

    composed_fun = compose(some, long, debug(function), chain)

    """
    import pdb
    pdb.set_trace()
    ret = fn(value)
    return ret
