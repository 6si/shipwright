from __future__ import absolute_import

from collections import namedtuple

import git

from . import container


def _last_commit(repo, paths):
    commits = repo.iter_commits(
        paths=paths,
        max_count=1,
        topo_order=True,
    )
    for commit in commits:
        return commit


_Target = namedtuple('Target', ['container', 'ref', 'children'])


class Target(_Target):
    @property
    def name(self):
        return self.container.name

    @property
    def short_name(self):
        return self.container.short_name

    @property
    def parent(self):
        return self.container.parent

    @property
    def path(self):
        return self.container.path


del _Target


def _container_parents(index, container):
    while container:
        yield container
        container = index.get(container.parent)


def _hexsha(ref):
    if ref is not None:
        return ref.hexsha[:12]


class GitSourceControl(object):
    def __init__(self, path, namespace, name_map):
        self.path = path
        self._namespace = namespace
        self._name_map = name_map
        self._repo = git.Repo(path)

    def default_tags(self):
        branch = self._repo.active_branch.name
        return [branch]

    def this_ref_str(self):
        return _hexsha(self._repo.commit())

    def targets(self):
        repo = self._repo

        containers = container.list_containers(
            self._namespace,
            self._name_map,
            self.path,
        )
        c_index = {c.name: c for c in containers}

        targets = []

        for c in containers:
            paths = [p.dir_path for p in _container_parents(c_index, c)]
            ref = _hexsha(_last_commit(repo, paths))
            targets.append(Target(container=c, ref=ref, children=None))

        return targets
