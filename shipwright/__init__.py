import os

from . import container
from container import Container
from collections import OrderedDict, defaultdict

import zipper

# Path = str

# str -> Path -> [Container]
def targets(repo, last_built_ref, namespace):
  """
  Returns a list of containers in the proper build order.
  """

  containers = container.containers(namespace, repo.working_dir)
 
  return needs_building(
    commits(repo),
    last_built_ref,
    containers,
    lambda container: last_commit(repo,  os.path.dirname(container.path))
  )



# Ref = git.Ref
# item = <anything>
# [Ref] -> Ref -> [Containers] -> [item]
def needs_building(commits, last_built, containers, rev_func):
  """
  Given a list of commits (a list of git reference)
  for a branch, the last reference the branch  was built against
  and a list of [item, Ref] return the items that have been modified
  since the last build. 

  Testing Note: in reality commits are random sha and their values do not represents a
  specific ordering. It's eaiser to use strings for the test.

  >>> containers = [
  ...   Container('shipwright_test/2', 'path1/Dockerfile', 'shipwright_test/1'),
  ...   Container('shipwright_test/1', 'path1/Dockerfile', 'ubuntu'),
  ...   Container('shipwright_test/3', 'path1/Dockerfile', 'shipwright_test/2'),
  ...   Container('shipwright_test/independent', 'path1/Dockerfile', 'ubuntu'),
  ... ]

  >>> map = dict(zip(containers, ['a','c','d', 'b']))


  >>> commits = ['a', 'b', 'c', 'd','e']
  >>> last_built = 'c'


  >>> list(filter_built_2(commits, last_built, containers, map.get)) # doctest: +ELLIPSIS   +SKIP
  [Container(name='shipwright_test/3', ...)]

  >>> last_built = None
  >>> list(filter_built_2(commits, last_built, containers, map.get)) # doctest: +ELLIPSIS +SKIP
  [Container(name='shipwright_test/1', ...), Container(name='shipwright_test/2', ...), Container(name='shipwright_test/3', ...), Container(name='shipwright_test/independent', ...)]


  """
  
  commit_map = { rev:i  for i, rev in enumerate(commits) }

  if last_built is None:
    last = -1
  else:
    last = commit_map[last_built]

  gen = breadth_first_iter(make_tree(containers))
  root = next(gen) # skip root
  loc = next(gen)

  skip = []
  needs = []


  while True:
    try:
      container = loc.node()
      
      rev = rev_func(container)
      
      if rev and commit_map[rev] > last:
        # container has changes, it and all it's desendents need
        # to be rebuilt
        for modified_loc in breadth_first_iter(loc):
          container = modified_loc.node()
          if rev_func(container): #only yield containers commited to git
            needs.append(container)
        loc = gen.send(True) # don't check this locations children
      else:
        if rev:
          skip.append(container)
        
        loc = next(gen)
    except StopIteration:
      break
      
  return skip, needs


# git.Repo -> [git.Commit]
def commits(repo):
  return reversed(list(repo.iter_commits()))

def last_commit(repo,  path):
  try:
    return next(repo.iter_commits(paths=path, max_count=1))
  except StopIteration:
    return None

# repo -> [Container] -> [[Container,Ref]]
def annotate_containers(repo, containers):
  """
  Given a git repo and a list of containers returns
  a list of [Container,Ref] pairs where ref is the 
  last commit the directory containing the container
  was edited.
  """
  return [
    (c, last_commit(repo, os.path.dirname(c.path)))
    for c in containers
  ]


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

  container_map = {c.name:c for c in containers}
  graph = defaultdict(list)

  # TODO: check for cycles
  for c in containers:
    graph[container_map.get(c.parent)].append(c)

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

  