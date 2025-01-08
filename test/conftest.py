import os

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the directory containing test data files"""
    return os.path.join(os.path.dirname(__file__), 'data')
