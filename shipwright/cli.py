import sys
import os
import errno
import json
import string
from functools import partial

import docker
import git

import shipwright

from shipwright import fn
from shipwright.fn import maybe, first, _1, show, curry, compose, empty
from shipwright.fn import flatten, fmap, juxt, identity, apply

from shipwright.tar import mkcontext

from shipwright.colors import rainbow

def main():
 
  namespace = _1(sys.argv) or os.environ['SW_NAMESPACE']
  base_url = os.environ.get('DOCKER_HOST','unix://var/run/docker.sock')

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


  if current:
    # these containers weren't effected by the latest git changes
    # so we'll fast forward tag them with the build id. That way  any
    # of the containers that do need to be built can refer
    # to the skiped ones by user/image:<last_built_ref> which makes
    # them part of the same group.

    tag_containers(client, current, last_built_ref.hexsha[:12], this_ref_str)


  built = list(do_build( 
    highlight,  # callback function, prints to terminal
    build(client, this_ref_str), # build function
    targets # what needs building
  ))


  # now that we're built and tagged all the images with git commit,
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

  # todo: consider just querying docker for this information

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
  
  tag = new_ref.replace('/','-')
  for container in containers:
    client.tag(
      container.name + ":" + last_ref, 
      container.name,
      tag=tag
    )


@curry
def build(client, git_rev, container):
  """
  builds the given container tagged with <git_rev> and ensures that
  it dependson it's parent if it's part of this build group (shares
  the same namespace)
  """

  return client.build(
    fileobj = mkcontext(git_rev, os.path.dirname(container.path)),
    custom_context = True,
    stream=True,
    tag = '{0}:{1}'.format(container.name, git_rev)
  )
  



def do_build(show_func, build_func, targets): 
  return fmap(
    compose(
      apply(parse_and_show(show_func)),
      juxt(identity, build_func) # targets -> (container, stream)
    ), 
    targets
  )




@fn.composed(maybe(fn._0), fn.search(r'^Successfully built ([a-f0-9]+)\s*$'))
def success(line):
  """
  >>> success('Blah')
  >>> success('Successfully built 1234\\n')
  '1234'
  """
 

@fn.composed(fn.first, fn.filter(None), fn.map(success))
def success_from_stream(stream):
  """
  
  >>> stream = iter(('Blah', 'Successfully built 1234\\n'))
  >>> success_from_stream(stream)
  '1234'
  """

 

def highlight(container, colors = rainbow()):
  color_fn = next(colors)
  def highlight_(msg):
    print color_fn( container.name) + " | " + msg
  return highlight_


@curry
def parse_and_show(show_fn, container, stream):
  """
  >>> from collections import namedtuple
  >>> stream = iter([dict(stream="hi mom"), dict(stream="hi world"), dict(stream='Successfully built 1234\\n')])
  >>> stream = [dict(stream="hi mom"), dict(stream="hi world"), dict(stream='Successfully built 1234\\n')]
  
  >>> container = namedtuple('Container', 'name')('blah')
  >>> show2(container, stream)
  blah | hi mom
  blah | hi world
  blah | Successfully built 1234
  <BLANKLINE>
  (Container(name='blah'), '1234')
  """
  f = compose(
    fn.tap(show_fn(container)),
    partial(string.strip, chars='\n'), 
    switch,
    json.loads
  )
   
  return container, success_from_stream(fmap(f,stream))


def switch(rec):

  if 'stream' in rec:
    return rec['stream']

  elif 'status' in rec:
    if rec['status'].startswith('Downloading'):
      term = '\r'
    else:
      term = '\n'

    return '[STATUS] {0}: {1}{2}'.format(
      rec.get('id', ''), 
      rec['status'],
      term
    )
  elif 'error' in rec:
    return '[ERROR] {0}\n'.format(rec['errorDetail']['message'])
  else:
    return rec
