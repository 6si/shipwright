from __future__ import absolute_import

import pkg_resources
import pytest

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


def _refs(targets):
    return {target.image.name: target.ref for target in targets}


def test_dirty_tags_untracked(tmpdir):
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
    assert not scm.is_dirty()

    old_refs = _refs(scm.targets())
    old_ref_str = scm.this_ref_str()
    tag = repo.head.ref.commit.hexsha[:12]

    tmp.join('shared/base.txt').write('Hi mum')  # Untracked
    assert scm.is_dirty()

    new_refs = _refs(scm.targets())
    new_ref_str = scm.this_ref_str()

    assert new_refs['shipwright/base'] == old_refs['shipwright/base']
    assert new_refs['shipwright/shared'] != old_refs['shipwright/shared']
    assert new_refs['shipwright/service1'] != old_refs['shipwright/service1']

    dirty_tag = tag + '-dirty-adc37b7d003f'
    assert new_refs == {
        'shipwright/base': tag,
        'shipwright/service1': dirty_tag,
        'shipwright/shared': dirty_tag,
    }
    assert old_ref_str == tag
    assert new_ref_str == dirty_tag


def test_dirty_tags_new_dir(tmpdir):
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
    assert not scm.is_dirty()

    old_ref_str = scm.this_ref_str()
    tag = repo.head.ref.commit.hexsha[:12]

    tmp.join('service2').mkdir()
    tmp.join('service2/Dockerfile').write('FROM busybox\n')
    assert scm.is_dirty()

    new_refs = _refs(scm.targets())
    new_ref_str = scm.this_ref_str()

    dirty_suffix = '-dirty-f2f0df80ff0f'
    service2_tag = 'g' * 12 + dirty_suffix
    assert new_refs['shipwright/base'] == tag
    assert new_refs['shipwright/shared'] == tag
    assert new_refs['shipwright/service1'] == tag
    assert new_refs['shipwright/service2'] == service2_tag

    assert new_refs == {
        'shipwright/base': tag,
        'shipwright/service1': tag,
        'shipwright/shared': tag,
        'shipwright/service2': service2_tag,
    }
    assert old_ref_str == tag
    assert new_ref_str == tag + dirty_suffix


def test_dirty_tags_tracked(tmpdir):
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
    assert not scm.is_dirty()

    old_refs = _refs(scm.targets())
    old_ref_str = scm.this_ref_str()
    tag = repo.head.ref.commit.hexsha[:12]

    tmp.join('shared/base.txt').write('Hi mum')  # Untracked
    repo.index.add(['shared/base.txt'])
    assert scm.is_dirty()

    new_refs = _refs(scm.targets())
    new_ref_str = scm.this_ref_str()

    assert new_refs['shipwright/base'] == old_refs['shipwright/base']
    assert new_refs['shipwright/shared'] != old_refs['shipwright/shared']
    assert new_refs['shipwright/service1'] != old_refs['shipwright/service1']

    dirty_tag = tag + '-dirty-adc37b7d003f'
    assert new_refs == {
        'shipwright/base': tag,
        'shipwright/service1': dirty_tag,
        'shipwright/shared': dirty_tag,
    }
    assert old_ref_str == tag
    assert new_ref_str == dirty_tag


def _git_modified_not_added_to_index(tmp, repo):
    tmp.join('base/base.txt').write('Hi again')  # Modified, not added to index


def _git_modified_version_added_to_index(tmp, repo):
    tmp.join('base/base.txt').write('Hi again')
    repo.index.add(['base/base.txt'])  # Modified version added to index
    return '-dirty-5227fefb4c30'


def _git_deleted_but_not_removed_from_index(tmp, repo):
    tmp.join('base/base.txt').write('Hi again')
    repo.index.add(['base/base.txt'])  # Modified version added to index
    tmp.join('base/base.txt').remove()  # Deleted, but not removed from index


def _git_remove_from_index(tmp, repo):
    tmp.join('base/base.txt').write('Hi again')
    repo.index.add(['base/base.txt'])  # Modified version added to index
    tmp.join('base/base.txt').remove()  # Deleted, but not removed from index
    repo.index.remove(['base/base.txt'])  # Remove from index


_various_git_functions = [
    _git_modified_not_added_to_index,
    _git_modified_version_added_to_index,
    _git_deleted_but_not_removed_from_index,
    _git_remove_from_index,
]


@pytest.mark.parametrize('func', _various_git_functions)
def test_dirty_tags_various(func, tmpdir):
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
    assert not scm.is_dirty()

    old_refs = _refs(scm.targets())
    old_ref_str = scm.this_ref_str()
    tag = repo.head.ref.commit.hexsha[:12]

    expected_tag_suffix = func(tmp, repo) or '-dirty-0d6d6d2f8739'
    assert scm.is_dirty()

    new_refs = _refs(scm.targets())
    new_ref_str = scm.this_ref_str()

    assert new_refs['shipwright/base'] != old_refs['shipwright/base']
    dirty_tag = tag + expected_tag_suffix
    assert new_refs == {
        'shipwright/base': dirty_tag,
        'shipwright/service1': dirty_tag,
        'shipwright/shared': dirty_tag,
    }
    assert old_ref_str == tag
    assert new_ref_str == dirty_tag
