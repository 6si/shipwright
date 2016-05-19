# -*- coding: utf-8 -*-
"""
Shipwright -- Builds shared Docker images within a common git repository.


Usage:
  shipwright [options] [build|push [--no-build]]
             [TARGET]...
             [-d TARGET]...
             [-e TARGET]...
             [-u TARGET]...
             [-x TARGET]...


Options:

 --help               Show all help information

 --dump-file=FILE     Save raw events to json to FILE. Useful for
                      debugging.

 -H DOCKER_HOST       Override DOCKER_HOST if it's set in the environment.

 --x-assert-hostname  Disable strict hostchecking, useful for boot2docker.

 --account=DOCKER_HUB_ACCOUNT Override SW_NAMESPACE if it's set in the
                      environment.




Specifiers:

  -d --dependents=TARGET  Build TARGET and all its dependents

  -e --exact=TARGET       Build TARGET only - may fail if
                          dependencies have not been built

  -u --upto=TARGET        Build TARGET and it dependencies

  -x --exclude=TARGET     Build everything but TARGET and
                          its dependents


Environment Variables:

  SW_NAMESPACE : If DOCKER_HUB_ACCOUNT is not passed on the command line
   this Environment variable must be present.

  DOCKER_HOST : Same URL as used by the docker client to connect to
    the docker daemon.

Examples:

  Assuming adependencies tree that looks like this.

  ubuntu
    └─── base
        └─── shared
        |     ├─── service1
        |     |     └─── service2
        |     └─── service3
        └─── independent


  Build everything:

    $ shipwright

  Build base, shared and service1:

    $ shipwright service1

  Build base, shared and service1, service2:

    $ shipwright -d service1

  Use exclude to build base, shared and service1, service2:

    $ shipwright -x service3 -x independent

  Build base, independent, shared and service3

    $ shipwright -x service1

  Build base, independent, shared and service1, service2:

    $ shipwright -d service1 -u independent

  Note that specfying a TARGET is the same as -u so the following
  command is equivalent to the one above.

  $ shipwright -d service1 independent


"""
from __future__ import absolute_import, print_function

import functools
import json
import os
import sys
from itertools import chain, cycle

import docker
import git
import pkg_resources
from docker.utils import kwargs_from_env
from docopt import docopt

from shipwright.base import Shipwright
from shipwright.colors import rainbow
from shipwright.dependencies import dependents, exact, exclude, upto


def main():
    version = pkg_resources.get_distribution('dockhand').version
    arguments = docopt(
        __doc__, options_first=False, version='Shipwright ' + version,
    )
    return run(
        repo=git.Repo(os.getcwd()),
        arguments=arguments,
        client_cfg=kwargs_from_env(),
        environ=os.environ,
    )


def process_arguments(repo, arguments, client_cfg, environ):
    try:
        config = json.load(open(
            os.path.join(repo.working_dir, '.shipwright.json'),
        ))
    except IOError:
        config = {
            'namespace': (
                arguments['--account'] or
                environ.get('SW_NAMESPACE')
            ),
        }
    if config['namespace'] is None:
        exit(
            'Please specify your docker hub account in\n'
            'the .shipwright.json config file,\n '
            'the command line or set SW_NAMESPACE.\n'
            'Run shipwright --help for more information.',
        )
    assert_hostname = config.get('assert_hostname')
    if arguments['--x-assert-hostname']:
        assert_hostname = not arguments['--x-assert-hostname']

    tls_config = client_cfg.get('tls')
    if tls_config is not None:
        tls_config.assert_hostname = assert_hostname

    client = docker.Client(version='1.18', **client_cfg)
    commands = ['build', 'push']
    command_names = [c for c in commands if arguments[c]]
    command_name = command_names[0] if command_names else 'build'
    pt = functools.partial

    args = [chain(
        [pt(exact, target) for target in arguments.pop('--exact')],
        [pt(dependents, target) for target in arguments.pop('--dependents')],
        [pt(exclude, target) for target in arguments.pop('--exclude')],
        [pt(upto, target) for target in arguments.pop('--upto')],
        [pt(upto, target) for target in arguments.pop('TARGET')],
    )]
    if command_name == 'push':
        args.append(not arguments.pop('--no-build'))
    dump_file = None
    if arguments['--dump-file']:
        dump_file = open(arguments['--dump-file'], 'w')

    return args, command_name, dump_file, config, client


def run(repo, arguments, client_cfg, environ):
    args, command_name, dump_file, config, client = process_arguments(
        repo, arguments, client_cfg, environ,
    )
    command = getattr(Shipwright(config, repo, client), command_name)

    for event in command(*args):
        show_fn = mk_show(event)
        formatted_message = streamout(event, dump_file)
        if formatted_message is not None:
            show_fn(streamout(event, dump_file))


def streamout(event, dump_file):
    if dump_file:
        dump_file.write(json.dumps(event))
        dump_file.write('\n')
    return switch(event)


def exit(msg):
    print(msg)
    sys.exit(1)


def memo(f, arg, memos={}):
    if arg in memos:
        return memos[arg]
    else:
        memos[arg] = f(arg)
        return memos[arg]


def mk_show(evt):
    if evt['event'] in ('build_msg', 'push') or 'error' in evt:
        name = None
        container = evt.get('container')
        if container is not None:
            name = container.name
        else:
            name = evt.get('image')
        return memo(
            highlight,
            name,
        )
    else:
        return print

colors = cycle(rainbow())


def highlight(name):
    color_fn = next(colors)

    def highlight_(msg):
        print(color_fn(name) + ' | ' + msg)
    return highlight_


def switch(rec):

    if 'stream' in rec:
        return rec['stream'].strip('\n')

    elif 'status' in rec:
        if rec['status'].startswith('Downloading'):
            term = '\r'
        else:
            term = ''

        return '[STATUS] {0}: {1}{2}'.format(
            rec.get('id', ''),
            rec['status'],
            term,
        )
    elif 'error' in rec:
        return '[ERROR] {0}\n'.format(rec['errorDetail']['message'])
    elif rec['event'] == 'tag':
        return 'Tagging {image} to {name}:{tag}'.format(
            name=rec['container'].name,
            image=rec['image'],
            tag=rec['tag'],
        )
    elif rec['event'] == 'removed':
        return 'Untagging {image}:{tag}'.format(**rec)
    elif rec['event'] == 'push' and 'aux' in rec:
        return None
    else:
        return json.dumps(rec)
