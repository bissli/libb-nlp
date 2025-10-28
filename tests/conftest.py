"""Test configuration.

Test structure:
- test/api/ - API tests requiring docker container (build with ./docker-ops -b)
- test/local/ - Local tests that run without docker

Run only local tests: pytest test/local/
Run only API tests: pytest test/api/
Run all tests: pytest
"""
import logging
import os
import pathlib

import pytest

logging.getLogger('pdfminer').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

pytest_plugins = ['tests.fixtures.docker']


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
