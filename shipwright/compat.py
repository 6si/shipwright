from __future__ import absolute_import

import json

def json_loads(s, **kwargs):
    if isinstance(s, bytes):
        s = s.decode('utf8')
    return json.loads(s, **kwargs)
