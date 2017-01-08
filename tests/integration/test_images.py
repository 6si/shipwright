from __future__ import absolute_import

import argparse

import pkg_resources
from docker import utils as docker_utils

from shipwright import cli as shipw_cli

from .utils import create_repo, get_defaults


def default_args():
    return argparse.Namespace(dirty=False, pull_cache=False)


def test_sample(tmpdir, capsys):
    path = str(tmpdir.join('shipwright-sample'))
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    tag = repo.head.ref.commit.hexsha[:12]

    client_cfg = docker_utils.kwargs_from_env()
    args = get_defaults()
    args['images'] = True

    shipw_cli.run(
        path=path,
        client_cfg=client_cfg,
        arguments=args,
        environ={},
    )

    out, err = capsys.readouterr()
    images = {'base', 'shared', 'service1'}
    tmpl = 'shipwright/{img}:{tag}'
    expected = {tmpl.format(img=i, tag=tag) for i in images}

    assert {l for l in out.split('\n') if l} == expected
