import os
import errno
import json

from functools import partial

import docker
import git

import shipwright


def main():
 
  namespace = _0(sys.argv) or os.environ['SW_NAMESPACE']

  repo = git.Repo(os.getcwd())
  data_dir = os.path.join(repo.working_dir, '.shipwright')

  branch = repo.active_branch.name

  # last_built_ref or none 
  last_built_ref = maybe(repo.commit, last_built(data_dir, branch))

  base_url = os.environ.get('DOCKER_URL','unix://var/run/docker.sock')
  build_func = partial(
    docker.Client(
      base_url=base_url,
      version='1.9',
      timeout=10).build,
    stream=True
  )

  targets = shipwright.targets(repo, last_built_ref, namespace)
  for line in do_build(build_func, targets):

    try:
      print line,
    except UnicodeEncodeError:
      pass
  save_last_built(data_dir, branch, repo.commit())

  for t in targets:
    print "Built ", t

def get(index, arr):
  """
  Returns the item in the array at the given index or None.
  """
  if index > len(arr) - 1:
    return None
  else:
    return arr[index]

# Return the item at index 0 in the array or None if the 
# array is empty
_0 = partial(get, 0)

def maybe(f, value):
  """
  Given a function and a value. If the value is not None
  apply the value to the function and return the result.
  """
  if value is not None:
    return f(value)


def last_built(data_dir, branch):
  """
  Look in the data dir for a file named branch and return it's contents.
  The contents represents the last commit that we successfully built 
  docker containers. 
  """
  ensure_dir(data_dir)
  ref_path = os.path.join(data_dir, branch)

  try:
    return open(ref_path).read()
  except IOError,e:
    if e.errno == errno.ENOENT:
      return None
    raise

def save_last_built(data_dir, branch, ref):
  ref_path = os.path.join(data_dir, branch)  
  open(ref_path,'w').write(ref.hexsha)


def ensure_dir(path):
  if not os.path.exists(path):
    os.makedirs(path)


# (path -> iter str) -> [Containers]  -> iter str
def do_build(build_func, targets):
  """
  Returns an iterator  that contacts the  output of building each
  container.
  """
  
  return (
    switch(json.loads(line))
    for  c in targets # c = Container
    for line in build_func(show(os.path.dirname(c.path)), tag=c.name) 
  )


def show(i):
  print  i
  return i

def switch(rec):
  if 'stream' in rec:
    return rec['stream']
  else:
    # TODO: this represents an error
    return rec
