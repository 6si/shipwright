from __future__ import absolute_import

import binascii
import hashlib
import os.path
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

def _hash_blob(blob):
    if blob.hexsha != blob.NULL_HEX_SHA:
        return blob.hexsha
    else:
        return blob.repo.git.hash_object(blob.abspath)

def _dirty_suffix(repo, base_paths = ['.']):
    abspath = lambda path: os.path.abspath(os.path.join(repo.working_dir, path))
    hash_blobs = lambda blobs: [(b.path, _hash_blob(b)) for b in blobs if b]
    in_paths = lambda path: any(abspath(path).startswith(abspath(base_path) + os.sep) for base_path in base_paths)

    diff = repo.head.commit.diff(None)
    a_hashes = hash_blobs(map(lambda d: d.a_blob, diff))
    b_hashes = hash_blobs(map(lambda d: d.b_blob, diff))
    untracked_hashes = [(path, repo.git.hash_object(path))
                        for path in repo.untracked_files]
    hashes = sorted(a_hashes) + sorted(b_hashes + untracked_hashes)
    filtered_hashes = [(path, hash_) for path, hash_ in hashes if in_paths(path)]

    if not filtered_hashes:
        return ''
    digest = hashlib.sha256()
    for path, hash_ in filtered_hashes:
        digest.update(path.encode('utf-8') + b'\0' + hash_.encode('utf-8'))
    return '-dirty-' + binascii.hexlify(digest.digest())[:12].decode("utf-8")

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
        return _hexsha(self._repo.commit()) + _dirty_suffix(self._repo)

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
            ref = _hexsha(_last_commit(repo, paths)) + _dirty_suffix(repo, paths)
            targets.append(Target(image=c, ref=ref, children=None))

        return targets
