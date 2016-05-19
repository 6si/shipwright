from __future__ import absolute_import

import shutil

import docker
import git
import pkg_resources
from docker import utils as docker_utils

from shipwright import cli as shipw_cli


def get_defaults():
    return {
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
        'purge': False,
        'push': False,
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
            repo=repo,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1, shared, base = (
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/shared') +
            cli.images(name='shipwright/base')
        )

        assert 'shipwright/service1:master' in service1['RepoTags']
        assert 'shipwright/service1:latest' in service1['RepoTags']
        assert 'shipwright/service1:' + tag in service1['RepoTags']
        assert 'shipwright/shared:master' in shared['RepoTags']
        assert 'shipwright/shared:latest' in shared['RepoTags']
        assert 'shipwright/shared:' + tag in shared['RepoTags']
        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
        assert 'shipwright/base:' + tag in base['RepoTags']
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
            repo=repo,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        service1_dev, service1, base = (
            cli.images(name='shipwright/service1-dev') +
            cli.images(name='shipwright/service1') +
            cli.images(name='shipwright/base')
        )

        assert 'shipwright/service1-dev:master' in service1_dev['RepoTags']
        assert 'shipwright/service1-dev:latest' in service1_dev['RepoTags']
        assert 'shipwright/service1-dev:' + tag in service1_dev['RepoTags']
        assert 'shipwright/service1:master' in service1['RepoTags']
        assert 'shipwright/service1:latest' in service1['RepoTags']
        assert 'shipwright/service1:' + tag in service1['RepoTags']
        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
        assert 'shipwright/base:' + tag in base['RepoTags']
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
            repo=repo,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        tmp.join('service1/base.txt').write('Hi mum')
        commit_untracked(repo)
        new_tag = repo.head.ref.commit.hexsha[:12]

        shipw_cli.run(
            repo=repo,
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

        assert 'shipwright/service1:master' in service1a['RepoTags']
        assert 'shipwright/service1:latest' in service1a['RepoTags']
        assert 'shipwright/service1:' + new_tag in service1a['RepoTags']

        assert 'shipwright/service1:' + old_tag in service1b['RepoTags']

        assert 'shipwright/shared:master' in shared['RepoTags']
        assert 'shipwright/shared:latest' in shared['RepoTags']
        assert 'shipwright/shared:' + old_tag in shared['RepoTags']
        assert 'shipwright/shared:' + new_tag in shared['RepoTags']

        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
        assert 'shipwright/base:' + old_tag in base['RepoTags']
        assert 'shipwright/base:' + new_tag in base['RepoTags']

    finally:
        old_images = (
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/shared', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)


def test_purge_removes_stale_images(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
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
            repo=repo,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        tmp.join('service1/base.txt').write('Hi mum')
        commit_untracked(repo)

        shipw_cli.run(
            repo=repo,
            client_cfg=client_cfg,
            arguments=get_defaults(),
            environ={},
        )

        assert len(cli.images(name='shipwright/service1')) == 2
        assert len(cli.images(name='shipwright/shared')) == 1
        assert len(cli.images(name='shipwright/base')) == 1

        args = get_defaults()
        args['purge'] = True

        shipw_cli.run(
            repo=repo,
            client_cfg=client_cfg,
            arguments=args,
            environ={},
        )

        assert len(cli.images(name='shipwright/service1')) == 1
        assert len(cli.images(name='shipwright/shared')) == 1
        assert len(cli.images(name='shipwright/base')) == 1

    finally:
        old_images = (
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
    repo = create_repo(path, source)

    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

    try:
        args = get_defaults()
        args['--dump-file'] = str(dump_file)
        shipw_cli.run(
            repo=repo,
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
    repo = create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

    args = get_defaults()
    args['--exclude'] = [
        'shipwright/service1',
        'shipwright/shared',
    ]

    try:
        shipw_cli.run(
            repo=repo,
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
    repo = create_repo(path, source)
    client_cfg = docker_utils.kwargs_from_env()

    cli = docker.Client(version='1.18', **client_cfg)

    args = get_defaults()
    args['--exact'] = [
        'shipwright/base',
    ]

    try:
        shipw_cli.run(
            repo=repo,
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
