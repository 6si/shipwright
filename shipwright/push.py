from __future__ import absolute_import

from . import compat


def do_push(client, images):
    for image in images:
        for evt in push(client, image):
            yield evt


def push(client, image_tag):
    image, tag = image_tag

    def fmt(s):
        d = compat.json_loads(s)
        d.update({'event': 'push', 'image': image})
        return d

    results = client.push(image, tag, stream=True)
    return [fmt(r) for r in results]
