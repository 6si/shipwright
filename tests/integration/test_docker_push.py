from __future__ import absolute_import

import docker
import pkg_resources
import pytest
from docker import utils as docker_utils

from shipwright import cli as shipw_cli

from .utils import create_repo, get_defaults


@pytest.fixture(scope='session')
def docker_client():
    client_cfg = docker_utils.kwargs_from_env()
    return docker.Client(version='1.18', **client_cfg)


@pytest.yield_fixture(scope='session')
def registry(docker_client):
    cli = docker_client
    cli.pull('registry', '2')
    cont = cli.create_container(
        'registry:2',
        ports=[5000],
        host_config=cli.create_host_config(
            port_bindings={
                5000: 5000,
            },
        ),
    )
    try:
        cli.start(cont)
        try:
            yield
        finally:
            cli.stop(cont)
    finally:
        cli.remove_container(cont, v=True, force=True)


def test_docker_push(tmpdir, docker_client, registry):
    path = str(tmpdir.join('shipwright-localhost-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-localhost-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    defaults = get_defaults()
    defaults['push'] = True
    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
        )

        # Remove the build images:
        old_images = (
            cli.images(name='localhost:5000/service1', quiet=True) +
            cli.images(name='localhost:5000/shared', quiet=True) +
            cli.images(name='localhost:5000/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)

        images_after_delete = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )
        assert images_after_delete == []

        # Pull them again:
        for t in ['master', 'latest', tag]:
            for repo in ['service1', 'shared', 'base']:
                cli.pull('localhost:5000/' + repo, t)

        service1, shared, base = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )

        assert set(service1['RepoTags']) == {
            'localhost:5000/service1:master',
            'localhost:5000/service1:latest',
            'localhost:5000/service1:' + tag,
        }

        assert set(shared['RepoTags']) == {
            'localhost:5000/shared:master',
            'localhost:5000/shared:latest',
            'localhost:5000/shared:' + tag,
        }

        assert set(base['RepoTags']) == {
            'localhost:5000/base:master',
            'localhost:5000/base:latest',
            'localhost:5000/base:' + tag,
        }
    finally:
        old_images = (
            cli.images(name='localhost:5000/service1', quiet=True) +
            cli.images(name='localhost:5000/shared', quiet=True) +
            cli.images(name='localhost:5000/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_docker_no_build(tmpdir, docker_client, registry):
    path = str(tmpdir.join('shipwright-localhost-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-localhost-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    defaults = get_defaults()
    defaults.update({
        'push': True,
        '--no-build': True,
    })
    try:
        # run a plain build so the images exist for push --no-build
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
        )

        # Remove the build images:
        old_images = (
            cli.images(name='localhost:5000/service1', quiet=True) +
            cli.images(name='localhost:5000/shared', quiet=True) +
            cli.images(name='localhost:5000/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)

        images_after_delete = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )
        assert images_after_delete == []

        # Pull them again:
        for t in ['master', 'latest', tag]:
            for repo in ['service1', 'shared', 'base']:
                cli.pull('localhost:5000/' + repo, t)

        service1, shared, base = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )

        assert set(service1['RepoTags']) == {
            'localhost:5000/service1:master',
            'localhost:5000/service1:latest',
            'localhost:5000/service1:' + tag,
        }

        assert set(shared['RepoTags']) == {
            'localhost:5000/shared:master',
            'localhost:5000/shared:latest',
            'localhost:5000/shared:' + tag,
        }

        assert set(base['RepoTags']) == {
            'localhost:5000/base:master',
            'localhost:5000/base:latest',
            'localhost:5000/base:' + tag,
        }
    finally:
        old_images = (
            cli.images(name='localhost:5000/service1', quiet=True) +
            cli.images(name='localhost:5000/shared', quiet=True) +
            cli.images(name='localhost:5000/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)
