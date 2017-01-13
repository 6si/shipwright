from __future__ import absolute_import

import docker
import pytest
from docker import utils as docker_utils


@pytest.fixture(scope='session')
def docker_client():
    client_cfg = docker_utils.kwargs_from_env()
    return docker.APIClient(version='1.21', **client_cfg)


@pytest.yield_fixture(scope='session')
def registry(docker_client):
    cli = docker_client
    cli.pull('registry', '2')
    cont = cli.create_container(
        'registry:2',
        ports=[5000],
        host_config=cli.create_host_config(
            port_bindings={
                5000: 5000,
            },
        ),
    )
    try:
        cli.start(cont)
        try:
            yield
        finally:
            cli.stop(cont)
    finally:
        cli.remove_container(cont, v=True, force=True)
