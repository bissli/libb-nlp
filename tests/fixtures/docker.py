"""Docker-related test fixtures."""
import os
import time
from collections.abc import Generator

import docker
import pytest
import requests
from docker.models.containers import Container


@pytest.fixture(scope='session')
def docker_image():
    """Construct ECR image name using same env vars as docker-compose
    """
    AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', '123456789')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    ECR_REPOSITORY = os.getenv('ECR_REPOSITORY', 'libb-nlp')
    IMAGE_TAG = os.getenv('IMAGE_TAG', 'latest')
    return f'{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}'


@pytest.fixture(scope='session')
def docker_client() -> docker.DockerClient:
    """Create a Docker client"""
    return docker.from_env()


@pytest.fixture(scope='session')
def docker_container(docker_client: docker.DockerClient, docker_image) -> Generator[Container, None, None]:
    """Start the libb-nlp container and wait for it to be ready.

    Only used by API tests in test_api.py.
    Local tests in test_pdf.py and test_splitters.py don't need this.
    """
    try:
        existing = docker_client.containers.list(filters={'publish': '8000'})
        for container in existing:
            container.stop()
            container.remove()
    except Exception as e:
        print(f'Warning: Failed to clean up existing containers: {e}')

    container = docker_client.containers.run(
        docker_image,
        detach=True,
        ports={'8000/tcp': 8000},
        environment={
            'ENV': 'test',
            'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY'),
            'OPENROUTER_REFERER': os.getenv('OPENROUTER_REFERER', 'http://localhost:8000'),
            'OPENROUTER_TITLE': os.getenv('OPENROUTER_TITLE', 'Libb-NLP API'),
        }
    )

    max_retries = 30
    retry_interval = 1
    session = requests.Session()
    for _ in range(max_retries):
        try:
            response = session.get('http://localhost:8000/health')
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(retry_interval)
    else:
        raise Exception('Container failed to become ready')
    session.close()

    yield container

    container.stop()
    container.remove()
