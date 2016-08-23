from __future__ import absolute_import

import os

from . import docker
from .compat import json_loads
from .tar import mkcontext


def _merge(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d


def do_build(client, build_ref, targets, pull_cache):
    """
    Generic function for building multiple images while
    notifying a callback function with output produced.

    Given a list of targets it builds the target with the given
    build_func while streaming the output through the given
    show_func.

    Returns an iterator of (image, docker_image_id) pairs as
    the final output.

    Building an image can take sometime so  the results are returned as
    an iterator in case the caller wants to use restults in between builds.

    The consequences of this is you must either call it as part of a for loop
    or pass it to a function like list() which can consume an iterator.

    """

    build_index = {t.image.name: t.ref for t in targets}

    for target in targets:
        parent_ref = None
        if target.parent:
            parent_ref = build_index.get(target.parent)
        for evt in build(client, parent_ref, target, pull_cache):
            yield evt


def build(client, parent_ref, image, pull_cache):
    """
    builds the given image tagged with <build_ref> and ensures that
    it depends on it's parent if it's part of this build group (shares
    the same namespace)
    """

    merge_config = {
        'event': 'build_msg',
        'target': image,
        'rev': image.ref,
    }

    def process_event_(evt):
        evt_parsed = json_loads(evt)
        return _merge(merge_config, evt_parsed)

    built_tags = docker.last_built_from_docker(client, image.name)
    if image.ref in built_tags:
        return

    if pull_cache:
        pull_evts = client.pull(
            repository=image.name,
            tag=image.ref,
            stream=True,
        )

        failed = False
        for evt in pull_evts:
            event = process_event_(evt)
            if 'error' in event:
                event['warn'] = event['error']
                del event['error']
                failed = True
            yield event

        if not failed:
            return

    build_evts = client.build(
        fileobj=mkcontext(parent_ref, image.path),
        rm=True,
        custom_context=True,
        stream=True,
        tag='{0}:{1}'.format(image.name, image.ref),
        dockerfile=os.path.basename(image.path),
    )

    for evt in build_evts:
        yield process_event_(evt)
