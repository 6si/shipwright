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


def test_dirty_tags(tmpdir):
    tmp = tmpdir.join('shipwright-sample')
    path = str(tmp)
    source = pkg_resources.resource_filename(
        __name__,
        'examples/shipwright-sample',
    )
    repo = create_repo(path, source)

    scm = source_control.GitSourceControl(
        path=path,
        namespace='shipwright',
        name_map={},
    )

    def refs():
        return {target.image.name: target.ref for target in scm.targets()}
    clean_refs = refs()
    clean_ref_str = scm.this_ref_str()

    tmp.join('shared/base.txt').write('Hi mum')  # Untracked

    assert refs()['shipwright/base'] == clean_refs['shipwright/base']
    assert refs()['shipwright/shared'] != clean_refs['shipwright/shared']
    assert refs()['shipwright/service1'] != clean_refs['shipwright/service1']
    assert '-dirty-' in refs()['shipwright/service1']
    assert '-dirty-' in refs()['shipwright/shared']
    assert clean_ref_str != scm.this_ref_str()

    repo.index.add(['shared/base.txt'])  # Tracked

    assert refs()['shipwright/base'] == clean_refs['shipwright/base']
    assert refs()['shipwright/shared'] != clean_refs['shipwright/shared']
    assert refs()['shipwright/service1'] != clean_refs['shipwright/service1']
    assert '-dirty-' in refs()['shipwright/service1']
    assert '-dirty-' in refs()['shipwright/shared']
    assert clean_ref_str != scm.this_ref_str()

    tmp.join('base/base.txt').write('Hi again')  # Modified, not added to index
    assert refs()['shipwright/base'] != clean_refs['shipwright/base']

    repo.index.add(['base/base.txt'])  # Modified version added to index
    assert refs()['shipwright/base'] != clean_refs['shipwright/base']

    tmp.join('base/base.txt').remove()  # Deleted, but not removed from index
    assert refs()['shipwright/base'] != clean_refs['shipwright/base']

    repo.index.remove(['base/base.txt'])  # Remove from index
    assert refs()['shipwright/base'] != clean_refs['shipwright/base']
