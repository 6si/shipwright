from __future__ import absolute_import

import operator
from collections import namedtuple

from . import zipper


# [(tree -> [ImageNames])] -> [Images]
def eval(build_targets, targets):
    """
    Given a list of partially applied functions that
    take a tree and return a list of image names.

    First apply all non-exclude functinons with the tree built from targets
    creating a union of the results.

    Then returns the results of applying each exclusion functinon
    in order.

    """
    tree = _make_tree(targets)
    bt = build_targets

    exact, dependents, upto = bt['exact'], bt['dependents'], bt['upto']
    if exact or dependents or upto:
        base = set()
        for target in exact:
            base = base | set(_exact(target, tree))
        for target in dependents:
            base = base | set(_dependents(target, tree))
        for target in upto:
            base = base | set(_upto(target, tree))

        tree = _make_tree(base)

    for target in bt['exclude']:
        tree = _exclude(target, tree)

    return _brood(tree)


_Root = namedtuple('_Root', ['name', 'short_name', 'children'])


def _find(tree, name):
    def find_(loc):
        target = loc.node()
        return target.name == name or target.short_name == name

    return tree.find(find_)


def _make_tree(images):
    """
    Converts a list of images into a tree represented by a zipper.
    see http://en.wikipedia.org/wiki/Zipper_(data_structure)
    """

    root = _Root(None, None, ())
    tree = zipper.zipper(root, _is_branch, _children, _make_node)

    for c in images:

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
    """Returns target and everything it depends on"""

    loc = _find(tree, target)

    return _lineage(loc)  # _make_tree(lineage(loc))


# Target -> Tree -> [Target]
def _dependents(target, tree):
    """Returns a target it's dependencies and everything that depends on it"""

    loc = _find(tree, target)

    return _lineage(loc) + _brood(loc)


# Target -> Tree -> [Target]
def _exact(target, tree):
    """Returns only the target."""

    loc = _find(tree, target)

    return [loc.node()]


# Target -> Tree -> Tree
def _exclude(target, tree):
    """
    Returns everything but the target and it's dependents. If target
    is not found the whole tree is returned.
    """

    loc = _find(tree, target)
    if loc:
        return loc.remove().top()
    else:
        return tree
