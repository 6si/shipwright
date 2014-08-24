from __future__ import absolute_import
from shipwright import fn
from shipwright.fn import _1, identity, curry, compose,  flatten



@fn.composed(_1, fn.split(':'))
def key_from_image_name(image_name):
  """
  >>> key_from_image_name('shipwright/blah:1234')
  '1234'
  """

# DockerTag = str
# {} -> [DockerTag]
@fn.composed(fn.map(key_from_image_name), fn.getitem('RepoTags'))
def key_from_image_info(image_info_dict):
  """
  >>> key_from_image_info({ u'RepoTags': [u'shipwright/base:6e29823388f8', u'shipwright/base:test']})
  ['6e29823388f8', 'test']
  """

@curry
def last_built_from_docker(client, name):
  return compose(
    list,
    flatten,
    fn.fmap(key_from_image_info) # {.. 'RepoTags': [...]} -> [...]
  )(client.images(name))

# client -> [containers] -> [[DockerTag]]
@curry
def tags_from_containers(client, containers):
  return map(
    compose(last_built_from_docker(client), fn.getattr('name')),
    containers
  )


def tag_containers(client, containers,  new_ref):
  
  tag = new_ref.replace('/','-')
  for container in containers:
    client.tag(
      container.name + ":" + container.last_built_ref, 
      container.name,
      tag=tag
    )
