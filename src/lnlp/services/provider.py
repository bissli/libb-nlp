import logging
import time
from typing import Literal

import httpx
from lnlp.config import get_settings
from lnlp.schemas.chat import ProviderRequest, ProviderResponse

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified provider for LLM API access"""

    SUPPORTED_MODELS = {
        'openai': ['openai/o1-mini', 'openai/o3-mini'],
        'anthropic': [
            'anthropic/claude-3.5-sonnet',
            'anthropic/claude-sonnnet-4'
            ],
        'openrouter': [
            'openrouter/openai/o1-mini',
            'openrouter/openai/o3-mini',
            'openrouter/openai/gpt-4o-mini',
            'openrouter/anthropic/claude-3.5-sonnet',
            'openrouter/anthropic/claude-sonnet-4'
        ]
    }

    def __init__(self):
        settings = get_settings()

        self.openai_key = settings.openai_api_key
        self.anthropic_key = settings.anthropic_api_key
        self.openrouter_key = settings.openrouter_api_key
        self.openrouter_referer = settings.openrouter_referer
        self.openrouter_title = settings.openrouter_title

        if not any([self.openai_key, self.anthropic_key, self.openrouter_key]):
            logger.warning('No API keys configured - LLM features will be unavailable')

    def _strip_provider_prefix(self, model: str, provider: str) -> str:
        """Remove provider prefix from model name if present"""
        return model.replace(f'{provider}/', '')

    def _get_provider_for_model(self, model: str) -> Literal['openai', 'anthropic', 'openrouter']:
        """Determine which provider to use based on model name prefix"""
        provider = model.split('/')[0]

        # Map of providers to their API keys
        provider_keys = {
            'openrouter': self.openrouter_key,
            'openai': self.openai_key,
            'anthropic': self.anthropic_key
        }

        if provider not in provider_keys:
            raise ValueError(f'Unknown provider: {provider}')

        if not provider_keys[provider]:
            raise ValueError(f'{provider.title()} API key not configured')

        return provider

    async def query(self, request: ProviderRequest) -> ProviderResponse:
        """Send chat completion request to appropriate provider"""
        provider = self._get_provider_for_model(request.model)

        match provider:
            case 'openrouter':
                return await self._openrouter_completion(request)
            case 'openai':
                return await self._openai_completion(request)
            case 'anthropic':
                return await self._anthropic_completion(request)
            case _:
                raise ValueError(f'Unknown provider: {provider}')

    async def _openrouter_completion(self, request: ProviderRequest) -> ProviderResponse:
        """Handle OpenRouter API requests"""
        headers = {
            'HTTP-Referer': self.openrouter_referer,
            'X-Title': self.openrouter_title,
            'Authorization': f'Bearer {self.openrouter_key}'
        }

        # Strip provider prefix from model
        model = self._strip_provider_prefix(request.model, 'openrouter')

        async with httpx.AsyncClient() as client:
            # Get provider defaults and override with any specified values
            defaults = request.get_defaults()
            messages = [{'role': 'user', 'content': m.content} for m in request.messages]
            request_data = {
                'model': model,
                'messages': messages,
                **defaults
            }
            # Override defaults with any specified values
            request_data.update({k: v for k, v in request.model_dump().items() if k not in {'model', 'messages'} and v is not None})
            response = await client.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=request_data
            )
            response.raise_for_status()
            data = response.json()

            return ProviderResponse(**data)

    async def _openai_completion(self, request: ProviderRequest) -> ProviderResponse:
        """Handle OpenAI API requests"""
        from openai import AsyncOpenAI

        # Strip provider prefix and create base params
        model = self._strip_provider_prefix(request.model, 'openai')
        params = {
            'model': model,
            'messages': [{'role': 'user', 'content': m.content} for m in request.messages],
        }

        # Add optional parameters only if they are not None
        optional_params = {
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'top_p': request.top_p,
            'frequency_penalty': request.frequency_penalty,
            'presence_penalty': request.presence_penalty,
            'stop': request.stop
        }

        # Add only non-None optional parameters
        params.update({k: v for k, v in optional_params.items() if v is not None})

        client = AsyncOpenAI(api_key=self.openai_key)
        response = await client.chat.completions.create(**params)

        return ProviderResponse(
            id=response.id,
            model=response.model,
            choices=[choice.dict() for choice in response.choices],
            usage=response.usage.dict(),
            created=response.created
        )

    async def _anthropic_completion(self, request: ProviderRequest) -> ProviderResponse:
        """Handle Anthropic API requests"""
        from anthropic import AsyncAnthropic

        # Strip provider prefix and create base params
        model = self._strip_provider_prefix(request.model, 'anthropic')
        params = {
            'model': model,
            'messages': [{'role': 'user', 'content': m.content} for m in request.messages],
        }

        # Add optional parameters only if they are not None
        optional_params = {
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'top_p': request.top_p,
            'stop_sequences': request.stop
        }

        # Add only non-None optional parameters
        params.update({k: v for k, v in optional_params.items() if v is not None})

        client = AsyncAnthropic(api_key=self.anthropic_key)
        response = await client.messages.create(**params)

        return ProviderResponse(
            id=response.id,
            model=request.model,
            choices=[{
                'message': {
                    'role': response.role,
                    'content': response.content
                },
                'finish_reason': response.stop_reason
            }],
            usage={
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens
            },
            created=int(time.time())
        )

    def get_available_models(self) -> list[str]:
        """Get list of available models based on configured API keys"""
        models = []
        if self.openrouter_key:
            models.extend(self.SUPPORTED_MODELS['openrouter'])
        if self.openai_key:
            models.extend(self.SUPPORTED_MODELS['openai'])
        if self.anthropic_key:
            models.extend(self.SUPPORTED_MODELS['anthropic'])
        return models
