from __future__ import absolute_import

from . import compat
from .fn import curry, flat_map


@curry
def do_push(client, images):
    return flat_map(push(client), images)


@curry
def push(client, image_tag):
    image, tag = image_tag

    def fmt(s):
        d = compat.json_loads(s)
        d.update({'event': 'push', 'image': image})
        return d

    results = client.push(image, tag, stream=True)
    return [fmt(r) for r in results]
