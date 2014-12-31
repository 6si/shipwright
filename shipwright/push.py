import json

from .fn import (
  compose,  curry,  fmap, flat_map, merge
)

@curry
def do_push(client, images):
  return flat_map(push(client), images)
  
@curry
def push(client, (image, tag)):
  return fmap(
    compose(
      merge(dict(event="push", image=image)),
      json.loads,
    ),
    client.push(
      image,
      tag, 
      stream=True
    )
  )
