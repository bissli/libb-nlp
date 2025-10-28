from pydantic import BaseModel, Field


class PDFResponse(BaseModel):
    """Response model for PDF text extraction.

    Attributes
        text: List of extracted text lines
        html: Optional HTML-formatted version of the extracted text
    """
    text: list[str] = Field(..., description='List of extracted text lines')
    html: str | None = Field(None, description='HTML-formatted version of the extracted text')


class TickerRequest(BaseModel):
    """Request model for ticker symbol extraction.

    Attributes
        text: Source text to extract ticker from
    """
    text: str = Field(..., description='Source text to extract company ticker from')


class TickerResponse(BaseModel):
    """Response model for ticker symbol extraction.

    Attributes
        ticker: Extracted ticker symbol
        company_name: Extracted company name
    """
    ticker: str | None = Field(None, description='Extracted ticker symbol')
    company_name: str | None = Field(None, description='Extracted company name')
