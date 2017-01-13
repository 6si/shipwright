from __future__ import absolute_import

import itertools

from . import compat


def chunks(iterable, chunk_size):
    result = []
    for item in iterable:
        result.append(item)
        if len(result) == chunk_size:
            yield result
            result = []
    if len(result) > 0:
        yield result


def do_push(client, images):
    # Docker seems to limit us to about 20 requests in one go.
    for image_chunk in chunks(images, 20):
        push_results = [push(client, image) for image in image_chunk]

        for evt in itertools.chain.from_iterable(push_results):
            yield evt


def push(client, image_tag):
    image, tag = image_tag
    extra = {'event': 'push', 'image': image}

    for evt in client.push(image, tag, stream=True):
        d = compat.json_loads(evt)
        d.update(extra)
        yield d
