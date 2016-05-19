from __future__ import absolute_import

import os

from .compat import json_loads
from .fn import merge
from .tar import mkcontext


def do_build(client, git_rev, targets):
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

    for target in targets:
        for evt in build(client, git_rev, target):
            yield evt


def build(client, git_rev, container):
    """
    builds the given container tagged with <git_rev> and ensures that
    it depends on it's parent if it's part of this build group (shares
    the same namespace)
    """

    merge_config = {
        'event': 'build_msg',
        'container': container,
        'rev': git_rev,
    }

    def process_event_(evt):
        evt_parsed = json_loads(evt)
        return merge(merge_config, evt_parsed)

    build_evts = client.build(
        fileobj=mkcontext(git_rev, container.path),
        rm=True,
        custom_context=True,
        stream=True,
        tag='{0}:{1}'.format(container.name, git_rev),
        dockerfile=os.path.basename(container.path),
    )

    return (process_event_(evt) for evt in build_evts)
