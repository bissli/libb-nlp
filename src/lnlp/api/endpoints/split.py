import asyncio

from fastapi import APIRouter, HTTPException
from lnlp.api.deps import get_splitter_manager
from lnlp.schemas.split import SimilarityRequest, SpacyRequest, TextResponse

router = APIRouter()


@router.post('/split/spacy', response_model=TextResponse, tags=['splitting'])
async def split_text_spacy(request: SpacyRequest):
    """Split text into chunks using spaCy."""
    try:
        manager = get_splitter_manager()
        splitter = manager.get_spacy_splitter()
        chunks = await asyncio.to_thread(
            splitter.split_text,
            request.text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        return TextResponse(chunks=chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/split/similarity', response_model=TextResponse, tags=['splitting'])
async def split_text_similarity(request: SimilarityRequest):
    """Split text into chunks using semantic similarity."""
    try:
        manager = get_splitter_manager()
        splitter = manager.get_similarity_splitter()
        chunks = await asyncio.to_thread(splitter.split_text, request.text)
        return TextResponse(chunks=chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
