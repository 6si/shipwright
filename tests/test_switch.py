from __future__ import absolute_import

from shipwright.cli import switch

aux = {
    u'aux': {
        u'Digest': u'sha256:redacted',
        u'Size': 1337,
        u'Tag': u'redacted',
    },
    'event': 'push',
    'image': u'redacted/redacted',
    u'progressDetail': {},
}

unhandled = {
    'event': 'unhandled',
}


def test_aux_record():
    assert switch(aux) is None


def test_unhandled_record():
    assert switch(unhandled) == '{"event": "unhandled"}'


def test_status():
    assert switch({
        'status': 'Not Downloading xyz',
        'id': 'eg',
    }) == '[STATUS] eg: Not Downloading xyz'


def test_status_downloading():
    assert switch({
        'status': 'Downloading xyz',
        'id': 'eg',
    }) == '[STATUS] eg: Downloading xyz\r'


def test_error():
    assert switch({
        'error': None,
        'errorDetail': {
            'message': 'I AM ERROR',
        },
    }) == '[ERROR] I AM ERROR\n'
