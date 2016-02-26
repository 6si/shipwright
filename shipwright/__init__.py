from __future__ import absolute_import

from collections import namedtuple

from . import build
from . import push
from . import purge
from . import fn
from . import commits
from . import docker

from . import dependencies

from . import query

from .container import containers as list_containers, container_name
from .fn import curry, compose


class Shipwright(object):
    def __init__(self, config, source_control, docker_client):
        self.source_control = source_control
        self.docker_client = docker_client
        self.namespace = config['namespace']
        self.config = config

    def containers(self):
        return list_containers(
            container_name(
                self.namespace,
                self.config.get('names', {}),
                self.source_control.working_dir
            ),
            self.source_control.working_dir
        )

    def targets(self):
        client = self.docker_client

        containers = self.containers()

        commit_map = commits.mkmap(self.source_control)

        last_built_ref, last_built_rel = zip(*map(
            commits.max_commit(commit_map),
            docker.tags_from_containers(client, containers)  # list of tags
        ))

        current_rel = map(
            compose(
                commits.last_commit_relative(self.source_control, commit_map),
                fn.getattr('dir_path')
            ),
            containers
        )

        # [[Container], [Tag], [Int], [Int]] -> [Target]
        return [
            Target(container, built_ref, built_rel, current_rel, None)

            for container, built_ref, built_rel, current_rel in zip(
                containers, last_built_ref, last_built_rel, current_rel
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
            "latest",
        )
        for evt in latest_events:
            yield evt

        raise StopIteration(all_images)

    def purge(self, specifiers):
        """
        Removes all stale images.

        A stale image is an image that is not the latest of at
        least one branch.
        """

        containers = self.containers()
        d = query.dataset(self.source_control, self.docker_client, containers)

        stale_images = d.query('''
      select image.image, tag
      from
        image
        left join latest_commit on latest_commit.commit = image.tag
      where latest_commit.commit is null
    ''')

        return purge.do_purge(self.docker_client, stale_images)

    def push(self, specifiers, build=True):
        """
        Pushes the latest images for the current branch to the repository.

        """
        branch = self.source_control.active_branch.name
        tree = dependencies.eval(specifiers, self.targets())

        push_tree = compose(
            push.do_push(self.docker_client),
            # [Target] -> [[ImageName, Tag]]
            fn.map(fn.juxt(fn.getattr('name'), fn.getattr('last_built_ref'))),
            expand(branch)
        )

        if build:
            return bind(self.build_tree, push_tree, tree)
        else:
            return push_tree(tree)

    def z_push(self, tree):
        containers = dependencies.brood(tree)

        branch = self.source_control.active_branch.name
        d = query.dataset(self.source_control, self.docker_client, containers)

        images = d.query("""
      select image, commit
      from latest_commit
      where
        branch = ?0 and image is not null
    """).execute(branch)
        return push.do_push(self.docker_client, images)


@curry
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
    return fn.flat_map(
        fn.juxt(
            fn.identity,
            fn.replace(last_built_ref=branch),
            fn.replace(last_built_ref="latest")
        ),
        dependencies.brood(tree)
    )


def unit(tree):
    return tree, iter(())


# (Tree -> [Target]) -> (Tree -> [Target]) -> [Target]
@curry
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
