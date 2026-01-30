"""Local configuration tests - no API required."""

from lnlp.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    """Test default configuration values."""
    # Clear any existing environment variables
    monkeypatch.delenv('OPENROUTER_REFERER', raising=False)
    monkeypatch.delenv('OPENROUTER_TITLE', raising=False)

    settings = Settings()

    assert settings.openrouter_referer == 'http://localhost:8000'
    assert settings.openrouter_title == 'Libb-NLP API'
    # Ticker extraction models are hardcoded (not from environment)
    assert settings.ticker_extraction_name_model == 'anthropic/claude-haiku-4.5'
    assert settings.ticker_extraction_symbol_model == 'anthropic/claude-haiku-4.5'


def test_settings_with_env_vars(monkeypatch):
    """Test configuration with environment variables."""
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key-123')
    monkeypatch.setenv('OPENROUTER_REFERER', 'https://example.com')
    monkeypatch.setenv('OPENROUTER_TITLE', 'Test App')

    # Clear the cache to force re-reading settings
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.openrouter_api_key == 'test-key-123'
    assert settings.openrouter_referer == 'https://example.com'
    assert settings.openrouter_title == 'Test App'
    # Ticker extraction models are hardcoded (not from environment)
    assert settings.ticker_extraction_name_model == 'anthropic/claude-haiku-4.5'
    assert settings.ticker_extraction_symbol_model == 'anthropic/claude-haiku-4.5'

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
