import shutil

import pkg_resources
import git
from docker import utils as docker_utils
import docker

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


def test_sample(tmpdir):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
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
        assert 'shipwright/shared:master' in shared['RepoTags']
        assert 'shipwright/shared:latest' in shared['RepoTags']
        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
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
        assert 'shipwright/service1:master' in service1['RepoTags']
        assert 'shipwright/service1:latest' in service1['RepoTags']
        assert 'shipwright/base:master' in base['RepoTags']
        assert 'shipwright/base:latest' in base['RepoTags']
    finally:
        old_images = (
            cli.images(name='shipwright/service1-dev', quiet=True) +
            cli.images(name='shipwright/service1', quiet=True) +
            cli.images(name='shipwright/base', quiet=True)
        )
        for image in old_images:
            cli.remove_image(image, force=True)
