from __future__ import absolute_import

from collections import namedtuple

from . import build, commits, container, dependencies, docker, push


class Shipwright(object):
    def __init__(self, config, source_control, docker_client, tags):
        self.source_control = source_control
        self.docker_client = docker_client
        self.namespace = config['namespace']
        self.config = config
        self.tags = tags

    def containers(self):
        return container.list_containers(
            self.namespace,
            self.config.get('names', {}),
            self.source_control.working_dir,
        )

    def targets(self):
        client = self.docker_client
        repo = self.source_control

        containers = self.containers()
        docker_tags = docker.tags_from_containers(client, containers)
        paths = [c.dir_path for c in containers]
        cci = commits.container_commit_info(repo, docker_tags, paths)
        last_built_ref, last_built_rel, current_rels = cci

        # [[Container], [Tag], [Int], [Int]] -> [Target]
        return [
            Target(container, built_ref, built_rel, current_rel, None)

            for container, built_ref, built_rel, current_rel in zip(
                containers, last_built_ref, last_built_rel, current_rels,
            )

            if current_rel is not None
        ]

    def build(self, specifiers):
        tree = dependencies.eval(specifiers, self.targets())
        info = self._get_build_info(tree)
        return self.build_tree(tree, info)

    def _get_build_info(self, tree):
        this_ref_str = commits.hexsha(self.source_control.commit())
        current, targets = dependencies.needs_building(tree)

        extra = [t._replace(last_built_ref=this_ref_str) for t in targets]

        return {
            'this_ref_str': this_ref_str,
            'current': current,
            'all_images': current + extra,
            'targets': targets,
        }

    def build_tree(self, tree, info):
        branch = self.source_control.active_branch.name
        current = info['current']
        this_ref_str = info['this_ref_str']
        targets = info['targets']
        all_images = info['all_images']

        for c in current:
            # these containers weren't effected by the latest git changes
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

        # now that we're built and tagged all the images with git commit,
        # (either during the process of building or forwarding the tag)
        # tag all containers with the branch name
        for tag in [branch] + self.tags:
            for image in all_images:
                yield docker.tag_container(
                    self.docker_client,
                    image,
                    tag,
                )

    def push(self, specifiers, build=True):
        """
        Pushes the latest images for the current branch to the repository.

        """
        branch = self.source_control.active_branch.name
        tree = dependencies.eval(specifiers, self.targets())

        if build:
            info = self._get_build_info(tree)
            for evt in self.build_tree(tree, info):
                yield evt
            tree = dependencies.make_tree(info['all_images'])

        tags = [branch] + self.tags
        names_and_tags = []
        for dep in dependencies.brood(tree):
            names_and_tags.append((dep.name, dep.last_built_ref))
            for tag in tags:
                names_and_tags.append((dep.name, tag))

        for evt in push.do_push(self.docker_client, names_and_tags):
            yield evt


_Target = namedtuple('Target', [
    'container', 'last_built_ref', 'last_built_rel', 'current_rel',
    'children',
])


class Target(_Target):
    @property
    def name(self):
        return self.container.name

    @property
    def short_name(self):
        return self.container.short_name

    @property
    def dir_path(self):
        return self.container.dir_path

    @property
    def parent(self):
        return self.container.parent

    @property
    def path(self):
        return self.container.path


del _Target
