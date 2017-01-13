from __future__ import absolute_import

import pkg_resources
from docker import utils as docker_utils

from shipwright import cli as shipw_cli

from .utils import commit_untracked, create_repo, default_args, get_defaults


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


def test_docker_push_target_ref(tmpdir, docker_client, registry):
    """
    Test that shipwright push includes the target ref of every image.
    Otherwise --pull-cache will not work.
    """
    tmp = tmpdir.join('shipwright-localhost-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-localhost-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    tmp.join('service1/base.txt').write('Hi mum')
    commit_untracked(repo)
    new_tag = repo.head.ref.commit.hexsha[:12]

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
        for t in ['master', 'latest', new_tag, tag]:
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
            'localhost:5000/service1:' + new_tag,
        }

        assert set(shared['RepoTags']) == {
            'localhost:5000/shared:master',
            'localhost:5000/shared:latest',
            'localhost:5000/shared:' + new_tag,
            'localhost:5000/shared:' + tag,
        }

        assert set(base['RepoTags']) == {
            'localhost:5000/base:master',
            'localhost:5000/base:latest',
            'localhost:5000/base:' + new_tag,
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


def test_docker_push_direct_registry(tmpdir, docker_client, registry):
    tmp = tmpdir.join('shipwright-localhost-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-localhost-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    args = default_args()
    args.registry_login = [['docker login http://localhost:5000']]

    defaults = get_defaults()
    defaults['push'] = True
    try:

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            new_style_args=args,
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

        tmp.join('spam').write('Hi mum')
        commit_untracked(repo)
        new_tag = repo.head.ref.commit.hexsha[:12]

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
            new_style_args=args,
        )

        images_after_build = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )

        # Nothing up my sleeve (Shipwright didn't download any images)
        assert images_after_build == []

        # Pull them again:
        for t in ['master', 'latest', tag, new_tag]:
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
            # But it still managed to tag a new commit!
            'localhost:5000/service1:' + new_tag,
        }

        assert set(shared['RepoTags']) == {
            'localhost:5000/shared:master',
            'localhost:5000/shared:latest',
            'localhost:5000/shared:' + tag,
            'localhost:5000/shared:' + new_tag,
        }

        assert set(base['RepoTags']) == {
            'localhost:5000/base:master',
            'localhost:5000/base:latest',
            'localhost:5000/base:' + tag,
            'localhost:5000/base:' + new_tag,
        }
    finally:
        old_images = (
            cli.images(name='localhost:5000/service1', quiet=True) +
            cli.images(name='localhost:5000/shared', quiet=True) +
            cli.images(name='localhost:5000/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)
