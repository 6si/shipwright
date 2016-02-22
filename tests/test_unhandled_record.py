from shipwright.cli import switch


example = {
    u'aux': {
        u'Digest': u'sha256:redacted',
        u'Size': 1337,
        u'Tag': u'redacted'
    },
    'event': 'push',
    'image': u'redacted/redacted',
    u'progressDetail': {},
}


def test_unhandled_record():
    assert isinstance(switch(example), str)
