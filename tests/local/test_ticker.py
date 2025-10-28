"""Local ticker extraction tests - require API keys but no docker."""
import os
import re

import pytest
from lnlp.config import get_settings
from lnlp.services.provider import LLMProvider


@pytest.fixture(scope='module')
def spot_transcript_text(test_data_dir):
    """Extract text from SPOT HTML transcript"""
    html_path = os.path.join(test_data_dir, 'transcripts', 'SPOT.html')
    with open(html_path) as f:
        html_content = f.read()

    # Remove HTML tags and extract text
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@pytest.fixture(scope='module')
def provider():
    """Create LLM provider instance"""
    return LLMProvider()


@pytest.fixture(scope='module', autouse=True)
def check_api_key():
    """Skip tests if OpenRouter API key is not configured"""
    settings = get_settings()
    if not settings.openrouter_api_key:
        pytest.skip('OpenRouter API key not configured')


@pytest.mark.asyncio
async def test_extract_ticker_from_spot_transcript(spot_transcript_text, provider):
    """Test ticker extraction from SPOT earnings call transcript"""
    ticker, company_name = await provider.extract_ticker(spot_transcript_text)

    assert ticker is not None, 'Ticker should be extracted'
    assert company_name is not None, 'Company name should be extracted'
    assert ticker == 'SPOT', f'Expected SPOT but got {ticker}'
    assert 'Spotify' in company_name, f'Expected Spotify in company name but got {company_name}'


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
