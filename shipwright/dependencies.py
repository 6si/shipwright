from __future__ import absolute_import

from collections import namedtuple
import functools

import zipper

from . import fn
from .fn import curry


def union(inclusions, tree):
    targets = functools.reduce(
        # for each tree func run it, convert to set
        lambda p, f: p | set(f(tree)),
        inclusions,
        set()
    )

    return make_tree(targets)


# [(tree -> [ImageNames])] -> [Containers]
def eval(specifiers, targets):
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

    for spec in specifiers:
        if spec.func_name == 'exclude':
            exclusions.append(spec)
        else:
            inclusions.append(spec)

    tree = make_tree(targets)
    if inclusions:
        tree = union(inclusions, tree)

    return fn.compose(*exclusions)(tree)


# Ref = git.Ref
# item = <anything>
# [Ref] -> Ref -> [Containers] -> [item]
def needs_building(tree):
    gen = breadth_first_iter(tree)
    next(gen)  # skip root
    loc = next(gen)

    skip = []
    needs = []

    while True:
        try:
            target = loc.node()

            if target.current_rel > target.last_built_rel:
                # target has changes, it and all it's desendents need
                # to be rebuilt
                for modified_loc in breadth_first_iter(loc):
                    target = modified_loc.node()

                    # only yield targets commited to git
                    if target.current_rel is not None:
                        needs.append(target)
                loc = gen.send(True)  # don't check this locations children
            else:
                if target.last_built_rel:
                    skip.append(target)

                loc = next(gen)
        except StopIteration:
            break

    return skip, needs


Root = namedtuple('Root', 'name, children')

# [Container] -> Loc Container


def make_tree(containers):
    """
    Converts a list of containers into a tree represented by a zipper.
    see http://en.wikipedia.org/wiki/Zipper_(data_structure)

    >>> from .dependencies import targets

    >>> root = make_tree(targets)
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

    root = Root(None, ())
    tree = zipper.zipper(root, is_branch, children, make_node)

    for c in containers:

        branch_children, root_children = split(is_child(c), tree.children())
        t = c._replace(children=tuple(branch_children))

        if branch_children:
            tree = tree.edit(replace, tuple(root_children))

        loc = tree.find(fmap(is_target(t.parent)))
        if loc:
            tree = loc.insert(t).top()
        else:
            tree = tree.insert(t)

    return tree


def replace(node, children):
    return node._replace(children=children)


def children(item):
    return item.children


def is_branch(item):
    return True


def make_node(node, children):
    # keep children sorted to make testing easier
    ch = tuple(sorted(children, key=fn.getattr('name')))
    return node._replace(children=ch)


def breadth_first_iter(loc):
    """
    Given a loctation node (from a zipper) walk it's children in breadth first
    order.

    >>> from .dependencies import targets

    >>> tree = make_tree(targets)

    >>> result = [loc.node().name for loc in breadth_first_iter(tree)]
    >>> result  # doctest: +NORMALIZE_WHITESPACE
    [None, 'shipwright_test/1', 'shipwright_test/independent',
    'shipwright_test/2', 'shipwright_test/3']

    """

    tocheck = [loc]
    while tocheck:
        l = tocheck.pop(0)
        skip = yield l
        if skip:
            continue
        child = l.down()
        while child:
            tocheck.append(child)
            child = child.right()


@curry
def is_target(name, target):
    """
    >>> from .base import Target
    >>> from .container import Container

    >>> target = Target(
    ...     Container('test', None, None, None), None, None, None, None,
    ... )
    >>> is_target('test', target)
    True
    """
    return target.name == name


@curry
def is_child(parent, target):
    if not isinstance(target, Root):
        return target.parent == parent.name


# (a -> b) -> Loc a -> b
@curry
def fmap(func, loc):
    return func(loc.node())


# Loc -> [Target]
def lineage(loc):
    results = []
    while loc.path:
        node = loc.node()
        results.append(node)
        loc = loc.up()
    return results


# (a -> Bool) -> [a] ->[a], [a]
@curry
def split(f, children):
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
def brood(loc):
    return [loc.node() for loc in breadth_first_iter(loc)][1:]


# Target -> Tree -> [Target]
@curry
def upto(target, tree):
    """
    returns target and everything it depends on

    >>> from .dependencies import targets
    >>> targets = upto('shipwright_test/2', make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/1', 'shipwright_test/2']
    """

    loc = tree.find(fmap(is_target(target)))

    return lineage(loc)  # make_tree(lineage(loc))


# Target -> Tree -> [Target]
@curry
def dependents(target, tree):
    """
    Returns a target it's dependencies and
    everything that depends on it

    >>> from .dependencies import targets
    >>> targets = dependents('shipwright_test/2', make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/1', 'shipwright_test/2', 'shipwright_test/3']
    """

    loc = tree.find(fmap(is_target(target)))
    return lineage(loc) + brood(loc)


# Target -> Tree -> [Target]
@curry
def exact(target, tree):
    """
    Returns only the target.

    >>> from .dependencies import targets
    >>> targets = exact('shipwright_test/2', make_tree(targets))
    >>> _names_list(targets)
    ['shipwright_test/2']

    """

    loc = tree.find(fmap(is_target(target)))

    return [loc.node()]


# Target -> Tree -> Tree
@curry
def exclude(target, tree):
    """
    Returns everything but the target and it's dependents. If target
    is not found the whole tree is returned.

    >>> from .dependencies import targets
    >>> tree = exclude('shipwright_test/2', make_tree(targets))
    >>> _names(tree) # doctest: +ELLIPSIS
    ['shipwright_test/1', 'shipwright_test/independent']

    """

    loc = tree.find(fmap(is_target(target)))
    if loc:
        return loc.remove().top()
    else:
        return tree


# Test methods ###
def _names(tree):
    return [n.name for n in brood(tree)]


def _names_list(targets):
    return sorted([n.name for n in targets])


def setup_module(module):
    from .container import Container
    from .base import Target

    module.targets = [
        Target(
            Container(
                'shipwright_test/2', 'path2/', 'path2/Dockerfile',
                'shipwright_test/1',
            ),
            'abc',
            3,
            3,
            None
        ),
        Target(
            Container(
                'shipwright_test/1', 'path1/', 'path1/Dockerfile',
                'ubuntu',
            ),
            'abc',
            3,
            3,
            None
        ),
        Target(
            Container(
                'shipwright_test/3', 'path3/', 'path3/Dockerfile',
                'shipwright_test/2',
            ),
            'abc',
            3,
            3,
            None
        ),
        Target(
            Container(
                'shipwright_test/independent', 'independent',
                'path1/Dockerfile', 'ubuntu',
            ),
            'abc',
            3,
            3,
            None
        )
    ]
