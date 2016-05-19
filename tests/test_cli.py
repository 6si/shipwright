from __future__ import absolute_import

import git
from docker import tls

import pytest
from shipwright import cli


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
    }


def create_repo(path):
    repo = git.Repo.init(path)
    repo.index.add(repo.untracked_files)
    repo.index.commit('Initial Commit')
    return repo


def test_without_json_manifest(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    repo = create_repo(path)
    with pytest.raises(SystemExit):
        cli.process_arguments(
            repo, get_defaults(), client_cfg={}, environ={},
        )


def test_push_also_builds(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    repo = create_repo(path)
    in_args = get_defaults()
    in_args['push'] = True
    args, _, _, _, _ = cli.process_arguments(
        repo, in_args, client_cfg={},
        environ={'SW_NAMESPACE': 'eg'},
    )
    specifiers, build = args
    assert build


def test_assert_hostname(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    repo = create_repo(path)
    args = get_defaults()
    args['--x-assert-hostname'] = True
    tls_config = tls.TLSConfig()
    _, _, _, _, client = cli.process_arguments(
        repo, args,
        client_cfg={
            'base_url': 'https://example.com:443/api/v1/',
            'tls': tls_config,
        },
        environ={'SW_NAMESPACE': 'eg'},
    )

    assert not client.adapters['https://'].assert_hostname
