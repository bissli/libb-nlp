import logging

from fastapi import APIRouter, Depends, HTTPException
from lnlp.api.deps import get_provider
from lnlp.schemas.chat import ModelInfo, ProviderRequest, ProviderResponse
from lnlp.services.provider import LLMProvider

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/chat/query', response_model=ProviderResponse, tags=['ai'])
async def query(
    request: ProviderRequest,
    provider: LLMProvider = Depends(get_provider)
):
    """Endpoint for GPT-style completions through various providers.

    Example request:
        ```python
        response = requests.post(
            'http://localhost:8000/chat/query',
            json={
            'model': 'openrouter/openai/gpt-4o-mini',
            'messages': [
                {'content': 'prompt text'}
            ],
            'max_tokens': 100000,
            'temperature': 0.1
        })
        ```
    """
    # Log the request (excluding prompt content)
    logger.info(
        'Chat completion request - Model: %s, Options: %s',
        request.model,
        {
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'top_p': request.top_p,
            'frequency_penalty': request.frequency_penalty,
            'presence_penalty': request.presence_penalty,
            'stop': request.stop
        }
    )
    try:
        return await provider.query(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/models', response_model=list[ModelInfo], tags=['ai'])
async def list_available_models(
    provider: LLMProvider = Depends(get_provider)
):
    """List available models across all providers"""
    available_models = provider.get_available_models()
    return [
        ModelInfo(
            name=model,
            provider=model.split('/')[0] if '/' in model else 'openai',
            max_tokens=None,
            features=['chat']
        )
        for model in available_models
    ]
