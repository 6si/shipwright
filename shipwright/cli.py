# -*- coding: utf-8 -*-
"""
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

    $ shipwright build

  Build base, shared and service1:

    $ shipwright build -u service1

  Build base, shared and service1, service2:

    $ shipwright build -d service1

  Use exclude to build base, shared and service1, service2:

    $ shipwright build -x service3 -x independent

  Build base, independent, shared and service3

    $ shipwright build -x service1

  Build base, independent, shared and service1, service2:

    $ shipwright build -d service1 -u independent

  Note that specfying a TARGET is the same as -u so the following
  command is equivalent to the one above.

  $ shipwright build -d service1 independent


"""
from __future__ import absolute_import, print_function

import argparse
import functools
import json
import os
import sys
from itertools import chain, cycle

import docker
import git
from docker.utils import kwargs_from_env

from shipwright.base import Shipwright
from shipwright.colors import rainbow
from shipwright.dependencies import dependents, exact, exclude, upto


def argparser():
    def a_arg(parser, *args, **kwargs):
        default = kwargs.pop('default', [])
        parser.add_argument(
            *args,
            action='append',
            nargs='*',
            default=default,
            **kwargs
        )

    desc = 'Builds shared Docker images within a common git repository'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '-H', '--docker-host',
        help="Override DOCKER_HOST if it's set in the environment.",
    )
    parser.add_argument(
        '--dump-file',
        help='Save raw events to json to FILE, Useful for debugging',
        type=argparse.FileType('w'),
    )
    parser.add_argument(
        '--x-assert-hostname',
        action='store_true',
        help='Disable strict hostchecking, useful for boot2docker.',
    )
    parser.add_argument(
        '--account',
        help="Override SW_NAMESPACE if it's set in the environment.",
    )

    subparsers = parser.add_subparsers(help='sub-command help', dest='command')
    subparsers.required = True

    common = argparse.ArgumentParser(add_help=False)
    a_arg(
        common, '-d', '--dependants',
        help='Build DEPENDANTS and all its dependants',
    )
    a_arg(
        common, '-e', '--exact',
        help='Build EXACT only - may fail if dependencies have not been built',
    )
    a_arg(
        common, '-u', '--upto',
        help='Build UPTO and it dependencies',
    )
    a_arg(
        common, '-x', '--exclude',
        help=' Build everything but EXCLUDE and its dependents',
    )
    a_arg(
        common, '-t', '--tag',
        dest='tags',
        help='extra tags to apply to the images',
    )

    subparsers.add_parser(
        'build', help='builds containers', parents=[common],
    )
    push = subparsers.add_parser(
        'push', help='pushes built containers', parents=[common],
    )
    push.add_argument('--no-build', action='store_true')

    return parser


def _flatten(items):
    return list(chain.from_iterable(items))


def old_style_arg_dict(namespace):
    ns = namespace
    return {
        '--account': ns.account,
        '--dependents': _flatten(ns.dependants),
        '--dump-file': ns.dump_file,
        '--exact': _flatten(ns.exact),
        '--exclude': _flatten(ns.exclude),
        '--help': False,
        '--no-build': getattr(ns, 'no_build', False),
        '--upto': _flatten(ns.upto),
        '--x-assert-hostname': ns.x_assert_hostname,
        '-H': ns.docker_host,
        'TARGET': [],
        'build': ns.command == 'build',
        'push': ns.command == 'push',
        'tags': sorted(set(_flatten(ns.tags))) or ['latest'],
    }


def main():
    arguments = old_style_arg_dict(argparser().parse_args())
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
    sw = Shipwright(config, repo, client, arguments['tags'])
    command = getattr(sw, command_name)

    show_progress = sys.stdout.isatty()

    errors = []

    for event in command(*args):
        if dump_file:
            dump_file.write(json.dumps(event))
            dump_file.write('\n')
        if 'error' in event:
            errors.append(event)
        msg = pretty_event(event, show_progress)
        if msg is not None:
            print(msg)

    if errors:
        print('The following errors occurred:', file=sys.stdout)
        messages = [pretty_event(error, True) for error in errors]
        for msg in sorted(m for m in messages if m is not None):
            print(msg, file=sys.stdout)
        sys.exit(1)


def exit(msg):
    print(msg)
    sys.exit(1)


def memo(f, arg, memos={}):
    if arg in memos:
        return memos[arg]
    else:
        memos[arg] = f(arg)
        return memos[arg]


def pretty_event(evt, show_progress):
    formatted_message = switch(evt, show_progress)
    if formatted_message is None:
        return
    if not (evt['event'] in ('build_msg', 'push') or 'error' in evt):
        return formatted_message

    name = None
    container = evt.get('container')
    if container is not None:
        name = container.name
    else:
        name = evt.get('image')
    prettify = memo(
        highlight,
        name,
    )
    return prettify(formatted_message)

colors = cycle(rainbow())


def highlight(name):
    color_fn = next(colors)

    def highlight_(msg):
        return color_fn(name) + ' | ' + msg
    return highlight_


def switch(rec, show_progress):

    if 'stream' in rec:
        return rec['stream'].strip('\n')

    elif 'status' in rec:
        status = '[STATUS] {0}: {1}'.format(
            rec.get('id', ''),
            rec['status'],
        )

        progress = rec.get('progressDetail')
        if progress:
            if show_progress:
                return '{status} {p[current]}/{p[total]}\r'.format(
                    status=status,
                    p=progress,
                )
            return None
        return status

    elif 'error' in rec:
        return '[ERROR] {0}'.format(rec['errorDetail']['message'])
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
