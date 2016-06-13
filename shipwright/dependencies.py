from __future__ import absolute_import

import functools
import itertools
import operator
from collections import namedtuple

from . import zipper


def _compose(*fns):
    """
    Given a list of functions such as f, g, h, that each take a single value
    return a function that is equivalent of f(g(h(v)))
    """

    ordered = list(reversed(fns))

    def apply_(v, f):
        return f(v)

    def compose_(v):
        return functools.reduce(apply_, ordered, v)
    return compose_


def _union(inclusions, tree):
    targets = functools.reduce(
        # for each tree func run it, convert to set
        lambda p, f: p | set(f(tree)),
        inclusions,
        set(),
    )

    return _make_tree(targets)


# [(tree -> [ImageNames])] -> [Containers]
def eval(build_targets, targets):
    """
    Given a list of partially applied functions that
    take a tree and return a list of image names.

    First apply all non-exclude functinons with the tree built from targets
    creating a union of the results.

    Then returns the results of applying each exclusion functinon
    in order.

    """
    inclusions = []
    exclusions = []

    pt = functools.partial
    bt = build_targets

    specifiers = itertools.chain(
        (pt(_exact, target) for target in bt['exact']),
        (pt(_dependents, target) for target in bt['dependents']),
        (pt(_exclude, target) for target in bt['exclude']),
        (pt(_upto, target) for target in bt['upto']),
    )

    for spec in specifiers:
        if spec.func == _exclude:
            exclusions.append(spec)
        else:
            inclusions.append(spec)

    tree = _make_tree(targets)
    if inclusions:
        tree = _union(inclusions, tree)

    return _brood(_compose(*exclusions)(tree))


_Root = namedtuple('_Root', ['name', 'short_name', 'children'])


def _find(tree, name):
    def find_(loc):
        target = loc.node()
        return target.name == name or target.short_name == name

    return tree.find(find_)


def _make_tree(containers):
    """
    Converts a list of containers into a tree represented by a zipper.
    see http://en.wikipedia.org/wiki/Zipper_(data_structure)

    >>> from .dependencies import targets

    >>> root = _make_tree(targets)
    >>> root.node().name is None # doctest: +ELLIPSIS
    True

    >>> _names(root)  # doctest: +NORMALIZE_WHITESPACE
    ['shipwright_test/1', 'shipwright_test/independent', 'shipwright_test/2',
    'shipwright_test/3']

    >>> root.down().node()  # doctest: +ELLIPSIS
    Target(container=Container(name='shipwright_test/1', ...)

    >>> _names(root.down())  # doctest: +ELLIPSIS
    ['shipwright_test/2', 'shipwright_test/3']


    >>> root.down().down().node()  # doctest: +ELLIPSIS
    Target(container=Container(name='shipwright_test/2', ...)

    >>> _names(root.down().down())  # doctest: +ELLIPSIS
    ['shipwright_test/3']

    >>> root.down().right().node().name # doctest: +ELLIPSIS
    'shipwright_test/independent'

    """

    root = _Root(None, None, ())
    tree = zipper.zipper(root, _is_branch, _children, _make_node)

    for c in containers:

        def is_child(target):
            if not isinstance(target, _Root):
                return target.parent == c.name

        branch_children, root_children = _split(is_child, tree.children())
        t = c._replace(children=tuple(branch_children))

        if branch_children:
            tree = tree.edit(_replace, tuple(root_children))

        loc = _find(tree, t.parent)
        if loc:
            tree = loc.insert(t).top()
        else:
            tree = tree.insert(t)

    return tree


def _replace(node, children):
    return node._replace(children=children)


def _children(item):
    return item.children


def _is_branch(item):
    return True


def _make_node(node, children):
    # keep children sorted to make testing easier
    ch = tuple(sorted(children, key=operator.attrgetter('name')))
    return node._replace(children=ch)


def _breadth_first_iter(loc):
    """
    Given a loctation node (from a zipper) walk it's children in breadth first
    order.

    >>> from .dependencies import targets

    >>> tree = _make_tree(targets)

    >>> result = [loc.node().name for loc in _breadth_first_iter(tree)]
    >>> result  # doctest: +NORMALIZE_WHITESPACE
    [None, 'shipwright_test/1', 'shipwright_test/independent',
    'shipwright_test/2', 'shipwright_test/3']

    """

    tocheck = [loc]
    while tocheck:
        l = tocheck.pop(0)
        yield l
        child = l.down()
        while child:
            tocheck.append(child)
            child = child.right()


# Loc -> [Target]
def _lineage(loc):
    results = []
    while loc.path:
        node = loc.node()
        results.append(node)
        loc = loc.up()
    return results


# (a -> Bool) -> [a] ->[a], [a]
def _split(f, children):
    """
    Given a function that returns true or false and a list. Return
    a two lists all items f(child) == True is in list 1 and
    all items not in the list are in list 2.

    """

    l1 = []
    l2 = []
    for child in children:
        if f(child):
            l1.append(child)
        else:
            l2.append(child)
    return l1, l2


# Loc -> [Target]
def _brood(loc):
    return [loc.node() for loc in _breadth_first_iter(loc)][1:]


# Target -> Tree -> [Target]
def _upto(target, tree):
    """
    returns target and everything it depends on

    >>> from .dependencies import targets
    >>> targets = _upto('shipwright_test/2', _make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/1', 'shipwright_test/2']
    """

    loc = _find(tree, target)

    return _lineage(loc)  # _make_tree(lineage(loc))


# Target -> Tree -> [Target]
def _dependents(target, tree):
    """
    Returns a target it's dependencies and
    everything that depends on it

    >>> from .dependencies import targets
    >>> targets = _dependents('shipwright_test/2', _make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/1', 'shipwright_test/2', 'shipwright_test/3']
    """

    loc = _find(tree, target)

    return _lineage(loc) + _brood(loc)


# Target -> Tree -> [Target]
def _exact(target, tree):
    """
    Returns only the target.

    >>> from .dependencies import targets
    >>> targets = _exact('shipwright_test/2', _make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/2']

    """

    loc = _find(tree, target)

    return [loc.node()]


# Target -> Tree -> Tree
def _exclude(target, tree):
    """
    Returns everything but the target and it's dependents. If target
    is not found the whole tree is returned.

    >>> from .dependencies import targets
    >>> tree = _exclude('shipwright_test/2', _make_tree(targets))
    >>> _names(tree) # doctest: +ELLIPSIS
    ['shipwright_test/1', 'shipwright_test/independent']

    """

    loc = _find(tree, target)
    if loc:
        return loc.remove().top()
    else:
        return tree


# Test methods ###
def _names(tree):
    return [n.name for n in _brood(tree)]


def _names_list(targets):
    return sorted([n.name for n in targets])


def setup_module(module):
    from .container import Container
    from .source_control import Target

    def target(name, dir_path, path, parent):
        return Target(
            Container(name, dir_path, path, parent, name),
            'abc', None,
        )

    module.targets = [
        target(
            'shipwright_test/2', 'path2/', 'path2/Dockerfile',
            'shipwright_test/1',
        ),
        target(
            'shipwright_test/1', 'path1/', 'path1/Dockerfile',
            'ubuntu',
        ),
        target(
            'shipwright_test/3', 'path3/', 'path3/Dockerfile',
            'shipwright_test/2',
        ),
        target(
            'shipwright_test/independent', 'independent',
            'path1/Dockerfile', 'ubuntu',
        ),
    ]
