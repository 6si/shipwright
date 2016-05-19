from __future__ import absolute_import

import functools
import io
import os
import re
import tarfile
from os.path import join

from docker import utils


def bundle_docker_dir(modify_docker_func, docker_path):
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

    >>> test_root = getfixture('tmpdir').mkdir('tar')
    >>> docker_path = test_root.join('Dockerfile')
    >>> docker_path.write(u'blah')

    >>> test_root.join('bogus1').write('hi mom')
    >>> test_root.join('bogus2').write('hello world')


    Now we can call bundle_docker_dir passing it our append_bogus function to
    mutate the docker contents. We'll receive a file like object which
    is stream of the contents encoded as a  tar file (the format Docker
    build expects)

    >>> fileobj = bundle_docker_dir(append_bogus, str(docker_path))

    Normally we'd just pass this directly to the docker build command
    but for the purpose of this test, we'll use tarfile to decode the string
    and ensure that our mutation happened as planned.


    First lets ensure that our tarfile contains our test files

    >>> t = tarfile.open(fileobj=fileobj)
    >>> t.getnames()  # doctest: +SKIP
    ['bogus1', 'bogus2', 'Dockerfile']

    And if we exctart the Dockerfile it starts with 'bogus header'

    >>> ti = t.extractfile('Dockerfile')
    >>> ti.read().startswith(b'bogus header')
    True

    Obviously a real mutation would ensure that the the contents
    of the Dockerfile are valid docker commands and not some
    bogus content.
    """

    # tar up the directory minus the Dockerfile,
    # TODO: respect .dockerignore

    path = os.path.dirname(docker_path)
    try:
        ignore = filter(None, [
            p.strip() for p in open(join(path, '.dockerignore')).readlines()
        ])
    except IOError:
        ignore = []

    dockerfile_name = os.path.basename(docker_path)

    # docker-py 1.6+ won't ignore the dockerfile
    # passing dockerfile='' works around the issuen
    # and lets us add the modified file when we're done.
    ignore.append(dockerfile_name)
    fileobj = utils.tar(path, ignore, dockerfile='')

    # append a dockerfile after running it through a mutation
    # function first
    t = tarfile.open(fileobj=fileobj, mode='a')
    dfinfo = tarfile.TarInfo(dockerfile_name)

    contents = modify_docker_func(open(join(path, dockerfile_name)).read())
    if not isinstance(contents, bytes):
        contents = contents.encode('utf8')
    dockerfile = io.BytesIO(contents)

    dfinfo.size = len(dockerfile.getvalue())
    t.addfile(dfinfo, dockerfile)
    t.close()
    fileobj.seek(0)
    return fileobj


def tag_parent(tag, docker_content):
    r"""
    Replace the From clause  like

    FROM somerepo/image

    To

    somerepo/image:tag


    >>> print(tag_parent(
    ...     "blah",
    ...     "# comment\n"
    ...     "author bob barker\n"
    ...     "FroM somerepo/image\n\n"
    ...     "RUN echo hi mom\n"
    ... ))
    # comment
    author bob barker
    FroM somerepo/image:blah
    <BLANKLINE>
    RUN echo hi mom
    <BLANKLINE>


    >>> print(tag_parent(
    ...     "blah",
    ...     "# comment\n"
    ...     "author bob barker\n"
    ...     "FroM localhost:5000/somerepo/image\n\n"
    ...     "RUN echo hi mom\n"
    ... ))
    # comment
    author bob barker
    FroM localhost:5000/somerepo/image:blah
    <BLANKLINE>
    RUN echo hi mom
    <BLANKLINE>

    >>> print(tag_parent(
    ...     "blah",
    ...     "# comment\n"
    ...     "author bob barker\n"
    ...     "FroM docker.example.com:5000/somerepo/image\n\n"
    ...     "RUN echo hi mom\n",
    ... ))
    # comment
    author bob barker
    FroM docker.example.com:5000/somerepo/image:blah
    <BLANKLINE>
    RUN echo hi mom
    <BLANKLINE>
    """

    v = re.sub(
        '^(\s*from\s+)(([\w.-]+(\:\d+)?\/)?[\w.-]+/[\w.-]+)(\s*)$',
        '\\1\\2:' + tag + '\\5',
        docker_content,
        flags=re.MULTILINE + re.I,
    )

    return v


# str -> str -> fileobj
def mkcontext(tag, docker_path):
    """
    Returns a streaming tarfile suitable for passing to docker build.

    This method expects that there will be a Dockerfile in the same
    directory as path. The contents of which will be substituted
    with a tag that ensure that the image depends on a parent built
    within the same git revision (bulid group) as the container being built.
    """

    return bundle_docker_dir(
        functools.partial(tag_parent, tag),
        docker_path,
    )
