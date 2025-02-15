import os
import time
from collections.abc import Generator

import docker
import pytest
import requests
from docker.models.containers import Container


@pytest.fixture(scope='session')
def test_data_dir():
    """Return the directory containing test data files
    """
    return os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture(scope='session')
def docker_client() -> docker.DockerClient:
    """Create a Docker client"""
    return docker.from_env()


@pytest.fixture(scope='session')
def docker_container(docker_client: docker.DockerClient) -> Generator[Container, None, None]:
    """Start the libb-nlp container and wait for it to be ready"""
    # Build and start container
    container = docker_client.containers.run(
        'libb-nlp:latest',
        detach=True,
        ports={'8000/tcp': 8000},
        environment={
            'ENV': 'test'
        }
    )

    # Wait for container to be ready
    max_retries = 30
    retry_interval = 1
    for _ in range(max_retries):
        try:
            response = requests.get('http://localhost:8000/health')
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(retry_interval)
    else:
        raise Exception('Container failed to become ready')

    yield container

    # Cleanup
    container.stop()
    container.remove()
