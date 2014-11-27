from __future__ import absolute_import

from collections import namedtuple

from . import build
from . import purge
from . import fn
from . import commits
from . import docker
from . import dependencies

from .container import containers as list_containers, container_name
from .fn import curry, compose, not_, contains

from . import fn

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
        self.config.get('names',{}),
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
      docker.tags_from_containers(self.docker_client, containers)  # list of tags
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
      Target(container, built_ref, built_rel, current_rel)

      for container, built_ref, built_rel, current_rel in  zip(
        containers, last_built_ref, last_built_rel, current_rel
      )

      if current_rel is not None
    ] 
    


  def build(self, mk_show_fn):

    branch = self.source_control.active_branch.name
    this_ref_str = commits.hexsha(self.source_control.commit())
    
    current, targets = dependencies.needs_building(self.targets())

    if current:
      # these containers weren't effected by the latest git changes
      # so we'll fast forward tag them with the build id. That way  any
      # of the containers that do need to be built can refer
      # to the skiped ones by user/image:<last_built_ref> which makes
      # them part of the same group.
      docker.tag_containers(
        self.docker_client, 
        current,
        this_ref_str
      )


    built = build.do_build( 
      mk_show_fn,  
      self.docker_client,
      this_ref_str,
      targets # what needs building
    )

    # now that we're built and tagged all the images with git commit,
    # (either during the process of building or forwarding the tag)
    # tag all containers with the branch name
    docker.tag_containers(
      self.docker_client, 
      current + [t._replace(last_built_ref=this_ref_str) for t in targets], 
      branch
    )

    docker.tag_containers(
      self.docker_client, 
      current + [t._replace(last_built_ref=this_ref_str) for t in targets], 
      "latest"
    )

    return (
      ("Built", container, ref)
      for container, ref in built
    )


  def purge(self, mk_show_fn):
    """
    Experimental feature use with caution. For each branch removes all 
    previous built images expept for the last built.
    """

    containers = self.containers()

    # [Branch] -> [(string -> Int)]
    maps = map(
      lambda b: commits.mkmap(self.source_control, b), 
      self.source_control.branches
    )

    # branches = Union([Branch, Git Ref, Rel Num],[Branch, Branch, -1])
    # containers = [Container, Git Ref | Branch ]
    # all = Join(branches.ref = containers.ref)
    # maximums = Join(
    #  all.ref = Select(branch,  Git Ref, max(rel num), GroupBy(all, "branch")).ref
    


    tags_by_container = docker.tags_from_containers(self.docker_client, containers)

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

    branches = map(ttag, self.source_control.branches) + ['latest']
    #for branch, ref in zip(branches,a):
    #  yield "Latest", branch, ref

    # [(last_built, relative_id)] -> set Tag
    keep =  set(p[0] for  p in fn.flatten(map(
      lambda x:zip(*x),
      z
    )) if p[1] not in(-1, None))


    for c,t in zip(containers, tags_by_container):
      for tag in t:
        if (tag not in branches) and (tag not in keep):
          image = "{name}:{tag}".format(
            name = c.name,
            tag  = tag
          )
          self.docker_client.remove_image(image, force=True, noprune=False)
          yield "Removed", c, tag




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



class Target(namedtuple('Target', 'container, last_built_ref, last_built_rel, current_rel')):
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



