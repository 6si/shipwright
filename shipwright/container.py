from __future__ import absolute_import

import os
from collections import namedtuple

Container = namedtuple('Container', 'name,dir_path,path,parent')


def container_name(namespace, name_map, root_path, path):
    """
    Determines the name of the container from the config file
    or based on it's parent directory name.

    >>> container_name(
    ...     'shipwright', {'blah':'foo/blah'}, 'x/', 'x/blah/Dockerfile',
    ... )
    'foo/blah'

    >>> container_name(
    ...     'shipwright', {'blah':'foo/blah'}, 'x/', 'x/baz/Dockerfile'
    ... )
    'shipwright/baz'

    """

    docker_repo = None
    if path.startswith(root_path):
        relative_path = os.path.dirname(path[len(root_path):])
        docker_repo = name_map.get(relative_path)

    if docker_repo is not None:
        return docker_repo
    else:
        # try to guess the name from the path
        return '/'.join([namespace, name(path)])


# namespace -> path -> [Container]
def containers(name_func, path):
    """
    Given a namespace and a path return a list of Containers. Each
    container's name will be based on the namespace and directory
    where the Dockerfile was located.

    >>> from shipwright import fn
    >>> test_root = getfixture('tmpdir').mkdir('containers')
    >>> test_root.mkdir('container1').join('Dockerfile').write('FROM ubuntu')
    >>> test_root.mkdir('container2').join('Dockerfile').write('FROM ubuntu')
    >>> container3 = test_root.mkdir('container3')
    >>> container3.join('Dockerfile').write('FROM ubuntu')
    >>> container3.join('Dockerfile-dev').write('FROM ubuntu')
    >>> other = test_root.mkdir('other')
    >>> _ = other.mkdir('subdir1')
    >>> other.mkdir('subdir2').join('empty.txt').write('')
    >>> containers(lambda x: x, str(test_root)) # doctest: +ELLIPSIS
    [Container(...), Container(...), Container(...), Container(...)]
    """
    return [
        container_from_path(name_func, container_path)
        for container_path in build_files(path)
    ]


# (path -> name) -> path -> Container(name, path, parent)
def container_from_path(name_func, path):
    """
    Given a name_func() that can determine the repository
    name for an image from a path; and a path to a Dockerfile
    parse the file and return a corresponding Container

    The runtime uses a more sophisticated name_func() for
    testing/demonstration purposes we simply append
    "shipwright_test" to the directory name.

    >>> def name_func(path):
    ...   return 'shipwright_test/' + os.path.basename(os.path.dirname(path))

    >>> test_root = getfixture('tmpdir').mkdir('from_path')
    >>> path = test_root.mkdir('container1').join('Dockerfile')
    >>> path.write('FROM ubuntu')
    >>> container = container_from_path(name_func, str(path))
    >>> container  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    Container(name='shipwright_test/container1',
              dir_path='.../container1',
              path='.../container1/Dockerfile',
              parent='ubuntu')
    """

    return Container(
        name=name_func(path),
        dir_path=os.path.dirname(path),
        path=path,
        parent=parent(path),
    )


# path -> iter([path ... / Dockerfile, ... ])
def build_files(build_root):
    """
    Given a directory returns an iterator where each item is
    a path to a dockerfile

    Setup creates 3  dockerfiles under test root along with other
    files

    >>> test_root = getfixture('tmpdir').mkdir('containers')
    >>> test_root.mkdir('container1').join('Dockerfile').write('FROM ubuntu')
    >>> test_root.mkdir('container2').join('Dockerfile').write('FROM ubuntu')
    >>> container3 = test_root.mkdir('container3')
    >>> container3.join('Dockerfile').write('FROM ubuntu')
    >>> container3.join('Dockerfile-dev').write('FROM ubuntu')
    >>> other = test_root.mkdir('other')
    >>> _ = other.mkdir('subdir1')
    >>> other.mkdir('subdir2').join('empty.txt').write('')

    >>> files = build_files(str(test_root))
    >>> sorted(files)  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    ['.../container1/Dockerfile', '.../container2/Dockerfile',
    '.../container3/Dockerfile', '.../container3/Dockerfile-dev']

    """
    for root, dirs, files in os.walk(build_root):
        for filename in files:
            if filename.startswith('Dockerfile'):
                yield os.path.join(root, filename)


# path -> str
def name(docker_path):
    """
    Return the immediate directory of a path pointing to a dockerfile.
    Raises ValueError if the path does not end in Dockerfile

    >>> name('/blah/foo/Dockerfile')
    'foo'

    >>> name('/blah/foo/Dockerfile-dev')
    'foo-dev'

    >>> name('/blah/foo/not-a-Dockerfile-dev')
    Traceback (most recent call last):
    ...
    ValueError: '/blah/foo/not-a-Dockerfile-dev' is not a valid Dockerfile

    >>> name('/blah/foo/setup.py')
    Traceback (most recent call last):
    ...
    ValueError: '/blah/foo/setup.py' is not a valid Dockerfile
    """

    filename = os.path.basename(docker_path)
    before, dockerfile, after = filename.partition('Dockerfile')
    if dockerfile != 'Dockerfile' or before != '':
        raise ValueError(
            "'{}' is not a valid Dockerfile".format(docker_path),
        )

    return os.path.basename(os.path.dirname(docker_path)) + after


def parent(docker_path):
    """
    >>> path = getfixture('tmpdir').mkdir('parent').join('Dockerfile')
    >>> path.write('FrOm    ubuntu')

    >>> parent(str(path))
    'ubuntu'

    """
    for l in open(docker_path):
        if l.strip().lower().startswith('from'):
            return l.split()[1]
