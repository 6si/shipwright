from __future__ import absolute_import

import json
import os

from . import dependencies, source_control


def targets(path='.', upto=None, tags=None, mode=None):
    if upto is None:
        upto = []
    try:
        config = json.load(open(
            os.path.join(path, '.shipwright.json'),
        ))
    except IOError:
        config = {
            'namespace': os.environ.get('SW_NAMESPACE'),
        }

    namespace = config['namespace']
    name_map = config.get('names', {})

    scm = source_control.source_control(path, namespace, name_map, mode)
    targets = dependencies.eval(
        {
            'upto': upto,
            'exact': [],
            'dependents': [],
            'exclude': [],
        },
        scm.targets(),
    )
    this_ref_str = scm.this_ref_str()
    default_tags = scm.default_tags()
    all_tags = (
        (tags if tags is not None else []) +
        default_tags +
        [this_ref_str]
    )

    def _targets():
        for image in targets:
            yield image.name + ':' + image.ref
            for tag in all_tags:
                yield image.name + ':' + tag.replace('/', '-')

    return list(_targets())
