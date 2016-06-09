from __future__ import absolute_import

from docker import errors as d_errors


def key_from_image_name(image_name):
    """
    >>> key_from_image_name('shipwright/blah:1234')
    '1234'
    """
    return image_name.split(':', 1)[1]


def key_from_image_info(image_info_dict):
    """
    >>> key_from_image_info({
    ...     'RepoTags': [
    ...         'shipwright/base:6e29823388f8', 'shipwright/base:test',
    ...     ]
    ... })
    ['6e29823388f8', 'test']
    """
    return [key_from_image_name(t) for t in image_info_dict['RepoTags']]


def last_built_from_docker(client, name):
    images = client.images(name)
    return list([x for i in images for x in key_from_image_info(i)])


def tags_from_containers(client, containers):
    return [last_built_from_docker(client, c.name) for c in containers]


def encode_tag(tag):
    return tag.replace('/', '-')


def tag_container(client, container, new_ref):
    tag = encode_tag(new_ref)
    image = container.name + ':' + container.last_built_ref
    evt = {
        'event': 'tag',
        'container': container,
        'image': image,
        'tag': tag,
    }
    try:
        client.tag(
            image,
            container.name,
            tag=tag,
            force=True,
        )
    except d_errors.NotFound:
        message = 'Error tagging {}, not found'.format(image)
        evt.update({
            'error': message,
            'errorDetail': {'message': message},
        })

    return evt
