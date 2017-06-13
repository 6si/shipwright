from __future__ import absolute_import

import os
import sys
import traceback

from docker import errors as d_errors
from requests import exceptions as requests_exceptions

from . import compat, docker, push, tar


def pull(client, *args, **kwargs):
    try:
        for evt in client.pull(*args, **kwargs):
            yield compat.json_loads(evt)
    except d_errors.NotFound as e:
        yield docker.error(e.explanation)


class PullFailedException(Exception):
    pass


class CacheMissException(Exception):
    pass


_FAILED = object()


class NoCache(object):
    def __init__(self, docker_client):
        self.docker_client = docker_client
        self._pulled_images = {}

    def _pull_cache(self, image):
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

    def build(self, parent_ref, image):
        repo = image.name
        tag = image.ref
        client = self.docker_client

        try:
            for evt in self._pull_cache(image):
                yield evt
        except CacheMissException:
            pass
        else:
            return

        # pull the parent if it has not been built because Docker-py fails
        # to send the correct credentials in the build command.
        if parent_ref:
            try:
                for evt in self._pull(image.parent, parent_ref):
                    yield evt
            except PullFailedException:
                pass

        build_evts = client.build(
            fileobj=tar.mkcontext(parent_ref, image.path),
            rm=True,
            custom_context=True,
            stream=True,
            tag='{0}:{1}'.format(image.name, image.ref),
            dockerfile=os.path.basename(image.path),
        )

        for evt in build_evts:
            yield compat.json_loads(evt)

        self._pulled_images[(repo, tag)] = True

    def _pull(self, repo, tag):
        already_pulled = self._pulled_images.get((repo, tag), False)
        if already_pulled is _FAILED:
            raise PullFailedException()

        if already_pulled:
            return

        client = self.docker_client

        failed = False
        pull_evts = pull(
            client,
            repository=repo,
            tag=tag,
            stream=True,
        )
        for event in pull_evts:
            if 'error' in event:
                event['warn'] = event['error']
                del event['error']
                failed = True
            yield event

        if failed:
            self._pulled_images[(repo, tag)] = _FAILED
            raise PullFailedException()

        self._pulled_images[(repo, tag)] = True


class Cache(NoCache):
    def _pull_cache(self, image):
        pull_events = self._pull(repo=image.name, tag=image.ref)
        try:
            for evt in pull_events:
                yield evt
        except PullFailedException:
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
        if manifest is None:
            msg = 'manifest does not exist, did the image fail to build?'
            yield docker.error(msg)
            return
        try:
            self.drc.put_manifest(name, ref, manifest)
        except requests_exceptions.HTTPError:
            msg = traceback.format_exception(*sys.exc_info())
            yield docker.error(msg)
        else:
            yield {}

    def _pull_cache(self, image):
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
