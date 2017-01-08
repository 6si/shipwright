from __future__ import absolute_import

import git
import pytest
from docker import tls

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
        'images': False,
        'tags': ['latest'],
    }


def create_repo(path):
    repo = git.Repo.init(path)
    repo.index.add(repo.untracked_files)
    repo.index.commit('Initial Commit')
    return repo


def test_without_json_manifest(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    create_repo(path)
    with pytest.raises(SystemExit):
        cli.process_arguments(
            path, get_defaults(), client_cfg={}, environ={},
        )


def test_push_also_builds(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    create_repo(path)
    in_args = get_defaults()
    in_args['push'] = True
    _, no_build, _, _, _, _ = cli.process_arguments(
        path, in_args, client_cfg={},
        environ={'SW_NAMESPACE': 'eg'},
    )
    assert not no_build


def test_assert_hostname(tmpdir):
    path = str(tmpdir.join('no-manifest'))
    create_repo(path)
    args = get_defaults()
    args['--x-assert-hostname'] = True
    tls_config = tls.TLSConfig()
    _, _, _, _, _, client = cli.process_arguments(
        path, args,
        client_cfg={
            'base_url': 'https://example.com:443/api/v1/',
            'tls': tls_config,
        },
        environ={'SW_NAMESPACE': 'eg'},
    )

    assert not client.adapters['https://'].assert_hostname


def test_args():
    args = [
        '--account=x', '--x-assert-hostname', 'build',
        '-d', 'foo', '-d', 'bar',
        '-t', 'latest', '-t', 'foo',
    ]
    parser = cli.argparser()
    arguments = cli.old_style_arg_dict(parser.parse_args(args))

    assert arguments == {
        '--account': 'x',
        '--dependents': ['foo', 'bar'],
        '--dump-file': None,
        '--exact': [],
        '--exclude': [],
        '--help': False,
        '--no-build': False,
        '--upto': [],
        '--x-assert-hostname': True,
        '-H': None,
        'TARGET': [],
        'build': True,
        'push': False,
        'images': False,
        'tags': ['foo', 'latest'],
    }


def test_args_2():
    args = [
        '--account=x', '--x-assert-hostname', 'build',
        '-d', 'foo', 'bar',
        '-t', 'foo', '--dirty', '--pull-cache',
    ]
    parser = cli.argparser()
    arguments = cli.old_style_arg_dict(parser.parse_args(args))

    assert arguments == {
        '--account': 'x',
        '--dependents': ['foo', 'bar'],
        '--dump-file': None,
        '--exact': [],
        '--exclude': [],
        '--help': False,
        '--no-build': False,
        '--upto': [],
        '--x-assert-hostname': True,
        '-H': None,
        'TARGET': [],
        'build': True,
        'push': False,
        'images': False,
        'tags': ['foo'],
    }


def test_args_base():
    args = ['build']
    parser = cli.argparser()
    arguments = cli.old_style_arg_dict(parser.parse_args(args))

    assert arguments == {
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
        'build': True,
        'push': False,
        'images': False,
        'tags': ['latest'],
    }
