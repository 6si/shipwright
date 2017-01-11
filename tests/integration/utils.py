from __future__ import absolute_import

import argparse
import shutil

import git


def get_defaults():
    return {
        '--account': None,
        '--dependents': [],
        '--dump-file': None,
        '--exact': [],
        '--exclude': [],
        '--help': False,
        '--no-build': False,
        '--dirty': False,
        '--upto': [],
        '--x-assert-hostname': False,
        '-H': None,
        'TARGET': [],
        'build': False,
        'push': False,
        'images': False,
        'tags': ['latest'],
    }


def create_repo(path, source):
    shutil.copytree(source, path)
    repo = git.Repo.init(path)
    repo.index.add(repo.untracked_files)
    repo.index.commit('Initial Commit')
    return repo


def commit_untracked(repo, message='WIP'):
    repo.index.add(repo.untracked_files)
    repo.index.commit(message)


def default_args():
    return argparse.Namespace(
        dirty=False,
        pull_cache=False,
        registry_login=[],
    )
