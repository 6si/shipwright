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
import collections
import json
import os
import re
import shlex
import sys
from itertools import chain, cycle

import docker
from docker.utils import kwargs_from_env

from . import cache, registry, source_control
from .base import Shipwright
from .colors import rainbow

try:
    import docker_registry_client as drc
except ImportError as e:
    drc = e


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

    desc = 'Builds shared Docker images within a common repository'
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
    common.add_argument(
        '--dirty',
        help='Build working tree, including uncommited and untracked changes',
        action='store_true',
    )
    common.add_argument(
        '--pull-cache',
        help='When building try to pull previously built images',
        action='store_true',
    )
    a_arg(
        common, '--registry-login',
        help=(
            'When pulling cache and pushing tags, talk to a registry directly '
            'where possible'
        ),
    )
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
        'build', help='builds images', parents=[common],
    )

    subparsers.add_parser(
        'images', help='lists images to build', parents=[common],
    )

    push = subparsers.add_parser(
        'push', help='pushes built images', parents=[common],
    )
    push.add_argument('--no-build', action='store_true')

    return parser


def parse_registry_logins(registry_logins):
    parser = argparse.ArgumentParser(description='--registry-login')
    parser.add_argument('-u', '--username', nargs='?', help='Username')
    parser.add_argument('-p', '--password', nargs='?', help='Password')
    parser.add_argument('-e', '--email', nargs='?', help='Email')
    parser.add_argument('server', help='SERVER')

    registries = {}
    for login in registry_logins:
        args = shlex.split(re.sub(r'^docker login ', '', login, count=1))
        ns, _ = parser.parse_known_args(args)
        server = re.sub(r'^https?://', '', ns.server, count=1)
        registries[server] = {
            'username': ns.username,
            'password': ns.password,
            'server': ns.server,
        }

    return registries


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
        'images': ns.command == 'images',
        'tags': sorted(set(_flatten(ns.tags))) or ['latest'],
    }


def main():
    arguments = argparser().parse_args()
    old_style_args = old_style_arg_dict(arguments)
    return run(
        path=os.getcwd(),
        arguments=old_style_args,
        client_cfg=kwargs_from_env(),
        environ=os.environ,
        new_style_args=arguments,
    )


def process_arguments(path, arguments, client_cfg, environ):
    try:
        config = json.load(open(
            os.path.join(path, '.shipwright.json'),
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

    client = docker.APIClient(version='1.18', **client_cfg)
    commands = ['build', 'push', 'images']
    command_names = [c for c in commands if arguments.get(c)]
    command_name = command_names[0] if command_names else 'build'

    build_targets = {
        'exact': arguments['--exact'],
        'dependents': arguments['--dependents'],
        'exclude': arguments['--exclude'],
        'upto': arguments['--upto'],
    }

    no_build = False
    if command_name == 'push':
        no_build = arguments['--no-build']
    dump_file = None
    if arguments['--dump-file']:
        dump_file = open(arguments['--dump-file'], 'w')

    return build_targets, no_build, command_name, dump_file, config, client


class SetJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, collections.Set):
            return sorted(obj)
        return super(SetJSONEncoder, self).decode(obj)


def run(path, arguments, client_cfg, environ, new_style_args=None):
    args = process_arguments(
        path, arguments, client_cfg, environ,
    )
    build_targets, no_build, command_name, dump_file, config, client = args

    if new_style_args is None:
        dirty = False
        pull_cache = False
        registry_logins = []
    else:
        dirty = new_style_args.dirty
        pull_cache = new_style_args.pull_cache
        registry_logins = _flatten(new_style_args.registry_login)

    namespace = config['namespace']
    name_map = config.get('names', {})
    scm = source_control.source_control(path, namespace, name_map)
    if not dirty and scm.is_dirty():
        return (
            'Aborting build, due to uncommitted changes. If you are not ready '
            'to commit these changes, re-run with the --dirty flag.'
        )

    if registry_logins:
        if isinstance(drc, Exception):
            raise drc

        registry_config = parse_registry_logins(registry_logins)
        registries = {}
        for server, config in registry_config.items():
            registries[server] = drc.BaseClient(
                config['server'],
                username=config['username'],
                password=config['password'],
                api_version=2,
            )
        the_cache = cache.DirectRegistry(client, registry.Registry(registries))
    elif pull_cache:
        the_cache = cache.Cache(client)
    else:
        the_cache = cache.NoCache(client)

    sw = Shipwright(scm, client, arguments['tags'], the_cache)
    command = getattr(sw, command_name)

    show_progress = sys.stdout.isatty()

    errors = []

    if no_build:
        events = command(build_targets, no_build)
    else:
        events = command(build_targets)

    for event in events:
        if dump_file:
            json.dump(event, dump_file, cls=SetJSONEncoder)
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
    target = evt.get('target')
    if target is not None:
        name = target.name
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
    elif 'warn' in rec:
        return '[WARN] {0}'.format(rec['errorDetail']['message'])
    elif rec['event'] == 'tag':
        fmt = 'Tagging {rec[old_image]} to {rec[repository]}:{rec[tag]}'
        return fmt.format(rec=rec)
    elif rec['event'] == 'alias':
        fmt = 'Fast-aliased {rec[old_image]} to {rec[repository]}:{rec[tag]}'
        return fmt.format(rec=rec)
    elif rec['event'] == 'push' and 'aux' in rec:
        return None
    else:
        return json.dumps(rec)
