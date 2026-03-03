"""Dynamic Anthropic model resolution via OpenRouter.

Queries the OpenRouter models API and caches the latest haiku,
sonnet, and opus model IDs. Cache expires at midnight EST daily.
"""

import logging

import cachu
import pendulum
from lnlp.config import get_settings
from openai import OpenAI

logger = logging.getLogger(__name__)

cachu.configure(backend_default='memory')


def _seconds_until_midnight_est() -> int:
    """Compute seconds remaining until midnight EST.
    """
    now = pendulum.now('America/New_York')
    midnight = now.add(days=1).start_of('day')
    return int((midnight - now).total_seconds())


def _resolve_latest_model(family: str) -> str:
    """Query OpenRouter for the latest Anthropic model in a family.
    """
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError('OpenRouter API key not configured')

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url='https://openrouter.ai/api/v1',
        default_headers={
            'HTTP-Referer': settings.openrouter_referer,
            'X-Title': settings.openrouter_title,
            },
        )

    response = client.models.list()
    candidates = [
        m for m in response.data
        if family in m.id and 'anthropic' in m.id
        ]
    if not candidates:
        raise ValueError(f'No {family} models found on OpenRouter')

    latest = max(candidates, key=lambda m: m.created)
    logger.debug(f'Resolved latest {family} model: {latest.id}')
    return latest.id


@cachu.cache(ttl=lambda _result: _seconds_until_midnight_est())
def get_latest_haiku() -> str:
    """Get the latest Anthropic Haiku model ID from OpenRouter.
    """
    return _resolve_latest_model('haiku')


@cachu.cache(ttl=lambda _result: _seconds_until_midnight_est())
def get_latest_sonnet() -> str:
    """Get the latest Anthropic Sonnet model ID from OpenRouter.
    """
    return _resolve_latest_model('sonnet')


@cachu.cache(ttl=lambda _result: _seconds_until_midnight_est())
def get_latest_opus() -> str:
    """Get the latest Anthropic Opus model ID from OpenRouter.
    """
    return _resolve_latest_model('opus')
