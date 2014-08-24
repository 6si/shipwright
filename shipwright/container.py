from __future__ import absolute_import

import os
from collections import namedtuple

Container = namedtuple('Container', 'name,dir_path,path,parent')


# namespace -> path -> [Container]
def containers(namespace, path):
  """
  Given a namespace and a path return a list of Containers. Each
  container's name will be based on the namespace and directory
  where the Dockerfile was located.

  >>> from shipwright.container import TEST_ROOT
  >>> containers('shipwright_test', TEST_ROOT) # doctest: +ELLIPSIS
  [Container(...), Container(...), Container(...)]
  """
  return [
    container_from_path(namespace, container_path)
    for  container_path in build_files(path)
  ]


#namespace -> path -> Container(name, path, parent)
def container_from_path(namespace, path):
  """
  Given a path to a Dockerfile parse the file and return 
  a coresponding Container


  >>> from .container import TEST_ROOT

  >>> path = os.path.join(TEST_ROOT, 'container1/Dockerfile')
  >>> container_from_path('shipwright_test', path) # doctest: +ELLIPSIS
  Container(name='shipwright_test/container1', path='.../container1/Dockerfile', parent='ubuntu')
  """

  return Container(
    name = '/'.join([namespace,name(path)]),
    dir_path = os.path.dirname(path),
    path = path,
    parent = parent(path)
  )

# path -> iter([path ... / Dockerfile, ... ])
def build_files(build_root):
  """
  Given a directory returns an iterator where each item is
  a path to a dockerfile

  Setup creates 3  dockerfiles under test root along with other
  files

  >>> from .container import TEST_ROOT

  >>> sorted(build_files(TEST_ROOT)) # doctest: +ELLIPSIS
  ['.../container1/Dockerfile', '.../container2/Dockerfile', '.../container3/Dockerfile']

  """
  for root, dirs, files in os.walk(build_root):
    if "Dockerfile" in files:
      yield os.path.join(root, "Dockerfile") 


# path -> str
def name(docker_path):
  """
  Return the immediate directory of a path pointing to a dockerfile.
  Raises ValueError if the path does not end in Dockerfile

  >>> name('/blah/foo/Dockerfile')
  'foo'
  """
  if not docker_path.endswith('Dockerfile'):
    raise ValueError(
      "'{}' is not a valid Dockerfile".format(docker_path)
    )

  return os.path.basename(os.path.dirname(docker_path))

def parent(docker_path):
  """
  >>> from .container import TEST_ROOT
  >>> docker_path = os.path.join(TEST_ROOT, "Dockerfile")
  >>> open(docker_path, "w").write('FrOm    ubuntu')

  >>> parent(docker_path)
  'ubuntu'

  """
  for l in open(docker_path):
    if l.strip().lower().startswith('from'):
      return l.split()[1]




## Test Helpers ########################

def setup(module):
  import tempfile
  TEST_ROOT=module.TEST_ROOT=tempfile.mkdtemp()

  contents = {
    'container1/Dockerfile': 'FROM ubuntu\nMAINTAINER bob',
    'container2/Dockerfile': 'FROM shipwright_test/container1\nMAINTAINER bob',
    'container3/Dockerfile': 'FROM shipwright_test/container2\nMAINTAINER bob',
    'other/subdir1':None,
    'other/subdir2/empty.txt': ''
  }
  
  for path,content in contents.items():
      file_path = os.path.join(TEST_ROOT, path)
      if content is None:
        dir = file_path
      else:
        dir = os.path.dirname(file_path)
      os.makedirs(dir)
      if content is not None:
        with(open(file_path,'w')) as f:
          f.write(content)
    

def teardown(module):
  import shutil
  shutil.rmtree(module.TEST_ROOT)
  del module.TEST_ROOT