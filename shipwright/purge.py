from .container import Container


def do_purge(client, images):
    for row in images:
        image, tag = row
        try:
            client.remove_image(
                "{}:{}".format(image, tag), force=True, noprune=False,
            )
            yield dict(event="removed", image=image, tag=tag)
        except Exception as e:
            yield dict(
                event="error",
                error=e,
                container=Container(image, None, None, None),
                errorDetail=dict(message=str(e))
            )
