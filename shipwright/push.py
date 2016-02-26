from . import compat
from .fn import (
    compose, curry, fmap, flat_map, merge
)


@curry
def do_push(client, images):
    return flat_map(push(client), images)


@curry
def push(client, image_tag):
    image, tag = image_tag
    return fmap(
        compose(
            merge(dict(event="push", image=image)),
            compat.json_loads,
        ),
        client.push(
            image,
            tag,
            stream=True
        )
    )
