
"""
Shipwright -- Builds shared Docker images within a common git repository.

Usage:
  shipwright [options] [DOCKER_HUB_ACCOUNT] [--publish] 

Options:

 --help           Show all help information 

 -H DOCKER_HOST   Override DOCKER_HOST if it's set in the environment.


Environment Variables:

  SW_NAMESPACE : If DOCKER_HUB_ACCOUNT is not passed on the command line
   this Environment variable must be present.

  DOCKER_HOST : Same URL as used by the docker client to connect to 
    the docker daemon. 
"""
from __future__ import absolute_import
from __future__ import print_function


import sys
import os
from itertools import cycle

from docopt import docopt
import docker
import git

from shipwright.version import version
from shipwright import Shipwright
from shipwright.fn import maybe, first, _1, show


from shipwright.colors import rainbow

def main():
  arguments = docopt(__doc__, version='Shipwright ' + version)
  namespace = arguments['DOCKER_HUB_ACCOUNT'] or os.environ.get('SW_NAMESPACE')
  if namespace is None:
    exit(
      "Please specify your docker hub account on  "
      "the command line or set SW_NAMESPACE.\n"
      "Run shipwright --help for more information."
    )

  if arguments["--publish"]:
    exit('Oh gosh, Sorry!\n "--publish" is not yet implemented')
  base_url = os.environ.get('DOCKER_HOST','unix://var/run/docker.sock')

  repo = git.Repo(os.getcwd())
  client = docker.Client(
    base_url=base_url,
    version='1.9',
    timeout=10
  )

  for t, docker_commit in Shipwright(namespace,repo,client).build(highlight):
    print("Built {}".format( t.name))

def exit(msg):
  print(msg)
  sys.exit(1)
 

colors = cycle(rainbow())
def highlight(container):
  color_fn = next(colors)
  def highlight_(msg):
    print(color_fn( container.name) + " | " + msg)
  return highlight_


