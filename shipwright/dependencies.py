from __future__ import absolute_import

from collections import  defaultdict

import zipper

# Ref = git.Ref
# item = <anything>
# [Ref] -> Ref -> [Containers] -> [item]
def needs_building(targets):
  """
  """
  
  gen = breadth_first_iter(make_tree(targets))
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




# [Container] -> Loc Container

def make_tree(containers):
  """
  Converts a list of containers into a tree represented by a zipper.
  see http://en.wikipedia.org/wiki/Zipper_(data_structure)

  >>> containers = [
  ...   Container('shipwright_test/2', 'path1/Dockerfile', 'shipwright_test/1'),
  ...   Container('shipwright_test/1', 'path1/Dockerfile', 'ubuntu'),
  ...   Container('shipwright_test/3', 'path1/Dockerfile', 'shipwright_test/2'),
  ...   Container('shipwright_test/independent', 'path1/Dockerfile', 'ubuntu'),
  ... ]

  >>> root = make_tree(containers)

  >>> root  # doctest: +ELLIPSIS
  <zipper.Loc(None) ...>

  >>> root.children()  # doctest: +ELLIPSIS
  [Container(name='shipwright_test/1', ...), Container(name='shipwright_test/independent', ...)]

  >>> root.down().node()  # doctest: +ELLIPSIS
  Container(name='shipwright_test/1', ...)

  >>> root.down().children()  # doctest: +ELLIPSIS
  [Container(name='shipwright_test/2', ...)]

  >>> root.down().down().node()  # doctest: +ELLIPSIS
  Container(name='shipwright_test/2', ...)

  >>> root.down().down().children()  # doctest: +ELLIPSIS
  [Container(name='shipwright_test/3', ...)]
  
  >>> root.down().right().node() # doctest: +ELLIPSIS
  Container(name='shipwright_test/independent', ...)

  """

  container_map = {c.container.name:c for c in containers}
  graph = defaultdict(list)

  # TODO: check for cycles
  for c in containers:
    graph[container_map.get(c.container.parent)].append(c)

  # sort children by name, to make testing eaiser
  for node, children in graph.items():
    graph[node] = sorted(children)

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

  >>> containers = [
  ...   Container('shipwright_test/2', 'path1/Dockerfile', 'shipwright_test/1'),
  ...   Container('shipwright_test/1', 'path1/Dockerfile', 'ubuntu'),
  ...   Container('shipwright_test/3', 'path1/Dockerfile', 'shipwright_test/2'),
  ...   Container('shipwright_test/independent', 'path1/Dockerfile', 'ubuntu'),
  ... ]

  >>> tree = make_tree(containers)
  >>> [loc.node() for loc in breadth_first_iter(tree)] # doctest: +ELLIPSIS
  [None, Container(name='shipwright_test/1', ...), Container(name='shipwright_test/independent', ...), Container(name='shipwright_test/2', ...), Container(name='shipwright_test/3', ...)]

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

  