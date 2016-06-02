from __future__ import absolute_import


def hexsha(ref):
    if ref is not None:
        return ref.hexsha[:12]


# git.Repo -> [git.Commit]
def _commits(repo):
    return reversed(list(repo.iter_commits(None)))


def _max_commit(commit_map, commits):
    # return the pair (tag, relative_commit)
    if commits:
        rel_commits = ((c, commit_map[c]) for c in commits if c in commit_map)
        return max(rel_commits)
    else:
        return None, -1


def _last_commit(repo, path):
    for commit in repo.iter_commits(paths=path, max_count=1):
        return commit


def _last_commit_relative(repo, commit_map, path):
    tag = _last_commit(repo, path)
    if tag is not None:
        return commit_map[hexsha(tag)]


def container_commit_info(repo, docker_tags, paths):
    commit_map = {hexsha(rev): i for i, rev in enumerate(_commits(repo))}
    latest_commits = [_max_commit(commit_map, tag) for tag in docker_tags]
    last_built_ref, last_built_rel = zip(*latest_commits)
    current_rels = [_last_commit_relative(repo, commit_map, p) for p in paths]
    return last_built_ref, last_built_rel, current_rels
