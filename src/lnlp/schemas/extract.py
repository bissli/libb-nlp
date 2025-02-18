from pydantic import BaseModel, Field


class PDFResponse(BaseModel):
    """Response model for PDF text extraction.

    Attributes
        text: List of extracted text lines
        html: Optional HTML-formatted version of the extracted text
    """
    text: list[str] = Field(..., description='List of extracted text lines')
    html: str | None = Field(None, description='HTML-formatted version of the extracted text')
