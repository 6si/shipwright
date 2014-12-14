from __future__ import absolute_import

from collections import  defaultdict, namedtuple

import zipper

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


Node = namedtuple('Node', 'value, children')

# [Container] -> Loc Container

def make_tree(containers):
  """
  Converts a list of containers into a tree represented by a zipper.
  see http://en.wikipedia.org/wiki/Zipper_(data_structure)

  >>> from .dependencies import targets

  >>> root = make_tree(targets)

  >>> root  # doctest: +ELLIPSIS
  <zipper.Loc(None) ...>

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
  
  >>> root.down().right().node() # doctest: +ELLIPSIS
  Target(container=Container(name='shipwright_test/independent', ...)

  """

  container_map = {c.container.name:c for c in containers}
  graph = defaultdict(list)

  # TODO: check for cycles
  for c in containers:
    graph[container_map.get(c.container.parent)].append(c)

  # sort children by name, to make testing eaiser
  for node, children in graph.items():
    graph[node] = tuple(sorted(children))

  def children(item):
    return graph[item]

  def is_branch(item):
    return len(children(item)) > 0

  def make_node(node, children):
    return node

  root_loc =  zipper.zipper(None, is_branch, children, make_node)

  return root_loc


def breadth_first_iter(loc):
  """
  Given a loctation node (from a zipper) walk it's children in breadth first
  order.

  >>> from .dependencies import targets

  >>> tree = make_tree(targets)
  >>> [loc.node() for loc in breadth_first_iter(tree)] # doctest: +ELLIPSIS
  [None, ...Container(name='shipwright_test/1', ...), ...Container(name='shipwright_test/independent', ...), ...Container(name='shipwright_test/2', ...), ...Container(name='shipwright_test/3', ...)]

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


#
@curry
def is_target(name, target):
  """
  >>> from . import Target
  >>> from . import Container

  >>> target = Target(Container('test', None, None, None), None, None, None)
  >>> is_target('test', target)
  True
  """
  return target.container.name == name

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


def exclude(target, tree):
  """
  Returns everything but the target and it's descendants.

  >>> from .dependencies import targets
  >>> tree = exclude('shipwright_test/2', make_tree(targets))
  >>> _names(tree) # doctest: +ELLIPSIS
  ['shipwright_test/1', 'shipwright_test/independent']

  """
  loc = tree.find(fmap(is_target(target)))
 
  ret = loc.remove()
  return ret.top()


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
      3
    ),
    Target(
      Container('shipwright_test/1', 'path1/', 'path1/Dockerfile', 'ubuntu'),
      'abc',
      3,
      3
    ),
    Target(
      Container('shipwright_test/3', 'path3/', 'path3/Dockerfile', 'shipwright_test/2'),
      'abc',
      3,
      3
    ),
    Target(
      Container('shipwright_test/independent', 'independent', 'path1/Dockerfile', 'ubuntu'),
      'abc',
      3,
      3
    )
  ]

