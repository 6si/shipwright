from __future__ import absolute_import

import functools
from collections import namedtuple

from . import build, commits, dependencies, docker, push
from .container import containers as list_containers
from .container import container_name


class Shipwright(object):
    def __init__(self, config, source_control, docker_client):
        self.source_control = source_control
        self.docker_client = docker_client
        self.namespace = config['namespace']
        self.config = config

    def containers(self):
        cn = functools.partial(
            container_name,
            self.namespace,
            self.config.get('names', {}),
            self.source_control.working_dir,
        )
        return list_containers(
            cn,
            self.source_control.working_dir,
        )

    def targets(self):
        client = self.docker_client

        containers = self.containers()

        commit_map = commits.mkmap(self.source_control)

        max_commit = functools.partial(
            commits.max_commit,
            commit_map,
        )

        last_built_ref, last_built_rel = zip(*map(
            max_commit,
            docker.tags_from_containers(client, containers),  # list of tags
        ))

        current_rel = [
            commits.last_commit_relative(
                self.source_control,
                commit_map,
                c.dir_path,
            )
            for c in containers
        ]

        # [[Container], [Tag], [Int], [Int]] -> [Target]
        return [
            Target(container, built_ref, built_rel, current_rel, None)

            for container, built_ref, built_rel, current_rel in zip(
                containers, last_built_ref, last_built_rel, current_rel,
            )

            if current_rel is not None
        ]

    def build(self, specifiers):
        tree = dependencies.eval(specifiers, self.targets())
        return self.build_tree(tree)

    def build_tree(self, tree):
        branch = self.source_control.active_branch.name
        this_ref_str = commits.hexsha(self.source_control.commit())

        current, targets = dependencies.needs_building(tree)

        if current:
            # these containers weren't effected by the latest git changes
            # so we'll fast forward tag them with the build id. That way  any
            # of the containers that do need to be built can refer
            # to the skiped ones by user/image:<last_built_ref> which makes
            # them part of the same group.
            events = docker.tag_containers(
                self.docker_client,
                current,
                this_ref_str,
            )
            for evt in events:
                yield evt

        # what needs building
        for evt in build.do_build(self.docker_client, this_ref_str, targets):
            yield evt

        all_images = current + [
            t._replace(last_built_ref=this_ref_str)
            for t in targets
        ]

        # now that we're built and tagged all the images with git commit,
        # (either during the process of building or forwarding the tag)
        # tag all containers with the branch name
        branch_events = docker.tag_containers(
            self.docker_client,
            all_images,
            branch,
        )
        for evt in branch_events:
            yield evt

        latest_events = docker.tag_containers(
            self.docker_client,
            all_images,
            'latest',
        )
        for evt in latest_events:
            yield evt

        raise StopIteration(all_images)

    def push(self, specifiers, build=True):
        """
        Pushes the latest images for the current branch to the repository.

        """
        branch = self.source_control.active_branch.name

        def push_tree(tree):
            flat_tree = expand(branch, tree)
            names_and_tags = [(x.name, x.last_built_ref) for x in flat_tree]
            return push.do_push(self.docker_client, names_and_tags)

        tree = dependencies.eval(specifiers, self.targets())

        if build:
            return bind(self.build_tree, push_tree, tree)
        else:
            return push_tree(tree)


def expand(branch, tree):
    """
    Flattens the tree to the list and triples each entry.

    Ex.

    > expand(make_tree([Target(..., last_built_ref='c1234567890a'...)]))
    [
        Target(..., last_built_ref='c1234567890a'),
        Target(..., last_built_ref='develop'...),
        Target(..., last_built_ref='latest'...),
    ]

    """
    return [
        [
            d,
            d._replace(last_built_ref=branch),
            d._replace(last_built_ref='latest'),
        ]
        for d in dependencies.brood(tree)
    ]


# (Tree -> [Target]) -> (Tree -> [Target]) -> [Target]
def bind(a, b, tree):
    """
    Glues two Shipwright commands (functions) together.
    """

    iterator = a(tree)

    while True:
        try:
            yield next(iterator)
        except StopIteration as e:
            x1 = e.args[0]
            for evt in b(dependencies.make_tree(x1)):
                yield evt
            break


_Target = namedtuple('Target', [
    'container', 'last_built_ref', 'last_built_rel', 'current_rel',
    'children',
])


class Target(_Target):
    @property
    def name(self):
        return self.container.name

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
