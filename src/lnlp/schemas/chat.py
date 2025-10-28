from typing import Any

from pydantic import BaseModel


class ChatMessage(BaseModel):
    content: str


class ProviderRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None


class UsageInfo(BaseModel):
    """Model for the detailed usage information returned by the provider."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: dict[str, Any] | None = None
    completion_tokens_details: dict[str, Any] | None = None


class ProviderResponse(BaseModel):
    id: str
    model: str
    choices: list[dict]
    usage: UsageInfo
    created: int


class ModelInfo(BaseModel):
    name: str
    provider: str
    context_length: int | None = None
    features: list[str]
