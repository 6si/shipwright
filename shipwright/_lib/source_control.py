from __future__ import absolute_import

import binascii
import fnmatch
import hashlib
import os.path
import re
from collections import namedtuple

import git

from . import image


class Mode(object):
    pass


AUTO = Mode()
GIT = Mode()


SOURCE_CONTROL = [
    ('.git', GIT),
]


class SourceControlNotFound(Exception):
    def __init__(self):
        possible_values = ', '.join([x for x, _ in SOURCE_CONTROL])
        msg = 'Cannot find directory in {}'.format(possible_values)
        super(SourceControlNotFound, self).__init__(msg)


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
    else:
        return 'g' * 12


def _hash_blob(blob):
    if blob.hexsha != blob.NULL_HEX_SHA:
        return blob.hexsha
    else:
        return blob.repo.git.hash_object(blob.abspath)


def _hash_blobs(blobs):
    return [(b.path, _hash_blob(b)) for b in blobs if b]


def _abspath(repo_wd, path):
    return os.path.abspath(os.path.join(repo_wd, path))


def _in_paths(repo_wd, base_paths, path):
    wd = repo_wd
    p = _abspath(repo_wd, path)

    for base_path in base_paths:
        path_pattern = _abspath(wd, base_path)
        if not re.match('[*?]', path_pattern):
            if p == path_pattern:
                return True
            extra = '*' if path_pattern.endswith(os.sep) else os.sep + '*'
            path_pattern += extra

        if fnmatch.fnmatch(p, path_pattern):
            return True
    return False


def _dirty_suffix(repo, base_paths=['.']):
    repo_wd = repo.working_dir
    diff = repo.head.commit.diff(None)
    a_hashes = _hash_blobs(d.a_blob for d in diff)
    b_hashes = _hash_blobs(d.b_blob for d in diff)

    u_files = repo.untracked_files
    untracked_hashes = [(path, repo.git.hash_object(path)) for path in u_files]

    hashes = sorted(a_hashes) + sorted(b_hashes + untracked_hashes)
    filtered_hashes = [
        (path, h) for path, h in hashes if _in_paths(repo_wd, base_paths, path)
    ]

    if not filtered_hashes:
        return ''

    digest = hashlib.sha256()
    for path, h in filtered_hashes:
        digest.update(path.encode('utf-8') + b'\0' + h.encode('utf-8'))
    return '-dirty-' + binascii.hexlify(digest.digest())[:12].decode('utf-8')


class SourceControl(object):
    pass


class GitSourceControl(SourceControl):
    mode = GIT

    def __init__(self, path, namespace, name_map):
        self.path = path
        self._namespace = namespace
        self._name_map = name_map
        self._repo = git.Repo(path)

    def is_dirty(self):
        repo = self._repo
        return bool(repo.untracked_files or repo.head.commit.diff(None))

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
            paths = sorted(frozenset.union(
                *(p.copy_paths for p in _image_parents(c_index, c))
            ))
            ref = (_hexsha(_last_commit(repo, paths)) +
                   _dirty_suffix(repo, paths))
            targets.append(Target(image=c, ref=ref, children=None))

        return targets


def get_mode(path):
    for scm_dir, mode in SOURCE_CONTROL:
        if os.path.isdir(os.path.join(path, scm_dir)):
            return mode
    raise SourceControlNotFound()


def source_control(path, namespace, name_map, mode=None):
    if mode is None:
        mode = AUTO
    assert isinstance(mode, Mode)
    the_mode = mode if mode is not AUTO else get_mode(path)
    for cls in SourceControl.__subclasses__():
        if cls.mode is the_mode:
            return cls(path, namespace, name_map)
