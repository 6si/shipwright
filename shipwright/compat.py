from __future__ import absolute_import

import json
import sys

PY2 = sys.version_info[0] == 2


if PY2:
    json_loads = json.loads
else:
    def json_loads(s, **kwargs):
        if isinstance(s, bytes):
            s = s.decode('utf8')
        return json.loads(s, **kwargs)
