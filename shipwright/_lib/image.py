from __future__ import absolute_import

import os
from collections import namedtuple

Image = namedtuple(
    'Image',
    ['name', 'dir_path', 'path', 'parent', 'short_name'],
)


def list_images(namespace, name_map, root_path):
    images = []
    for path in build_files(root_path):
        name, short_name = image_name(namespace, name_map, root_path, path)
        images.append(Image(
            name=name,
            short_name=short_name,
            dir_path=os.path.dirname(path),
            path=path,
            parent=parent(path),
        ))
    return images


def image_name(namespace, name_map, root_path, path):
    """
    Determines the name of the image from the config file
    or based on it's parent directory name.

    >>> image_name(
    ...     'shipwright', {'blah':'foo/blah'}, 'x/', 'x/blah/Dockerfile',
    ... )
    ('foo/blah', 'foo/blah')

    >>> image_name(
    ...     'shipwright', {'blah':'foo/blah'}, 'x/', 'x/baz/Dockerfile'
    ... )
    ('shipwright/baz', 'baz')

    """

    if path.startswith(root_path):
        relative_path = os.path.dirname(path[len(root_path):])
        docker_repo = name_map.get(relative_path)

        if docker_repo is not None:
            return docker_repo, docker_repo
    short_name = name(path)
    # try to guess the name from the path
    return namespace + '/' + short_name, short_name


# path -> iter([path ... / Dockerfile, ... ])
def build_files(build_root):
    """
    Given a directory returns an iterator where each item is
    a path to a dockerfile

    Setup creates 3  dockerfiles under test root along with other
    files

    >>> test_root = getfixture('tmpdir').mkdir('images')
    >>> test_root.mkdir('image1').join('Dockerfile').write('FROM ubuntu')
    >>> test_root.mkdir('image2').join('Dockerfile').write('FROM ubuntu')
    >>> image3 = test_root.mkdir('image3')
    >>> image3.join('Dockerfile').write('FROM ubuntu')
    >>> image3.join('Dockerfile-dev').write('FROM ubuntu')
    >>> other = test_root.mkdir('other')
    >>> _ = other.mkdir('subdir1')
    >>> other.mkdir('subdir2').join('empty.txt').write('')

    >>> files = build_files(str(test_root))
    >>> sorted(files)  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    ['.../image1/Dockerfile', '.../image2/Dockerfile',
    '.../image3/Dockerfile', '.../image3/Dockerfile-dev']

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
