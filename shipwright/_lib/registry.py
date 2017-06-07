from __future__ import absolute_import


class RegistryException(Exception):
    pass


class Registry(object):
    def __init__(self, registries):
        self._registries = registries

    def _get_registry_and_repo(self, name):
        registry_name, success, repository = name.partition('/')
        if not (registry_name or success or repository):
            raise RegistryException('name must be of the form registry/name')

        return self._registries[registry_name], repository

    def get_manifest(self, name, tag):
        client, repository = self._get_registry_and_repo(name)
        return client.get_manifest(repository, tag)

    def put_manifest(self, name, tag, manifest):
        client, repository = self._get_registry_and_repo(name)
        return client.put_manifest(repository, tag, manifest)
