from __future__ import absolute_import

from . import build, dependencies, docker, push


class Shipwright(object):
    def __init__(self, source_control, docker_client, tags):
        self.source_control = source_control
        self.docker_client = docker_client
        self.tags = tags

    def targets(self):
        return self.source_control.targets(self.docker_client)

    def build(self, specifiers):
        tree = dependencies.eval(specifiers, self.targets())
        info = self._get_build_info(tree)
        return self.build_tree(tree, info)

    def _get_build_info(self, tree):
        this_ref_str = self.source_control.this_ref_str()
        current, targets = dependencies.needs_building(tree)

        extra = [t._replace(last_built_ref=this_ref_str) for t in targets]

        return {
            'this_ref_str': this_ref_str,
            'current': current,
            'all_images': current + extra,
            'targets': targets,
        }

    def build_tree(self, tree, info):
        current = info['current']
        this_ref_str = info['this_ref_str']
        targets = info['targets']
        all_images = info['all_images']

        for c in current:
            # these containers weren't effected by the latest changes
            # so we'll fast forward tag them with the build id. That way  any
            # of the containers that do need to be built can refer
            # to the skiped ones by user/image:<last_built_ref> which makes
            # them part of the same group.
            yield docker.tag_container(
                self.docker_client,
                c,
                this_ref_str,
            )

        # what needs building
        for evt in build.do_build(self.docker_client, this_ref_str, targets):
            yield evt

        # now that we're built and tagged all the images.
        # (either during the process of building or forwarding the tag)
        # tag all containers with the human readable tags.
        for tag in self.source_control.default_tags() + self.tags:
            for image in all_images:
                yield docker.tag_container(
                    self.docker_client,
                    image,
                    tag,
                )

    def push(self, specifiers, build=True):
        """
        Pushes the latest images to the repository.
        """
        tree = dependencies.eval(specifiers, self.targets())

        if build:
            info = self._get_build_info(tree)
            for evt in self.build_tree(tree, info):
                yield evt
            tree = dependencies.make_tree(info['all_images'])

        tags = self.source_control.default_tags() + self.tags
        names_and_tags = []
        for dep in dependencies.brood(tree):
            names_and_tags.append((dep.name, dep.last_built_ref))
            for tag in tags:
                names_and_tags.append((dep.name, tag))

        for evt in push.do_push(self.docker_client, names_and_tags):
            yield evt
