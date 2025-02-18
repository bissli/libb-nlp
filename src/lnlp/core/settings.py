"""Settings management for the Libb-NLP API.

Optional environment variables:
- OPENAI_API_KEY: OpenAI API key
- ANTHROPIC_API_KEY: Anthropic API key
- OPENROUTER_API_KEY: OpenRouter API key
- OPENROUTER_REFERER: OpenRouter referer URL
- OPENROUTER_TITLE: OpenRouter app title
"""

import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):

    # API Keys
    openai_api_key: str | None = os.getenv('OPENAI_API_KEY')
    anthropic_api_key: str | None = os.getenv('ANTHROPIC_API_KEY')
    openrouter_api_key: str | None = os.getenv('OPENROUTER_API_KEY')

    # OpenRouter Config
    openrouter_referer: str = os.getenv('OPENROUTER_REFERER', 'http://localhost:8000')
    openrouter_title: str = os.getenv('OPENROUTER_TITLE', 'Libb-NLP API')

    class Config:
        case_sensitive = True
        extra = 'ignore'


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns
        Settings instance with validated configuration
    """
    return Settings()
