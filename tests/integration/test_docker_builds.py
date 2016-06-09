from __future__ import absolute_import

import shutil

import docker
import git
import pkg_resources
import pytest
from docker import utils as docker_utils

from shipwright import cli as shipw_cli


def get_defaults():
    return {
        '--account': None,
        '--dependents': [],
        '--dump-file': None,
        '--exact': [],
        '--exclude': [],
        '--help': False,
        '--no-build': False,
        '--upto': [],
        '--x-assert-hostname': False,
        '-H': None,
        'TARGET': [],
        'build': False,
        'push': False,
        'tags': ['latest'],
    }


def create_repo(path, source):
    shutil.copytree(source, path)
    repo = git.Repo.init(path)
    repo.index.add(repo.untracked_files)
    repo.index.commit('Initial Commit')
    return repo


def commit_untracked(repo, message='WIP'):
    repo.index.add(repo.untracked_files)
    repo.index.commit(message)


def test_sample(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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


def test_multi_dockerfile(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/multi-dockerfile',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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


def test_clean_tree_avoids_rebuild(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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


def test_clean_tree_avoids_rebuild_new_image_definition(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

    try:
        shipw_cli.run(
            path=path,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        dockerfile = """
        FROM busybox
        MAINTAINER dockhand
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


def test_dump_file(tmpdir):
    dump_file = tmpdir.join('dump.txt')
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)

    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

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


def test_exclude(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

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


def test_exact(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

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


def test_exit_on_failure_but_build_completes(tmpdir):
    path = str(tmpdir.join('failing-build'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/failing-build',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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


def test_short_name_target(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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


def test_child_inherits_parents_build_tag(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    cli = docker.Client(version='1.18', **client_cfg)

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
