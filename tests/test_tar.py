from __future__ import absolute_import

import tarfile

from shipwright import tar


def test_mkcontext(tmpdir):
    tmp = tmpdir.mkdir('image')
    docker_path = tmp.join('Dockerfile')
    docker_path.write('FROM example.com/r/image')
    tmp.join('bogus').write('hi mom')

    with tar.mkcontext('xyz', str(docker_path)) as f:
        with tarfile.open(fileobj=f, mode='a') as t:
            names = t.getnames()

    assert names == ['', 'bogus', 'Dockerfile']


def test_mkcontext_dockerignore(tmpdir):
    tmp = tmpdir.mkdir('image')
    docker_path = tmp.join('Dockerfile')
    docker_path.write('FROM example.com/r/image')
    tmp.join('.dockerignore').write('bogus2')
    tmp.join('bogus').write('hi mom')
    tmp.join('bogus2').write('This is ignored')

    with tar.mkcontext('xyz', str(docker_path)) as f:
        with tarfile.open(fileobj=f, mode='a') as t:
            names = t.getnames()

    assert names == ['', '.dockerignore', 'bogus', 'Dockerfile']
