from __future__ import absolute_import

from collections import namedtuple

import git

from . import container, docker


def _hexsha(ref):
    if ref is not None:
        return ref.hexsha[:12]


def _max_commit(commit_map, commits):
    # return the pair (tag, relative_commit)
    if commits:
        rel_commits = ((c, commit_map[c]) for c in commits if c in commit_map)
        try:
            return max(rel_commits)
        except ValueError:
            pass
    return None, -1


def _last_commit(repo, path):
    for commit in repo.iter_commits(paths=path, max_count=1):
        return commit


def _last_commit_relative(repo, commit_map, path):
    tag = _last_commit(repo, path)
    if tag is not None:
        return commit_map[_hexsha(tag)]


def _container_commit_info(repo, docker_tags, paths):
    commits = reversed(list(repo.iter_commits(None)))
    commit_map = {_hexsha(rev): i for i, rev in enumerate(commits)}
    latest_commits = [_max_commit(commit_map, tag) for tag in docker_tags]
    last_built_ref, last_built_rel = zip(*latest_commits)
    current_rels = [_last_commit_relative(repo, commit_map, p) for p in paths]
    return last_built_ref, last_built_rel, current_rels

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

    def targets(self, docker_client):
        client = docker_client
        repo = self._repo

        containers = container.list_containers(
            self._namespace,
            self._name_map,
            self.path,
        )

        docker_tags = docker.tags_from_containers(client, containers)
        paths = [c.dir_path for c in containers]
        cci = _container_commit_info(repo, docker_tags, paths)
        last_built_ref, last_built_rel, current_rels = cci

        return [
            Target(c, built_ref, built_rel, current_rel, None)

            for c, built_ref, built_rel, current_rel in zip(
                containers, last_built_ref, last_built_rel, current_rels,
            )

            if current_rel is not None
        ]
