from . import docker
from . import fn

from .fn import compose


# Repo -> [GitBranch] -> [Container] -> [[tags]]
def _stale_images(repo, branches, containers,  tags_by_container):
  # [Branch] -> [(string -> Int)]
  maps = map(
    lambda b: commits.mkmap(repo, b), 
    branches
  )

  # [(string -> Int)] -> [[Tag]] -> [[(last_built, relative_id)]]
  z = map(
    lambda commit_map:last_built(commit_map, tags_by_container),
    maps
  )

  #([Int],[Int]) -> [(Int,Int)]
  a = map(
    lambda t: max(zip(*reversed(t))),
    z
  )

  branch_set = map(ttag, branches) + ['latest']
  
  #for branch, ref in zip(branch_set,a):
  #  if ref[0] > -1:
  #    yield dict(event="latest", branch=branch, ref=ref)

  # [(last_built, relative_id)] -> set Tag
  keep =  set(p[0] for  p in fn.flatten(map(
    lambda x:zip(*x),
    z
  )) if p[1] not in(-1, None))

  return zip(containers, tags_by_container)


# move me
ttag = compose(
  docker.encode_tag,
  fn.getattr('name')
)


def last_built(commit_map, tags):
  last_built_ref, last_built_rel = zip(*map(
    commits.max_commit(commit_map),  
    tags
  ))
  return last_built_ref, last_built_rel
