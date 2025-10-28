"""Settings management for the Libb-NLP API.

All LLM requests are routed through OpenRouter.

Optional environment variables:
- OPENROUTER_API_KEY: OpenRouter API key (required for LLM features)
- OPENROUTER_REFERER: OpenRouter referer URL
- OPENROUTER_TITLE: OpenRouter app title
"""

import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):

    openrouter_api_key: str | None = Field(default_factory=lambda: os.getenv('OPENROUTER_API_KEY'))

    openrouter_referer: str = Field(default_factory=lambda: os.getenv('OPENROUTER_REFERER', 'http://localhost:8000'))
    openrouter_title: str = Field(default_factory=lambda: os.getenv('OPENROUTER_TITLE', 'Libb-NLP API'))

    ticker_extraction_name_model: str = Field(default_factory=lambda: os.getenv('TICKER_EXTRACTION_NAME_MODEL', 'openai/gpt-4o-mini'))
    ticker_extraction_symbol_model: str = Field(default_factory=lambda: os.getenv('TICKER_EXTRACTION_SYMBOL_MODEL', 'openai/gpt-4o-mini-search-preview'))

    model_config = ConfigDict(case_sensitive=True, extra='ignore')


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns
        Settings instance with validated configuration
    """
    return Settings()
