from __future__ import absolute_import

import itertools
import time

from . import compat, docker


def do_push(client, images):
    push_results = [push(client, image) for image in images]
    for evt in itertools.chain.from_iterable(push_results):
        yield evt


def retry_gen(fn, max_attempts=3):
    for i in range(max_attempts):
        try:
            for v in fn():
                yield v
            return
        except Exception as e:
            msg = 'Exception: {}, Attempt: {}'.format(e, i)
            yield docker.warn(msg)
        time.sleep(0.6 * (2 ** i))

    for v in fn():
        yield v


def push(client, image_tag):
    image, tag = image_tag
    extra = {'event': 'push', 'image': image}

    def _push():
        return client.push(image, tag, stream=True)

    for evt in retry_gen(_push):
        d = compat.json_loads(evt)
        d.update(extra)
        yield d
