import json
import string
from functools import partial


from . import fn

from .fn import apply,  compose, composed, curry, identity,juxt, maybe, fmap
from .tar import mkcontext

# (container->(str -> None)) -> (container -> stream) -> [targets] -> [(container, docker_image_id)] 
def do_build(show_func, client, git_rev, targets):
  """
  Generic function for building multiple containers while
  notifying a callback function with output produced.

  Given a list of targets it builds the target with the given
  build_func while streaming the output through the given
  show_func.

  Returns an iterator of (container, docker_image_id) pairs as 
  the final output.

  Building a container can take sometime so  the results are returned as 
  an iterator in case the caller wants to use restults in between builds.

  The consequences of this is you must either call it as part of a for loop
  or pass it to a function like list() which can consume an iterator.

  """
  return map(
    compose(
      apply(parse_and_show(show_func)), # (container,stream) => (container, docker_image_id)
      juxt(identity, build(client, git_rev)) # container => (container, stream)
    ), 
    targets
  )


@curry
def build(client, git_rev, container):
  """
  builds the given container tagged with <git_rev> and ensures that
  it depends on it's parent if it's part of this build group (shares
  the same namespace)
  """

  return client.build(
    fileobj = mkcontext(git_rev, container.dir_path),
    custom_context = True,
    stream=True,
    tag = '{0}:{1}'.format(container.name, git_rev)
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
    fn.tap(show_fn(container)), #'string' -> <side effect> -> 'string'
    partial(string.strip, chars='\n'), # 'string\n' -> 'string'
    switch, # {...} -> 'string\n'
    json.loads #'{...}' -> {...}
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
