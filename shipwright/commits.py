from __future__ import absolute_import

from .fn import curry, juxt, maybe, identity

# Tag = str
# git.Repo -> {Tag:Int}
def mkmap(repo):
  """
  Return a function suitable for mapping symbolic names to a relative number.
  """
  return { hexsha(rev):i  for i, rev in enumerate(commits(repo)) }.get


# if it's a ref return the first 12 hex digits, if it's None return None
#  git.Ref | None -> String | None
hexsha = maybe(lambda ref: ref.hexsha[:12])


# git.Repo -> [git.Commit]
def commits(repo):
  return reversed(list(repo.iter_commits()))

@curry
def relative_commit(commit_map, tag):
  return commit_map(hexsha(tag))


@curry
def max_commit(commit_map, commits):
  # return the pair (tag, relative_commit)
  if commits:
    return max(map(juxt(commit_map,identity), commits))[::-1] #reverse the list
  else:
    return [None, -1]

@curry
def last_commit(repo,  path):
  try:
    return next(repo.iter_commits(paths=path, max_count=1))
  except StopIteration:
    return None

@curry
def last_commit_relative(repo, commit_map, path):
  return relative_commit(commit_map, last_commit(repo,path))



@curry
def last_built(commit_map, commits):
  if commits:
    return max(map(commit_map.get, commits)) or -1
  else:
    return -1


