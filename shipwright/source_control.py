from __future__ import absolute_import

from collections import namedtuple

import git

from . import image


def _last_commit(repo, paths):
    commits = repo.iter_commits(
        paths=paths,
        max_count=1,
        topo_order=True,
    )
    for commit in commits:
        return commit


_Target = namedtuple('Target', ['image', 'ref', 'children'])


class Target(_Target):
    @property
    def name(self):
        return self.image.name

    @property
    def short_name(self):
        return self.image.short_name

    @property
    def parent(self):
        return self.image.parent

    @property
    def path(self):
        return self.image.path


del _Target


def _image_parents(index, image):
    while image:
        yield image
        image = index.get(image.parent)


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
        repo = self._repo
        if repo.head.is_detached:
            return []

        branch = repo.active_branch.name
        return [branch]

    def this_ref_str(self):
        return _hexsha(self._repo.commit())

    def targets(self):
        repo = self._repo

        images = image.list_images(
            self._namespace,
            self._name_map,
            self.path,
        )
        c_index = {c.name: c for c in images}

        targets = []

        for c in images:
            paths = [p.dir_path for p in _image_parents(c_index, c)]
            ref = _hexsha(_last_commit(repo, paths))
            targets.append(Target(image=c, ref=ref, children=None))

        return targets
