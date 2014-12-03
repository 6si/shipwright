
"""
Shipwright -- Builds shared Docker images within a common git repository.

Usage:
  shipwright [build|push|publish-no-build|purge] [TARGET...]

Options:

 --help           Show all help information

 -H DOCKER_HOST   Override DOCKER_HOST if it's set in the environment.


Target Specifiers:
  shipwright <target>   -- build a target and everything it depends on
  shipwright ^<target>  -- build a target it's dependencies and 
                           everything that depends on it
  shipwright =<target>  -- build without dependencies
  shipwright +<target>  -- force build a target
  shipwright -<target>  -- exclude a target


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
import json
from itertools import cycle

from docopt import docopt
import docker
import git

from shipwright.version import version
from shipwright import Shipwright


from shipwright.colors import rainbow
from shipwright.fn import _0



# todo: only do this if python 2.7
import ssl



def main():
  arguments = docopt(__doc__, options_first=True, version='Shipwright ' + version)
  repo = git.Repo(os.getcwd())

  try:
    config = json.load(open(
      os.path.join(repo.working_dir, '.shipwright.json')
    ))
  except OSError:
    config = {
      'namespace': arguments['DOCKER_HUB_ACCOUNT'] or os.environ.get('SW_NAMESPACE')
    }



  if config['namespace'] is None:
    exit(
      "Please specify your docker hub account in\n"
      "the .shipwright.json config file,\n "
      "the command line or set SW_NAMESPACE.\n"
      "Run shipwright --help for more information."
    )

  
  base_url = os.environ.get('DOCKER_HOST','unix:///var/run/docker.sock')
  
  DOCKER_TLS_VERIFY = bool(os.environ.get('DOCKER_TLS_VERIFY', False))
 
  if not DOCKER_TLS_VERIFY:
    tls_config = False
  else:
    cert_path = os.environ.get('DOCKER_CERT_PATH')
    if cert_path:
      ca_cert_path = os.path.join(cert_path,'ca.pem')
      client_cert=(
        os.path.join(cert_path, 'cert.pem'), 
        os.path.join(cert_path, 'key.pem')
      )

    tls_config = docker.tls.TLSConfig(
      ssl_version = ssl.PROTOCOL_TLSv1,
      client_cert = client_cert,
      verify=ca_cert_path,
      assert_hostname=False
    )
    if base_url.startswith('tcp://'):
      base_url = 'https://' + base_url[6:]

  client = docker.Client(
    base_url=base_url,
    version='1.12',
    timeout=10,
    tls=tls_config
  )

  # {'publish': false, 'purge': true, ...} = 'purge'
  command_name = _0([
    command for (command, enabled) in arguments.items()
    if command.islower() and enabled
  ]) or "build"

  command = getattr(Shipwright(config,repo,client), command_name)

  for event in command():
    show_fn = mk_show(event)
    show_fn(switch(event))

def exit(msg):
  print(msg)
  sys.exit(1)
 
def memo(f, arg, memos={}):
  if arg in memos:
    return memos[arg]
  else:
    memos[arg] = f(arg)
    return memos[arg]

def mk_show(evt):
  if evt['event'] == 'build_msg' or 'error' in evt:
    return memo(highlight,evt['container'])
  else:
    return print

colors = cycle(rainbow())
def highlight(container):
  color_fn = next(colors)
  def highlight_(msg):
    print(color_fn( container.name) + " | " + msg)
  return highlight_

def switch(rec):

  if 'stream' in rec:
    return rec['stream'].strip('\n')

  elif 'status' in rec:
    if rec['status'].startswith('Downloading'):
      term = '\r'
    else:
      term = '\n'

    return '[STATUS] {0}: {1}{2}'.format(
      rec.get('id', ''), 
      rec['status'],
      term
    )
  elif 'error' in rec:
    return '[ERROR] {0}\n'.format(rec['errorDetail']['message'])
  elif rec['event'] == 'tag':
    return 'Tagging {image} to {name}:{tag}'.format(name=rec['container'].name, **rec)
  elif rec['event'] == 'removed':
    return 'Untagging {image}:{tag}'.format(**rec)
  else:
    return rec
