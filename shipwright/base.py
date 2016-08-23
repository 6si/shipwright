from __future__ import absolute_import

from . import build, dependencies, docker, push


class Shipwright(object):
    def __init__(self, source_control, docker_client, tags, pull_cache=False):
        self.source_control = source_control
        self.docker_client = docker_client
        self.tags = tags
        self._pull_cache = pull_cache

    def targets(self):
        return self.source_control.targets()

    def build(self, build_targets):
        targets = dependencies.eval(build_targets, self.targets())
        this_ref_str = self.source_control.this_ref_str()
        return self._build(this_ref_str, targets)

    def _build(self, this_ref_str, targets):
        client = self.docker_client
        pull_cache = self._pull_cache
        ref = this_ref_str
        for evt in build.do_build(client, ref, targets, pull_cache):
            yield evt

        # now that we're built and tagged all the images.
        # (either during the process of building or forwarding the tag)
        # tag all images with the human readable tags.
        tags = self.source_control.default_tags() + self.tags + [this_ref_str]
        for image in targets:
            for tag in tags:
                yield docker.tag_image(
                    self.docker_client,
                    image,
                    tag,
                )

    def push(self, build_targets, no_build=False):
        """
        Pushes the latest images to the repository.
        """
        targets = dependencies.eval(build_targets, self.targets())
        this_ref_str = self.source_control.this_ref_str()

        if not no_build:
            for evt in self._build(this_ref_str, targets):
                yield evt

        this_ref_str = self.source_control.this_ref_str()
        tags = self.source_control.default_tags() + self.tags + [this_ref_str]
        names_and_tags = set()
        for image in targets:
            names_and_tags.add((image.name, image.ref))
            for tag in tags:
                names_and_tags.add((image.name, tag))

        for evt in push.do_push(self.docker_client, sorted(names_and_tags)):
            yield evt
