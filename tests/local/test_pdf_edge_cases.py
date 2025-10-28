"""Local PDF extraction edge case tests - no API required."""
import pytest
from lnlp.services.pdf import PDFTextExtractor


def test_text_cleaning():
    """Test text cleaning functionality."""
    extractor = PDFTextExtractor(b'dummy')  # Won't actually use this
    
    # Test zero-width characters removal
    text = 'Hello\u200bWorld'
    cleaned = extractor.clean_text(text)
    assert cleaned == 'Hello World'
    
    # Test smart quotes replacement
    text = '"Hello" and "World"'
    cleaned = extractor.clean_text(text)
    assert cleaned == '"Hello" and "World"'
    
    # Test em dash replacement
    text = 'Hello—World'
    cleaned = extractor.clean_text(text)
    assert cleaned == 'Hello-World'
    
    # Test multiple spaces collapsed
    text = 'Hello    World'
    cleaned = extractor.clean_text(text)
    assert cleaned == 'Hello World'
    
    # Test trailing whitespace removed
    text = 'Hello World   '
    cleaned = extractor.clean_text(text)
    assert cleaned == 'Hello World'


def test_page_number_patterns():
    """Test page number pattern matching."""
    patterns = PDFTextExtractor.PAGE_NUMBER_PATTERNS
    
    # Test basic page numbers
    assert any(__import__('re').match(p, '42', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').match(p, 'Page 42', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').match(p, '42 of 100', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').match(p, '- 42 -', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').match(p, '[ 42 ]', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').match(p, 'p. 42', __import__('re').IGNORECASE) for p in patterns)


def test_header_patterns():
    """Test header pattern matching."""
    patterns = PDFTextExtractor.HEADER_PATTERNS
    
    # Test various header patterns
    assert any(__import__('re').match(p, 'Chapter 5') for p in patterns)
    assert any(__import__('re').match(p, 'Section 3') for p in patterns)
    assert any(__import__('re').match(p, 'HEADER TEXT') for p in patterns)


def test_footer_patterns():
    """Test footer pattern matching."""
    patterns = PDFTextExtractor.FOOTER_PATTERNS
    
    # Test various footer patterns
    assert any(__import__('re').search(p, 'Copyright © 2024', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').search(p, '© 2024 Company', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').search(p, 'All Rights Reserved', __import__('re').IGNORECASE) for p in patterns)
    assert any(__import__('re').search(p, 'Confidential', __import__('re').IGNORECASE) for p in patterns)


def test_validate_page_numbers():
    """Test page number sequence validation."""
    extractor = PDFTextExtractor(b'dummy')
    
    # Valid sequences
    assert extractor._validate_page_numbers([1, 2, 3, 4])
    assert extractor._validate_page_numbers([1, 2, 4, 5])  # Gap of 2 allowed
    assert extractor._validate_page_numbers([5, 6, 7])
    
    # Invalid sequences
    assert not extractor._validate_page_numbers([1, 5, 10])  # Gap too large
    assert not extractor._validate_page_numbers([])  # Empty
    assert not extractor._validate_page_numbers([1, 1])  # No gap


def test_cluster_positions():
    """Test position clustering logic."""
    extractor = PDFTextExtractor(b'dummy')
    
    # Close positions should cluster
    positions = [0.1, 0.11, 0.12, 0.5, 0.51]
    clusters = extractor._cluster_positions(positions, threshold=0.05)
    
    assert len(clusters) == 2
    assert len(clusters[0]) == 3  # 0.1, 0.11, 0.12
    assert len(clusters[1]) == 2  # 0.5, 0.51


def test_config_override():
    """Test configuration override."""
    extractor = PDFTextExtractor(
        b'dummy',
        header_threshold=0.2,
        footer_threshold=0.9,
        min_repetition_ratio=0.5
    )
    
    assert extractor.config['header_threshold'] == 0.2
    assert extractor.config['footer_threshold'] == 0.9
    assert extractor.config['min_repetition_ratio'] == 0.5


def test_is_list_item():
    """Test list item detection."""
    extractor = PDFTextExtractor(b'dummy')
    
    # Indented, short text = list item
    assert extractor._is_list_item('Short item', indent=100, page_width=600)
    
    # Not indented = not list item
    assert not extractor._is_list_item('Short item', indent=10, page_width=600)
    
    # Too long = not list item
    long_text = ' '.join(['word'] * 25)
    assert not extractor._is_list_item(long_text, indent=100, page_width=600)
    
    # Empty = not list item
    assert not extractor._is_list_item('', indent=100, page_width=600)


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
