import os

import numpy as np
import pytest


@pytest.fixture(scope='session', autouse=True)
def setup_torch():
    """Configure torch before any tests run"""
    import torch
    if torch.cuda.is_available():
        torch.set_grad_enabled(False)
        torch.cuda.empty_cache()
    return torch


@pytest.fixture(scope='session')
def chunker():
    """Return a TextSplitterSimilarity instance"""
    from lnlp import TextSplitterSimilarity
    return TextSplitterSimilarity()


@pytest.fixture(scope='session')
def sample_text_long(test_data_dir):
    with open(os.path.join(test_data_dir, 'paragraph-long.txt')) as f:
        return f.read().strip()


@pytest.fixture(scope='session')
def sample_text_short(test_data_dir):
    with open(os.path.join(test_data_dir, 'paragraph-short.txt')) as f:
        return f.read().strip()


@pytest.fixture
def sample_similarities():
    """Return a sample similarity matrix for testing"""
    return np.array([[1.0, 0.8, 0.6],
                    [0.8, 1.0, 0.7],
                    [0.6, 0.7, 1.0]])


def test_chunker_initialization(chunker):
    assert chunker.model_name == 'all-mpnet-base-v2'
    assert chunker.model is not None
    assert chunker.seg is not None


def test_rev_sigmoid(chunker):
    result = chunker._rev_sigmoid(0)
    assert isinstance(result, float)
    assert 0 < result < 1
    assert abs(result - 0.5) < 0.01  # Should be close to 0.5 at x=0


def test_activate_similarities(chunker, sample_similarities):
    result = chunker._activate_similarities(sample_similarities, p_size=2)
    assert isinstance(result, np.ndarray)
    assert len(result) == 3


def test_split_text_long(chunker, sample_text_long):
    result = chunker.split_text(sample_text_long)
    assert isinstance(result, list)
    assert len(result) > 0

    # check that there enough of them (but not too many)
    assert 5 < len(result) < 15

    # Original text should be similar length to result (accounting for added newlines)
    joined = '\n\n'.join(result)
    assert abs(len(joined) - len(sample_text_long)) <= joined.count('\n\n') * 2


def test_split_text_short(chunker, sample_text_short):
    result = chunker.split_text(sample_text_short)
    assert isinstance(result, list)

    # Check if text contains paragraph breaks
    assert len(result) == 1

    # Original text should be similar length to result (accounting for added newlines)
    joined = '\n\n'.join(result)
    assert abs(len(joined) - len(sample_text_short)) == 0


if __name__ == '__main__':
    __import__('pytest').main([__file__])
