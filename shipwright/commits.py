from __future__ import absolute_import

from .fn import curry, maybe, identity
from . import compat


# Tag = str
# git.Repo -> {Tag:Int}
def mkmap(repo, branch=None):
    """
    Return a function suitable for mapping symbolic names to a relative number.
    """
    return {hexsha(rev): i for i, rev in enumerate(commits(repo, branch))}.get


# if it's a ref return the first 12 hex digits, if it's None return None
#  git.Ref | None -> String | None
hexsha = maybe(lambda ref: ref.hexsha[:12])


# git.Repo -> [git.Commit]
def commits(repo, branch=None):
    return reversed(list(repo.iter_commits(branch)))


@curry
def relative_commit(commit_map, tag):
    return commit_map(hexsha(tag))


@curry
def max_commit(commit_map, commits):
    # return the pair (tag, relative_commit)
    if commits:
        def key(item):
            ident, c_map = item
            return (
                compat.python2_sort_key(c_map),
                compat.python2_sort_key(ident),
            )
        return max(([identity(c), commit_map(c)] for c in commits), key=key)
    else:
        return [None, -1]


@curry
def last_commit(repo, path):
    try:
        return next(repo.iter_commits(paths=path, max_count=1))
    except StopIteration:
        return None


@curry
def last_commit_relative(repo, commit_map, path):
    return relative_commit(commit_map, last_commit(repo, path))


@curry
def last_built(commit_map, commits):
    if commits:
        return max(map(commit_map.get, commits)) or -1
    else:
        return -1
