from __future__ import absolute_import

from collections import namedtuple

from . import build
from . import fn
from . import commits
from . import docker
from . import dependencies

from . import query

from .container import containers as list_containers, container_name, Container
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
    


  def build(self):

    branch = self.source_control.active_branch.name
    this_ref_str = commits.hexsha(self.source_control.commit())
    
    current, targets = dependencies.needs_building(self.targets())

    if current:
      # these containers weren't effected by the latest git changes
      # so we'll fast forward tag them with the build id. That way  any
      # of the containers that do need to be built can refer
      # to the skiped ones by user/image:<last_built_ref> which makes
      # them part of the same group.
      for evt in docker.tag_containers(
        self.docker_client, 
        current,
        this_ref_str
      ): yield evt

    for evt in  build.do_build( 
          self.docker_client,
          this_ref_str,
          targets # what needs building
    ): yield evt

    # now that we're built and tagged all the images with git commit,
    # (either during the process of building or forwarding the tag)
    # tag all containers with the branch name
    for evt in docker.tag_containers(
      self.docker_client, 
      current + [t._replace(last_built_ref=this_ref_str) for t in targets], 
      branch
    ): yield evt

    for evt in docker.tag_containers(
      self.docker_client, 
      current + [t._replace(last_built_ref=this_ref_str) for t in targets], 
      "latest"
    ): yield evt



  def purge(self):
    """
    Experimental feature use with caution. For each branch removes all 
    previous built images expept for the last built.
    """

    containers = self.containers()
 
    d = query.dataset(self.source_control, self.docker_client, containers)
    for row in d.query('''
      select image, tag 
      from image left join latest_commit on latest_commit.commit = image.tag 
      where latest_commit.commit is null
    '''):
      image, tag = row
      try:
        self.docker_client.remove_image("{}:{}".format(image,tag), force=True, noprune=False)
        yield dict(event="removed", image=image, tag=tag)
      except Exception, e:
        yield dict(
          event="error", 
          error=e,
          container=Container(image,None,None,None), 
          errorDetail=dict(message=str(e))
        )




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



