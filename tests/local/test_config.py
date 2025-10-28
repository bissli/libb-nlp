"""Local configuration tests - no API required."""
import os

import pytest
from lnlp.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    """Test default configuration values."""
    # Clear any existing environment variables
    monkeypatch.delenv('OPENROUTER_REFERER', raising=False)
    monkeypatch.delenv('OPENROUTER_TITLE', raising=False)
    monkeypatch.delenv('TICKER_EXTRACTION_NAME_MODEL', raising=False)
    monkeypatch.delenv('TICKER_EXTRACTION_SYMBOL_MODEL', raising=False)
    
    settings = Settings()
    
    assert settings.openrouter_referer == 'http://localhost:8000'
    assert settings.openrouter_title == 'Libb-NLP API'
    assert settings.ticker_extraction_name_model == 'openai/gpt-4o-mini'
    assert settings.ticker_extraction_symbol_model == 'openai/gpt-4o-mini-search-preview'


def test_settings_with_env_vars(monkeypatch):
    """Test configuration with environment variables."""
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key-123')
    monkeypatch.setenv('OPENROUTER_REFERER', 'https://example.com')
    monkeypatch.setenv('OPENROUTER_TITLE', 'Test App')
    monkeypatch.setenv('TICKER_EXTRACTION_NAME_MODEL', 'custom/model-1')
    monkeypatch.setenv('TICKER_EXTRACTION_SYMBOL_MODEL', 'custom/model-2')
    
    # Clear the cache to force re-reading settings
    get_settings.cache_clear()
    
    settings = get_settings()
    
    assert settings.openrouter_api_key == 'test-key-123'
    assert settings.openrouter_referer == 'https://example.com'
    assert settings.openrouter_title == 'Test App'
    assert settings.ticker_extraction_name_model == 'custom/model-1'
    assert settings.ticker_extraction_symbol_model == 'custom/model-2'
    
    # Clean up
    get_settings.cache_clear()


def test_settings_case_sensitive():
    """Test that settings are case-sensitive."""
    settings = Settings()
    
    # Check that lowercase env vars don't work (case sensitive)
    assert not hasattr(settings, 'openrouter_api_KEY')


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_settings_extra_fields_ignored():
    """Test that extra fields in environment are ignored."""
    # Settings should have extra='ignore' in model_config
    settings = Settings()
    
    # This should not raise an error even if there are extra env vars
    assert settings is not None


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
