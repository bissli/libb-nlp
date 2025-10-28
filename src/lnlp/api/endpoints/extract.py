import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from lnlp.api.deps import get_pdf_extractor, get_provider
from lnlp.schemas.extract import PDFResponse, TickerRequest, TickerResponse
from lnlp.services.provider import LLMProvider

router = APIRouter()


logger = logging.getLogger(__name__)


@router.post('/extract/pdf', response_model=PDFResponse, tags=['extraction'])
async def extract_pdf(
    file: UploadFile = File(..., description='PDF file to process'),
    include_page_numbers: bool = Query(False, description='Include page number markers')
):
    """Extract text content from PDF files."""
    try:
        content = await file.read()
        extractor = get_pdf_extractor(content)
        text = await asyncio.to_thread(extractor.extract_lines, include_page_numbers=include_page_numbers)
        html_content = await asyncio.to_thread(extractor.extract_html, include_page_numbers=include_page_numbers)
        return PDFResponse(text=text, html=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/extract/ticker', response_model=TickerResponse, tags=['extraction'])
async def extract_ticker(
    request: TickerRequest,
    provider: LLMProvider = Depends(get_provider)
):
    """Extract company ticker symbol from text using LLM.

    Example request:
        ```python
        response = requests.post(
            'http://localhost:8000/extract/ticker',
            json={'text': 'earnings transcript text...'}
        )
        ```
    """
    logger.info(f'Ticker extraction request - Text length: {len(request.text):,} chars')

    try:
        ticker, company_name = await provider.extract_ticker(request.text)
        return TickerResponse(ticker=ticker, company_name=company_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f'Ticker extraction error: {e}')
        raise HTTPException(status_code=500, detail=str(e))
