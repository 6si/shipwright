from __future__ import absolute_import

import os

from . import docker
from .compat import json_loads
from .tar import mkcontext


def _merge(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d


def do_build(client, build_ref, targets):
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

    build_index = {t.container.name: t.ref for t in targets}

    for target in targets:
        parent_ref = None
        if target.parent:
            parent_ref = build_index.get(target.parent)
        for evt in build(client, parent_ref, target):
            yield evt


def build(client, parent_ref, container):
    """
    builds the given container tagged with <build_ref> and ensures that
    it depends on it's parent if it's part of this build group (shares
    the same namespace)
    """

    merge_config = {
        'event': 'build_msg',
        'container': container,
        'rev': container.ref,
    }

    def process_event_(evt):
        evt_parsed = json_loads(evt)
        return _merge(merge_config, evt_parsed)

    built_tags = docker.last_built_from_docker(client, container.name)
    if container.ref in built_tags:
        return []

    build_evts = client.build(
        fileobj=mkcontext(parent_ref, container.path),
        rm=True,
        custom_context=True,
        stream=True,
        tag='{0}:{1}'.format(container.name, container.ref),
        dockerfile=os.path.basename(container.path),
    )

    return (process_event_(evt) for evt in build_evts)
