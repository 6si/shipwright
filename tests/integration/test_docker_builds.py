from __future__ import absolute_import

import pkg_resources
import pytest
from docker import utils as docker_utils

from shipwright import cli as shipw_cli

from .utils import commit_untracked, create_repo, default_args, get_defaults


def test_sample(tmpdir, docker_client):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1, shared, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert set(service1['RepoTags']) == {
            'shipwright/service1:master',
            'shipwright/service1:latest',
            'shipwright/service1:' + tag,
        }

        assert set(shared['RepoTags']) == {
            'shipwright/shared:master',
            'shipwright/shared:latest',
            'shipwright/shared:' + tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + tag,
        }
    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_multi_dockerfile(tmpdir, docker_client):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/multi-dockerfile',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1_dev, service1, base = (
            cli.images(name='shipwright/service1-dev') +
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/base')
        )

        assert set(service1_dev['RepoTags']) == {
            'shipwright/service1-dev:master',
            'shipwright/service1-dev:latest',
            'shipwright/service1-dev:' + tag,
        }

        assert set(service1['RepoTags']) == {
            'shipwright/service1:master',
            'shipwright/service1:latest',
            'shipwright/service1:' + tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + tag,
        }
    finally:
        old_images = (
            cli.images(name='shipwright/service1-dev', quiet=True) +
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_clean_tree_avoids_rebuild(tmpdir, docker_client):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        tmp.join('service1/base.txt').write('Hi mum')
        commit_untracked(repo)
        new_tag = repo.head.ref.commit.hexsha[:12]

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1a, service1b, shared, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        service1a, service1b = sorted(
            (service1a, service1b),
            key=lambda x: len(x['RepoTags']),
            reverse=True,
        )

        assert set(service1a['RepoTags']) == {
            'shipwright/service1:master',
            'shipwright/service1:latest',
            'shipwright/service1:' + new_tag,
        }

        assert set(service1b['RepoTags']) == {
            'shipwright/service1:' + old_tag,
        }

        assert set(shared['RepoTags']) == {
            'shipwright/shared:master',
            'shipwright/shared:latest',
            'shipwright/shared:' + old_tag,
            'shipwright/shared:' + new_tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + old_tag,
            'shipwright/base:' + new_tag,
        }

    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_clean_tree_avoids_rebuild_new_image_definition(tmpdir, docker_client):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        dockerfile = """
        FROM busybox
        MAINTAINER shipwright
        """

        tmp.mkdir('service2').join('Dockerfile').write(dockerfile)
        commit_untracked(repo)
        new_tag = repo.head.ref.commit.hexsha[:12]

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service2, service1, shared, base = (
            cli.images(name='shipwright/service2') +
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert set(service2['RepoTags']) == {
            'shipwright/service2:master',
            'shipwright/service2:latest',
            'shipwright/service2:' + new_tag,
        }

        assert set(service1['RepoTags']) == {
            'shipwright/service1:master',
            'shipwright/service1:latest',
            'shipwright/service1:' + old_tag,
            'shipwright/service1:' + new_tag,
        }

        assert set(shared['RepoTags']) == {
            'shipwright/shared:master',
            'shipwright/shared:latest',
            'shipwright/shared:' + old_tag,
            'shipwright/shared:' + new_tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + old_tag,
            'shipwright/base:' + new_tag,
        }

    finally:
        old_images = (
            cli.images(name='shipwright/service2', quiet=True) +
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_dump_file(tmpdir, docker_client):
    dump_file = tmpdir.join('dump.txt')
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)

    client_cfg = docker_utils.kwargs_from_env()

    cli = docker_client

    try:
        args = get_defaults()
        args['--dump-file'] = str(dump_file)
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=args,
            environ={},
        )

        assert ' : FROM busybox' in dump_file.read()
    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_exclude(tmpdir, docker_client):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker_client

    args = get_defaults()
    args['--exclude'] = [
        'shipwright/service1',
        'shipwright/shared',
    ]

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=args,
            environ={},
        )

        base,  = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
    finally:
        old_images = (
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_exact(tmpdir, docker_client):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker_client

    args = get_defaults()
    args['--exact'] = [
        'shipwright/base',
    ]

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=args,
            environ={},
        )

        base,  = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )
        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
    finally:
        old_images = (
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_dirty_fails_without_flag(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    tmp.join('service1/base.txt').write('Some text')
    client_cfg = docker_utils.kwargs_from_env()

    args = get_defaults()

    result = shipw_cli.run(
        path=path,
        client_cfg=client_cfg,
        arguments=args,
        environ={},
    )
    assert '--dirty' in result
    assert 'Abort' in result


def test_dirty_flag(tmpdir, docker_client):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    tmp.join('service1/base.txt').write('Some text')
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker_client

    args = default_args()
    args.dirty = True

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
            new_style_args=args,
        )

        service1, shared, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert 'shipwright/service1:latest' in service1['RepoTags']
        assert 'shipwright/service1:master' in service1['RepoTags']
        assert 'shipwright/shared:latest' in shared['RepoTags']
        assert 'shipwright/shared:master' in shared['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
        assert 'shipwright/base:master' in base['RepoTags']

    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_exit_on_failure_but_build_completes(tmpdir, docker_client):
    path = str(tmpdir.join('failing-build'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/failing-build',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:
        with pytest.raises(SystemExit):
            shipw_cli.run(
                path=path,
                client_cfg=client_cfg,
                arguments=get_defaults(),
                environ={},
            )

        base, works = (
            cli.images(name='shipwright/base') +
            cli.images(name='shipwright/works') +
            cli.images(name='shipwright/crashy-from') +
            cli.images(name='shipwright/crashy-dev')
        )

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + tag,
        }

        assert set(works['RepoTags']) == {
            'shipwright/works:master',
            'shipwright/works:latest',
            'shipwright/works:' + tag,
        }

    finally:
        old_images = (
            cli.images(name='shipwright/works', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_short_name_target(tmpdir, docker_client):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:
        defaults = get_defaults()
        defaults['--upto'] = ['shared']
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
        )

        shared, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert set(shared['RepoTags']) == {
            'shipwright/shared:master',
            'shipwright/shared:latest',
            'shipwright/shared:' + tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + tag,
        }
    finally:
        old_images = (
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_child_inherits_parents_build_tag(tmpdir, docker_client):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker_client

    try:

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        tmp.join('shared/base.txt').write('Hi mum')
        commit_untracked(repo)
        new_tag = repo.head.ref.commit.hexsha[:12]

        # Currently service1 has not had any changes, and so naivly would not
        # need to be built, however because it's parent, shared has changes
        # it will need to be rebuilt with the parent's build tag.

        # Dockhand asks the question: What is the latest commit in this
        # directory, and all of this image's parents?

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1a, service1b, sharedA, sharedB, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        service1a, service1b = sorted(
            (service1a, service1b),
            key=lambda x: len(x['RepoTags']),
            reverse=True,
        )

        sharedA, sharedB = sorted(
            (sharedA, sharedB),
            key=lambda x: len(x['RepoTags']),
            reverse=True,
        )

        assert set(service1a['RepoTags']) == {
            'shipwright/service1:master',
            'shipwright/service1:latest',
            'shipwright/service1:' + new_tag,
        }

        assert set(service1b['RepoTags']) == {
            'shipwright/service1:' + old_tag,
        }

        assert set(sharedA['RepoTags']) == {
            'shipwright/shared:master',
            'shipwright/shared:latest',
            'shipwright/shared:' + new_tag,
        }

        assert set(sharedB['RepoTags']) == {
            'shipwright/shared:' + old_tag,
        }

        assert set(base['RepoTags']) == {
            'shipwright/base:master',
            'shipwright/base:latest',
            'shipwright/base:' + old_tag,
            'shipwright/base:' + new_tag,
        }

    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_build_with_repo_digest(tmpdir, docker_client, registry):
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

        # Remove a build image:
        old_images = cli.images(name='localhost:5000/service1')
        for image in old_images:
            cli.remove_image(image['Id'], force=True)

        repo_digest = old_images[0]['RepoDigests'][0]
        # Pull it so it's missing a build tag, but has a RepoDigest
        cli.pull(repo_digest)

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
        )

        service1a, service1b, shared, base = (
            cli.images(name='localhost:5000/service1') +
            cli.images(name='localhost:5000/shared') +
            cli.images(name='localhost:5000/base')
        )

        if service1b['RepoTags'] is None:
            service1b, service1a = service1a, service1b

        assert service1a['RepoTags'] is None

        assert set(service1b['RepoTags']) == {
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


def test_docker_build_pull_cache(tmpdir, docker_client, registry):
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

        args = default_args()
        args.pull_cache = True

        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=defaults,
            environ={},
            new_style_args=args,
        )

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
