from __future__ import absolute_import

from collections import  defaultdict, namedtuple

import zipper

from . import fn
from .fn import curry



def eval(specifiers, targets):
  transforms = []

  for spec in specifiers:
    if spec.startswith('='):
      # '=blah' -> exact('blah')
      transforms.append(exact(spec[1:]))
    elif spec.startswith('^'):
      # '^blah's -> descendants('blah')
      transforms.append(descendants(spec[1:]))
    elif spec.startswith('-'):
      # '-blah's -> exclude('blah')
      transforms.append(exclude(spec[1:]))
    else:
      transforms.append(upto(spec))

  tree = make_tree(targets)

  for trans in transforms:
    tree = trans(tree)

  return tree



def union(inclusions, tree):
  return make_tree(reduce(lambda p,f: p | set(f(tree)), inclusions, set()))

def eval2(specifiers, targets):
  inclusions = []
  exclusions = []

  for spec in specifiers:
    if spec.startswith('='):
      # '=blah' -> exact('blah')
      inclusions.append(exact(spec[1:]))
    elif spec.startswith('^'):
      # '^blah's -> descendants('blah')
      inclusions.append(descendants(spec[1:]))
    elif spec.startswith('-'):
      # '-blah's -> exclude('blah')
      exclusions.append(exclude(spec[1:]))
    else:
      inclusions.append(upto(spec))

  tree = union(inclusions, make_tree(targets))

  return fn.compose(exclusions)(tree)



# Ref = git.Ref
# item = <anything>
# [Ref] -> Ref -> [Containers] -> [item]
def needs_building(tree):
  """
  """
  
  gen = breadth_first_iter(tree)
  root = next(gen) # skip root
  loc = next(gen)

  skip = []
  needs = []


  while True:
    try:
      target  = loc.node()
      
      if target.current_rel > target.last_built_rel:

        # target has changes, it and all it's desendents need
        # to be rebuilt
        for modified_loc in breadth_first_iter(loc):
          target = modified_loc.node()

          if target.current_rel is not None: #only yield targets commited to git
            needs.append(target)
        loc = gen.send(True) # don't check this locations children
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

  >>> _names(root)
  ['shipwright_test/1', 'shipwright_test/independent', 'shipwright_test/2', 'shipwright_test/3']

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
  tree =  zipper.zipper(root, is_branch, children, make_node)
  
  for c in containers:
    t = c._replace(children=())

    loc = tree.find(fmap(is_target(t.parent)))
    if loc:
      tree = loc.insert(t).top()
    else: 
      tree = tree.edit(reroot, t)

  return tree

def reroot(root, branch):
  """
  Adds the branch into the root, sweeping up children that
  may have been inserted before it.
  """
  root_children = []
  branch_children = []
  for child in root.children:
    if child.parent == branch.name:
      branch_children.append(child)
    else:
      root_children.append(child)

  branch = branch._replace(children=tuple(branch_children))
  root_children.append(branch)

  return root._replace(children=tuple(root_children))


def children(item):
  return item.children

def is_branch(item):
  return True

def make_node(node, children):
  # keep children sorted to make testing easier
  ch = tuple(sorted(children,key=fn.getattr('name')))
  return node._replace(children=ch)


def breadth_first_iter(loc):
  """
  Given a loctation node (from a zipper) walk it's children in breadth first
  order.

  >>> from .dependencies import targets

  >>> tree = make_tree(targets)

  >>> [loc.node().name for loc in breadth_first_iter(tree)] # doctest: +ELLIPSIS
  [None, 'shipwright_test/1', 'shipwright_test/independent', 'shipwright_test/2', 'shipwright_test/3']

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
  >>> from . import Target
  >>> from . import Container

  >>> target = Target(Container('test', None, None, None), None, None, None, None)
  >>> is_target('test', target)
  True
  """
  return target.name == name

@curry
def is_child(parent, target):
  if not isinstance(target, Root):
    return target.parent == parent

@curry
def fmap(func, loc):
  return func(loc.node())

def lineage(loc):
  results = []
  while loc.path:
    node = loc.node()
    results.append(node)
    loc = loc.up()
  return results

def brood(loc):
  return [loc.node() for loc in breadth_first_iter(loc)][1:]

#all = make_tree


@curry
def upto(target, tree):
  """
  returns target and everything it depends on

  >>> from .dependencies import targets
  >>> tree = upto('shipwright_test/2', make_tree(targets))
  >>> _names(tree)
  ['shipwright_test/1', 'shipwright_test/2']
  """

  loc = tree.find(fmap(is_target(target)))
 
  return make_tree(lineage(loc))

@curry
def descendants(target, tree):
  """
  Returns a target it's dependencies and 
  everything that depends on it

  >>> from .dependencies import targets
  >>> tree = descendants('shipwright_test/2', make_tree(targets))
  >>> _names(tree)
  ['shipwright_test/1', 'shipwright_test/2', 'shipwright_test/3']
  """

  loc = tree.find(fmap(is_target(target)))
  return make_tree(lineage(loc) + brood(loc))

@curry
def exact(target, tree):
  """
  Returns only the target.

  >>> from .dependencies import targets
  >>> tree = exact('shipwright_test/2', make_tree(targets))
  >>> _names(tree)
  ['shipwright_test/2']
  
  """

  loc = tree.find(fmap(is_target(target)))

  return make_tree([loc.node()])

@curry
def exclude(target, tree):
  """
  Returns everything but the target and it's descendants. If target
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


### Test methods ###
def _names(tree):
 return [n.name for n in brood(tree)]

def setup_module(module):
  from .container import Container
  from . import Target

  module.targets = [
    Target(
      Container('shipwright_test/2', 'path2/', 'path2/Dockerfile', 'shipwright_test/1'),
      'abc',
      3,
      3,
      None
    ),
    Target(
      Container('shipwright_test/1', 'path1/', 'path1/Dockerfile', 'ubuntu'),
      'abc',
      3,
      3,
      None
    ),
    Target(
      Container('shipwright_test/3', 'path3/', 'path3/Dockerfile', 'shipwright_test/2'),
      'abc',
      3,
      3,
      None
    ),
    Target(
      Container('shipwright_test/independent', 'independent', 'path1/Dockerfile', 'ubuntu'),
      'abc',
      3,
      3,
      None
    )
  ]

