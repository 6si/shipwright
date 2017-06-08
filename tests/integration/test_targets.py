from __future__ import absolute_import

import pkg_resources
import pytest

from shipwright import exceptions, targets

from . import utils


def test_simple(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = utils.create_repo(path, source)
    commit = repo.head.ref.commit.hexsha[:12]
    assert targets.targets(path=path) == [
        'shipwright/base:' + commit,
        'shipwright/base:master',
        'shipwright/base:' + commit,
        'shipwright/shared:' + commit,
        'shipwright/shared:master',
        'shipwright/shared:' + commit,
        'shipwright/service1:' + commit,
        'shipwright/service1:master',
        'shipwright/service1:' + commit,
    ]


def test_upto(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = utils.create_repo(path, source)
    commit = repo.head.ref.commit.hexsha[:12]
    assert targets.targets(path=path, upto=['shared']) == [
        'shipwright/base:' + commit,
        'shipwright/base:master',
        'shipwright/base:' + commit,
        'shipwright/shared:' + commit,
        'shipwright/shared:master',
        'shipwright/shared:' + commit,
    ]


def test_extra_tags(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = utils.create_repo(path, source)
    commit = repo.head.ref.commit.hexsha[:12]
    assert targets.targets(path=path, upto=['shared'], tags=['ham/spam']) == [
        'shipwright/base:' + commit,
        'shipwright/base:ham-spam',
        'shipwright/base:master',
        'shipwright/base:' + commit,
        'shipwright/shared:' + commit,
        'shipwright/shared:ham-spam',
        'shipwright/shared:master',
        'shipwright/shared:' + commit,
    ]


def test_no_repo(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    utils.create_repo(path, source)
    tmp.join('.git').remove(rec=1)
    with pytest.raises(exceptions.SourceControlNotFound):
        targets.targets(path=path)
