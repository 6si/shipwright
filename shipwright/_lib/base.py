from __future__ import absolute_import

from . import build, dependencies
from .msg import BuildComplete


class Shipwright(object):
    def __init__(self, source_control, docker_client, tags, cache):
        self.source_control = source_control
        self.docker_client = docker_client
        self.tags = tags
        self._cache = cache

    def targets(self):
        return self.source_control.targets()

    def build(self, build_targets):
        targets = dependencies.eval(build_targets, self.targets())
        this_ref_str = self.source_control.this_ref_str()
        return self._build(this_ref_str, targets)

    def _build(self, this_ref_str, targets):
        client = self.docker_client
        ref = this_ref_str
        tags = self.source_control.default_tags() + self.tags + [this_ref_str]
        for evt in build.do_build(client, ref, targets, self._cache):
            if isinstance(evt, BuildComplete):
                target = evt.target
                for tag_evt in self._cache.tag([target], tags):
                    yield tag_evt
            yield evt

    def images(self, build_targets):
        for target in dependencies.eval(build_targets, self.targets()):
            yield {
                'stream': '{t.name}:{t.ref}'.format(t=target),
                'event': 'log',
            }

    def push(self, build_targets, no_build=False):
        """
        Pushes the latest images to the repository.
        """
        targets = dependencies.eval(build_targets, self.targets())
        this_ref_str = self.source_control.this_ref_str()
        tags = self.source_control.default_tags() + self.tags + [this_ref_str]

        if no_build:
            for evt in self._cache.push(targets, tags):
                yield evt
            return

        for evt in self._build(this_ref_str, targets):
            if isinstance(evt, BuildComplete):
                for push_evt in self._cache.push([evt.target], tags):
                    yield push_evt
            yield evt
