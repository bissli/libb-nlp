"""Build with ./docker-ops -b before running. Will reuse container.
"""
import logging
import os
import time
from collections.abc import Generator

import docker
import pytest
import requests
from docker.models.containers import Container
import pathlib

# Configure logging - suppress pdfminer debug logs
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
def test_data_dir():
    """Return the directory containing test data files
    """
    return os.path.join(pathlib.Path(__file__).parent, 'data')


@pytest.fixture(scope='session', autouse=True)
def suppress_third_party_warnings():
    """Suppress known warnings from third-party libraries"""
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='pysbd')
    warnings.filterwarnings('ignore', message="Can't initialize NVML", module='torch.cuda')


@pytest.fixture(scope='session')
def docker_client() -> docker.DockerClient:
    """Create a Docker client"""
    return docker.from_env()


@pytest.fixture(scope='session')
def docker_container(docker_client: docker.DockerClient, docker_image) -> Generator[Container, None, None]:
    """Start the libb-nlp container and wait for it to be ready"""
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
        environment={'ENV': 'test'}
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
