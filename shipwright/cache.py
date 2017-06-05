from __future__ import absolute_import

import sys
import traceback

from docker import errors as d_errors
from requests import exceptions as requests_exceptions

from . import compat, docker, push


def pull(client, *args, **kwargs):
    try:
        for evt in client.pull(*args, **kwargs):
            yield compat.json_loads(evt)
    except d_errors.NotFound as e:
        yield {'error': e.explanation,
               'errorDetail': {'message': e.explanation}}


class CacheMissException(Exception):
    pass


class NoCache(object):
    def __init__(self, docker_client):
        self.docker_client = docker_client

    def pull_cache(self, image):
        raise CacheMissException()
        yield

    def tag(self, targets, tags):
        for image in targets:
            for tag in tags:
                yield docker.tag_image(
                    self.docker_client,
                    image,
                    tag,
                )

    def push(self, targets, tags):
        names_and_tags = set()
        for image in targets:
            names_and_tags.add((image.name, image.ref))
            for tag in tags:
                names_and_tags.add((image.name, tag))

        for evt in push.do_push(self.docker_client, sorted(names_and_tags)):
            yield evt

        names_and_tags = set()
        names_and_tags.add((image.name, image.ref))
        for tag in tags:
            names_and_tags.add((image.name, tag))

        for evt in push.do_push(self.docker_client, sorted(names_and_tags)):
            yield evt


class Cache(NoCache):
    def pull_cache(self, image):
        client = self.docker_client
        pull_evts = pull(
            client,
            repository=image.name,
            tag=image.ref,
            stream=True,
        )

        failed = False
        for event in pull_evts:
            if 'error' in event:
                event['warn'] = event['error']
                del event['error']
                failed = True
            yield event

        if failed:
            raise CacheMissException()


class DirectRegistry(NoCache):
    def __init__(self, docker_client, docker_registry):
        super(DirectRegistry, self).__init__(docker_client)
        self.drc = docker_registry
        self._cache = {}

    def _get_manifest(self, tag):
        name, ref = tag
        try:
            return self._cache[tag]
        except KeyError:
            try:
                m = self.drc.get_manifest(name, ref)
            except requests_exceptions.HTTPError:
                return None
            else:
                self._cache[tag] = m
                return m

    def _put_manifest(self, tag, manifest):
        name, ref = tag
        try:
            self.drc.put_manifest(name, ref, manifest)
        except requests_exceptions.HTTPError:
            msg = traceback.format_exception(*sys.exc_info())
            yield {'error': {'errorDetails': {'message': msg}}}
        else:
            yield {}

    def pull_cache(self, image):
        tag = (image.name, image.ref)
        if self._get_manifest(tag) is None:
            raise CacheMissException()
        return
        yield

    def tag(self, targets, tags):
        """
        A noop operation because we can't tag locally, if we don't have the
        built images
        """
        return
        yield

    def push(self, targets, tags):
        to_push = set()
        to_alias = []
        for image in targets:
            tag = (image.name, image.ref)
            manifest = self._get_manifest(tag)
            if manifest is not None:
                to_alias.append((tag, manifest))
            else:
                to_push.add(tag)

        sorted_to_push = sorted(to_push)
        for evt in push.do_push(self.docker_client, sorted_to_push):
            yield evt

        for tag in sorted_to_push:
            manifest = self._get_manifest(tag)
            to_alias.append((tag, manifest))

        for (name, ref), manifest in to_alias:
            for tag in tags:
                dest = (name, tag)
                extra = {
                    'event': 'alias',
                    'old_image': name + ':' + ref,
                    'repository': name,
                    'tag': tag,
                }
                for evt in self._put_manifest(dest, manifest):
                    evt.update(extra)
                    yield evt
