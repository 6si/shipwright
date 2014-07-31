import sys
import os
import errno
import json

from functools import partial

import docker
import git

import shipwright

from shipwright.fn import maybe, first, _1, show, curry, compose, empty
from shipwright.tar import mkcontext

def main():
 
  namespace = _1(sys.argv) or os.environ['SW_NAMESPACE']
  base_url = os.environ.get('DOCKER_URL','unix://var/run/docker.sock')

  client = docker.Client(
    base_url=base_url,
    version='1.9',
    timeout=10
  )


  repo = git.Repo(os.getcwd())
  data_dir = os.path.join(repo.working_dir, '.shipwright')

  branch = repo.active_branch.name

  # last_built_ref or none 
  last_built_ref = maybe(compose(repo.commit, show), last_built(data_dir, branch))

  this_ref_str = repo.commit().hexsha[:12]

  current, targets = shipwright.targets(repo, last_built_ref, namespace)


  # these containers weren't effected by the latest changes
  # so we'll tag them with the build id. That way  any
  # of the containers that do need to be built can refer
  # to the skiped ones by user/image:<last_built_ref> which makes
  # them part of the same group.

  tag_containers(client, current, last_built_ref.hexsha[:12], this_ref_str)

  for line in do_build(build(client, this_ref_str), targets):

    try:
      print line,
    except UnicodeEncodeError:
      pass
  
  # now that we're built and tagged all the images with git commit
  # tag all containers with the branch name
  tag_containers(
    client, 
    current + targets, 
    this_ref_str, 
    repo.active_branch.name
  )


  save_last_built(data_dir, branch, this_ref_str)


  for t in targets:
    print "Built ", t.name




def last_built(data_dir, branch):
  """
  Look in the data dir for a file named branch and return it's contents.
  The contents represents the last commit that we successfully built 
  docker containers. 
  """
  ensure_dir(data_dir)
  ref_path = os.path.join(data_dir, branch)

  try:
    return open(ref_path).read().strip()
  except IOError,e:
    if e.errno == errno.ENOENT:
      return None
    raise

def save_last_built(data_dir, branch, ref_hexsha):
  ref_path = os.path.join(data_dir, branch)  
  open(ref_path,'w').write(ref_hexsha)


def ensure_dir(path):
  if not os.path.exists(path):
    os.makedirs(path)


def tag_containers(client, containers, last_ref, new_ref):
  
  for container in containers:
    client.tag(
      container.name + ":" + last_ref, 
      container.name,
      tag=new_ref
    )


@curry
def build(client, git_rev, container):
  """
  build the given container ensuring that it depends
  on it's parent that's part of this build group
  """

  return client.build(
    fileobj = mkcontext(git_rev, os.path.dirname(container.path)),
    custom_context = True,
    stream=True,
    tag = '{0}:{1}'.format(container.name, git_rev)
  )
  



# (path -> iter str) -> [Containers]  -> iter str
def do_build(build_func, targets):
  """
  Returns an iterator  that concats the  output of building each
  container.
  """
  
  return (
    switch(json.loads(line))
    for  c in targets # c = Container
    for line in build_func(c) 
  )





def switch(rec):
  if 'stream' in rec:
    return rec['stream']
  elif 'status' in rec:
    return '[STATUS] ' +  rec['status']
  elif 'error' in rec:
    return '[ERROR] ' +  rec['errorDetail']['message']
  else:
    import pdb; pdb.set_trace()
    return rec
