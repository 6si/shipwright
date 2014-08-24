from __future__ import absolute_import

from collections import namedtuple

from . import build
from . import fn
from . import commits
from . import docker
from . import dependencies

from .container import containers as list_containers
from .fn import curry, compose


class Shipwright(object):
  def __init__(self, namespace, source_control, docker_client):
    self.source_control = source_control
    self.docker_client = docker_client
    self.namespace = namespace

  def targets(self):
    client = self.docker_client

    containers = list_containers(
      self.namespace,
      self.source_control.working_dir
    )
 
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
    


  def build(self, callback):

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
      callback,  
      #build(client, this_ref_str), # build function
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


    return built


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



