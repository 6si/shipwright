from __future__ import absolute_import

from shipwright import dependencies, image, source_control


def names_list(targets):
    return sorted(n.name for n in targets)


def _names(tree):
    return [n.name for n in dependencies._brood(tree)]


def target(name, dir_path, path, parent):
    return source_control.Target(
        image.Image(name, dir_path, path, parent, name),
        'abc', None,
    )

targets = [
    target(
        'shipwright_test/2', 'path2/', 'path2/Dockerfile',
        'shipwright_test/1',
    ),
    target(
        'shipwright_test/1', 'path1/', 'path1/Dockerfile',
        'ubuntu',
    ),
    target(
        'shipwright_test/3', 'path3/', 'path3/Dockerfile',
        'shipwright_test/2',
    ),
    target(
        'shipwright_test/independent', 'independent',
        'path1/Dockerfile', 'ubuntu',
    ),
]


def default_build_targets():
    return {
        'exact': [],
        'dependents': [],
        'upto': [],
        'exclude': [],
    }


def test_upto():
    bt = default_build_targets()
    bt['upto'] = ['shipwright_test/2']
    result = names_list(dependencies.eval(bt, targets))
    assert result == ['shipwright_test/1', 'shipwright_test/2']


def test_dependents():
    bt = default_build_targets()
    bt['dependents'] = ['shipwright_test/2']
    result = names_list(dependencies.eval(bt, targets))
    assert result == [
        'shipwright_test/1', 'shipwright_test/2', 'shipwright_test/3',
    ]


def test_exact():
    bt = default_build_targets()
    bt['exact'] = ['shipwright_test/2']
    result = names_list(dependencies.eval(bt, targets))
    assert result == ['shipwright_test/2']


def test_exclude():
    bt = default_build_targets()
    bt['exclude'] = ['shipwright_test/2', 'fake_exclude']
    result = names_list(dependencies.eval(bt, targets))
    assert result == ['shipwright_test/1', 'shipwright_test/independent']


def test_breadth_first_iter():
    bt = default_build_targets()
    results = [result.name for result in dependencies.eval(bt, targets)]
    assert results == [
        'shipwright_test/1',
        'shipwright_test/independent',
        'shipwright_test/2',
        'shipwright_test/3',
    ]


def test_make_tree():
    root = dependencies._make_tree(targets)
    assert root.node().name is None

    assert _names(root) == [
        'shipwright_test/1',
        'shipwright_test/independent',
        'shipwright_test/2',
        'shipwright_test/3',
    ]

    sr_test_1 = root.down().node()
    assert sr_test_1.image.name == 'shipwright_test/1'

    assert _names(root.down()) == ['shipwright_test/2', 'shipwright_test/3']

    sr_test_2 = root.down().down().node()
    assert sr_test_2.image.name == 'shipwright_test/2'

    assert _names(root.down().down()) == ['shipwright_test/3']
    assert root.down().right().node().name == 'shipwright_test/independent'
