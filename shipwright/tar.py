from __future__ import absolute_import

import io
import re
import tarfile

from os.path import join

from docker import utils

from shipwright.fn import curry, show, compose


def bundle_docker_dir(modify_docker_func, path):
  """
  Tars up a directory using the normal docker.util.tar method but
  first relpaces the contents of the Dockerfile found at path with
  the result of calling modify_docker_func with a string containing
  the complete contents of the docker file.


  For example to prepend the phrase "bogus header"  to a dockerfile
  we first create a function that takes the contents of the current
  dockerfile as it's contents. 

  >>> def append_bogus(docker_content):
  ...   return "bogus header " + docker_content

  Then we can tar it up.. but first we'll need some test content.
  These routines create a  temporary directory containing the following
  3 files.

  ./Dockerfile
  ./bogus1
  ./bogus2

  >>> import tar 
  >>> path = join(tar.TEST_ROOT, 'Dockerfile')
  >>> open(path, 'w').write('blah')
  
  >>> open(join(tar.TEST_ROOT, 'bogus1'),'w').write('hi mom')
  >>> open(join(tar.TEST_ROOT, 'bogus2'), 'w').write('hello world')


  Now we can call bundle_docker_dir passing it our append_bogus function to
  mutate the docker contents. We'll receive a file like object which
  is stream of the contents encoded as a  tar file (the format Docker 
  build expects)

  >>> fileobj = bundle_docker_dir(append_bogus, tar.TEST_ROOT)

  Normally we'd just pass this directly to the docker build command
  but for the purpose of this test, we'll use trfile to decode the string
  and ensure that our mutation happened as planned.


  First lets ensure that our tarfile contains our test files

  >>> t = tarfile.open(fileobj=fileobj)
  >>> t.getnames()
  ['bogus1', 'bogus2', 'Dockerfile']

  And if we exctart the Dockerfile it starts with 'bogus header'
  >>> ti = t.extractfile('Dockerfile')
  >>> ti.read().startswith('bogus header')
  True
 
  Obviously a real mutation would ensure that the the contents 
  of the Dockerfile are valid docker commands and not some
  bogus content.
  
  """

  # tar up the directory minus the Dockerfile, 
  # TODO: respect .dockerignore
  fileobj = utils.tar(path, ['Dockerfile'])

  # append a dockerfile after running it through a mutation
  # function first
  t = tarfile.open(fileobj=fileobj, mode = 'a')
  dfinfo = tarfile.TarInfo('Dockerfile')


  dockerfile = io.BytesIO(
    modify_docker_func(open(join(path, 'Dockerfile')).read())
  )

  dfinfo.size = len(dockerfile.getvalue())
  t.addfile(dfinfo, dockerfile)
  t.close()
  fileobj.seek(0)
  return fileobj


@curry
def tag_parent(tag, docker_content):
  """
  Replace the From clause  like

  FROM somerepo/image

  To 

  somerepo/image:tag

 
  >>> tag_parent("blah", "# comment\\nauthor bob barker\\nFroM somerepo/image\\n\\nRUN echo hi mom\\n")
  '# comment\\nauthor bob barker\\nFroM somerepo/image:blah\\n\\nRUN echo hi mom\\n'
 
  """

  return re.sub(
    '^(\s*from\s+)(\w+/\w+)(\s*)$', 
    "\\1\\2:" + tag + "\\3", 
    docker_content, 
    flags=re.MULTILINE+re.I
  )
 

# str -> str -> fileobj
def mkcontext(tag, path):
  """
  Returns a streaming tarfile suitable for passing to docker build.

  This method expects that there will be a Dockerfile in the same
  directory as path. The contents of which will be substituted 
  with a tag that ensure that the image depends on a parent built
  within the same git revision (bulid group) as the container being built.
  """


  return bundle_docker_dir(tag_parent(tag), path)



## Test Helpers ########################

def setup(module):
  import tempfile
  module.TEST_ROOT=tempfile.mkdtemp()

def teardown(module):
  import shutil
  #shutil.rmtree(module.TEST_ROOT)
  del module.TEST_ROOT
