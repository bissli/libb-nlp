from pydantic import BaseModel, Field


class SpacyRequest(BaseModel):
    """Request model for spaCy-based text splitting.

    Attributes
        text: The input text to be split into chunks
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
    """
    text: str = Field(..., description='Input text to split into chunks')
    chunk_size: int = Field(4000, description='Maximum size of each chunk in characters')
    chunk_overlap: int = Field(200, description='Number of characters to overlap between chunks')


class SimilarityRequest(BaseModel):
    """Request model for similarity-based text splitting.

    Attributes
        text: The input text to be split using semantic similarity
    """
    text: str = Field(..., description='Input text to split using semantic similarity')


class TextResponse(BaseModel):
    """Response model for text splitting endpoints.

    Attributes
        chunks: List of text chunks after splitting
    """
    chunks: list[str] = Field(..., description='List of text chunks after splitting')
