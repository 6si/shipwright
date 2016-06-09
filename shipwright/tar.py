from __future__ import absolute_import

import io
import os
import re
import tarfile
from os.path import join

from docker import utils


def bundle_docker_dir(tag, docker_path):
    """
    Tars up a directory using the normal docker.util.tar method but
    adds tag if it's not None.
    """

    # tar up the directory minus the Dockerfile,

    path = os.path.dirname(docker_path)
    try:
        with open(join(path, '.dockerignore')) as f:
            stripped = (p.strip() for p in f.readlines())
            ignore = [x for x in stripped if x]
    except IOError:
        ignore = []

    dockerfile_name = os.path.basename(docker_path)

    if tag is None:
        return utils.tar(path, ignore, dockerfile=dockerfile_name)

    # docker-py 1.6+ won't ignore the dockerfile
    # passing dockerfile='' works around the issuen
    # and lets us add the modified file when we're done.
    ignore.append(dockerfile_name)
    fileobj = utils.tar(path, ignore, dockerfile='')

    t = tarfile.open(fileobj=fileobj, mode='a')
    dfinfo = tarfile.TarInfo(dockerfile_name)

    contents = tag_parent(tag, open(join(path, dockerfile_name)).read())
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
    with a tag that ensures that the image depends on a parent built
    within the same build_ref (bulid group) as the container being built.
    """

    return bundle_docker_dir(
        tag,
        docker_path,
    )
