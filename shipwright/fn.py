# Collection of our favorite functional idioms
# Note in many cases you'll see normal python functions
# with the arguments reversed. Have a look at
# http://functionaltalks.org/2013/05/27/brian-lonsdorf-hey-underscore-youre-doing-it-wrong/
# to understand why

from __future__ import absolute_import, print_function

from functools import reduce as ft_reduce


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


def merge(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d
