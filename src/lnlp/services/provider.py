import logging
import re

from lnlp.config import get_settings
from lnlp.schemas.chat import ProviderRequest, ProviderResponse
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified provider for LLM API access with automatic parameter optimization"""

    _models_cache = None
    DEFAULT_TEMPERATURE = 0.1

    def __init__(self):
        settings = get_settings()

        self.openrouter_key = settings.openrouter_api_key
        self.openrouter_referer = settings.openrouter_referer
        self.openrouter_title = settings.openrouter_title

        if not self.openrouter_key:
            logger.warning('OpenRouter API key not configured - LLM features will be unavailable')

    def _strip_openrouter_prefix(self, model: str) -> str:
        """Remove openrouter/ prefix from model name if present"""
        if model.startswith('openrouter/'):
            return model.replace('openrouter/', '', 1)
        return model

    async def _get_model_info(self, model: str) -> dict | None:
        """Get model information from OpenRouter API"""
        models = await self._fetch_openrouter_models()
        for model_info in models:
            if model_info['id'] == model:
                return model_info
        return None

    async def query(self, request: ProviderRequest) -> ProviderResponse:
        """Send chat completion request to OpenRouter with optimized parameters"""
        if not self.openrouter_key:
            raise ValueError('OpenRouter API key not configured')

        total_chars = sum(len(m.content) for m in request.messages)
        estimated_tokens = total_chars // 4
        logger.info(f'Query request - Model: {request.model}, Messages: {len(request.messages)}, '
                    f'Total chars: {total_chars:,}, Estimated tokens: {estimated_tokens:,}')

        return await self._openrouter_completion(request)

    async def _openrouter_completion(self, request: ProviderRequest) -> ProviderResponse:
        """Handle OpenRouter API requests with automatic parameter optimization"""
        model = self._strip_openrouter_prefix(request.model)

        model_info = await self._get_model_info(model)
        if not model_info:
            logger.warning(f'Could not fetch model info for {model}, using defaults')

        params = {
            'model': model,
            'messages': [{'role': 'user', 'content': m.content} for m in request.messages],
            'temperature': self.DEFAULT_TEMPERATURE,
        }

        if request.max_tokens is not None:
            params['max_tokens'] = request.max_tokens
        elif model_info and model_info.get('context_length'):
            params['max_tokens'] = model_info['context_length']

        logger.debug(f'Querying {model} with params: temperature={params["temperature"]}, '
                     f'max_tokens={params.get("max_tokens", "unspecified")}')

        client = AsyncOpenAI(
            api_key=self.openrouter_key,
            base_url='https://openrouter.ai/api/v1',
            default_headers={
                'HTTP-Referer': self.openrouter_referer,
                'X-Title': self.openrouter_title
            }
        )
        response = await client.chat.completions.create(**params)

        return ProviderResponse(
            id=response.id,
            model=response.model,
            choices=[choice.model_dump() for choice in response.choices],
            usage=response.usage.model_dump(),
            created=response.created
        )

    async def _fetch_openrouter_models(self) -> list[dict]:
        """Fetch available models from OpenRouter API with caching"""

        if self._models_cache is not None:
            return self._models_cache

        if not self.openrouter_key:
            logger.warning('OpenRouter API key not configured - cannot fetch models')
            return []

        client = AsyncOpenAI(
            api_key=self.openrouter_key,
            base_url='https://openrouter.ai/api/v1',
            default_headers={
                'HTTP-Referer': self.openrouter_referer,
                'X-Title': self.openrouter_title
            }
        )

        models_response = await client.models.list()
        self._models_cache = [model.dict() for model in models_response.data]

        logger.debug(f'Fetched {len(self._models_cache)} models from OpenRouter API')
        return self._models_cache

    async def get_available_models(self) -> list[tuple[str, int | None]]:
        """Get list of available models with context lengths from OpenRouter"""
        if not self.openrouter_key:
            logger.warning('OpenRouter API key not configured - no models available')
            return []

        try:
            openrouter_models = await self._fetch_openrouter_models()
            return [
                (f"openrouter/{model['id']}", model.get('context_length'))
                for model in openrouter_models
            ]
        except Exception as e:
            logger.error(f'Failed to fetch OpenRouter models: {e}')
            return []

    async def extract_ticker(self, text: str) -> tuple[str | None, str | None]:
        """Extract company ticker symbol from source text using LLM.

        Args
            text: Source text to extract ticker from (e.g., earnings transcript)

        Returns
            Tuple of (ticker_symbol, company_name)
        """
        if not self.openrouter_key:
            raise ValueError('OpenRouter API key required for ticker extraction')

        logger.info(f'Ticker extraction - Input text length: {len(text):,} chars, '
                    f'Estimated tokens: {len(text) // 4:,}')

        settings = get_settings()

        client = AsyncOpenAI(
            api_key=self.openrouter_key,
            base_url='https://openrouter.ai/api/v1',
            default_headers={
                'HTTP-Referer': self.openrouter_referer,
                'X-Title': self.openrouter_title
            }
        )

        company_name_prompt = """Extract only the company name from this earnings transcript.
Reply with just the company name, nothing else. No explanations."""

        try:
            response = await client.chat.completions.create(
                model=settings.ticker_extraction_name_model,
                messages=[{'role': 'user', 'content': f'{company_name_prompt}\n\n{text[:3000]}'}],
                max_tokens=100,
                temperature=0,
            )
            company_name = response.choices[0].message.content.strip()

            if not company_name:
                logger.warning('Failed to extract company name from text')
                return None, None

            logger.debug(f'Extracted company name: {company_name}')
        except Exception as e:
            logger.error(f'Error extracting company name: {e}')
            return None, None

        ticker_prompt = f"""What is the stock ticker symbol for {company_name}?
Reply with ONLY the ticker symbol itself (e.g., AAPL, TSLA, MSFT).
Do not include any explanation, markdown, formatting, or additional information. Just the ticker."""

        try:
            response = await client.chat.completions.create(
                model=settings.ticker_extraction_symbol_model,
                messages=[{'role': 'user', 'content': ticker_prompt}],
                max_tokens=50,
                temperature=0,
            )
            ticker_response = response.choices[0].message.content.strip()

            match = re.search(r'\(([A-Z]{1,5})\)', ticker_response)
            if match:
                ticker = match.group(1)
            else:
                match = re.search(r'\b([A-Z]{1,5})\b', ticker_response)
                if match:
                    ticker = match.group(1)
                else:
                    ticker = re.sub(r'[^A-Z]', '', ticker_response.upper())[:5]

            if not ticker:
                logger.warning(f'Could not extract valid ticker from response: {ticker_response}')
                return None, company_name

            logger.debug(f'Extracted ticker from response: {ticker_response[:100]} -> {ticker}')
            return ticker, company_name

        except Exception as e:
            logger.error(f'Error extracting ticker symbol: {e}')
            return None, company_name
