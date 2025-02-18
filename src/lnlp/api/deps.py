from functools import lru_cache
from fastapi import HTTPException

from lnlp.services.provider import LLMProvider
from lnlp.services.splitters import SplitterManager
from lnlp.services.pdf import PDFTextExtractor

@lru_cache()
def get_provider():
    """Dependency to get LLM provider instance"""
    try:
        return LLMProvider()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@lru_cache()
def get_splitter_manager():
    """Dependency to get splitter manager instance"""
    return SplitterManager()

def get_pdf_extractor(pdf_input: bytes | str):
    """Dependency to get PDF extractor instance"""
    return PDFTextExtractor(pdf_input)
