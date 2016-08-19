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
    built_tags = set()
    for image in images:
        if image['RepoTags'] is None:
            continue
        for key in key_from_image_info(image):
            built_tags.add(key)
    return built_tags


def encode_tag(tag):
    return tag.replace('/', '-')


def tag_image(client, image, new_ref):
    tag = encode_tag(new_ref)
    old_image = image.name + ':' + image.ref
    repository = image.name
    evt = {
        'event': 'tag',
        'old_image': old_image,
        'repository': repository,
        'tag': tag,
    }
    try:
        client.tag(
            old_image,
            repository,
            tag=tag,
            force=True,
        )
    except d_errors.NotFound:
        message = 'Error tagging {}, not found'.format(old_image)
        evt.update({
            'error': message,
            'errorDetail': {'message': message},
        })

    return evt
