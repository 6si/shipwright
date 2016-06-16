from __future__ import absolute_import

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
        '--upto': [],
        '--x-assert-hostname': False,
        '-H': None,
        'TARGET': [],
        'build': False,
        'push': False,
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
