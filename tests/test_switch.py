from __future__ import absolute_import

from shipwright import cli


def switch(event):
    return cli.switch(event, True)

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


def test_progress():
    evt = {
        'status': 'Downloading xyz',
        'id': 'eg',
        'progressDetail': {'current': 10, 'total': 100},
    }
    assert cli.switch(evt, True) == '[STATUS] eg: Downloading xyz 10/100\r'


def test_hide_progress():
    evt = {
        'status': 'Downloading xyz',
        'id': 'eg',
        'progressDetail': {'current': 10, 'total': 100},
    }
    assert cli.switch(evt, False) is None


def test_error():
    assert switch({
        'error': None,
        'errorDetail': {
            'message': 'I AM ERROR',
        },
    }) == '[ERROR] I AM ERROR'
