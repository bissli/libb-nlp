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
    """Endpoint for GPT-style completions with automatic parameter optimization.

    The API automatically sets optimal parameters based on the model:
    - Temperature: 0.1 (fixed for consistency)
    - Max tokens: Model's context_length (override with max_tokens parameter)

    Example request:
        ```python
        response = requests.post(
            'http://localhost:8000/chat/query',
            json={
                'model': 'openrouter/openai/gpt-4o-mini',
                'messages': [{'content': 'prompt text'}]
            }
        )
        ```
    """
    total_chars = sum(len(m.content) for m in request.messages)
    logger.info(f'Chat query request - Model: {request.model}, Messages: {len(request.messages)}, '
                f'Total chars: {total_chars:,}, max_tokens: {request.max_tokens or "auto"}')

    try:
        return await provider.query(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f'Chat query error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/models', response_model=list[ModelInfo], tags=['ai'])
async def list_available_models(
    provider: LLMProvider = Depends(get_provider)
):
    """List available models with context lengths"""
    available_models = await provider.get_available_models()
    return [
        ModelInfo(
            name=model_name,
            provider=model_name.split('/')[0] if '/' in model_name else 'openai',
            context_length=context_length,
            features=['chat']
        )
        for model_name, context_length in available_models
    ]
