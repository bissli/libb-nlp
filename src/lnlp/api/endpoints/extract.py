import asyncio

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from lnlp.api.deps import get_pdf_extractor
from lnlp.schemas.extract import PDFResponse

router = APIRouter()


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
