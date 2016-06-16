from __future__ import absolute_import

import pkg_resources

from shipwright import source_control

from .utils import commit_untracked, create_repo


def test_default_tags_works_with_detached_head(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)
    old_commit = repo.head.ref.commit
    tmp.join('service1/base.txt').write('Hi mum')
    commit_untracked(repo)

    repo.head.reference = old_commit

    scm = source_control.GitSourceControl(
        path=path,
        namespace=None,
        name_map=None,
    )

    assert scm.default_tags() == []
