from pydantic import BaseModel


class ChatMessage(BaseModel):
    content: str


class ProviderDefaults:
    """Provider-specific default parameters"""
    OPENAI = {
        'max_tokens': 8192,
        'temperature': 0.1,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'stop': []
    }

    ANTHROPIC = {
        'max_tokens': 100000,
        'temperature': 0.1,
        'top_p': 1.0,
        'stop': []
    }

    OPENROUTER = {
        'max_tokens': 100000,
        'temperature': 0.1,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'stop': []
    }


class ProviderRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None

    def get_defaults(self) -> dict:
        """Get default parameters based on provider"""
        provider = self.model.split('/')[0]
        match provider:
            case 'openai':
                return ProviderDefaults.OPENAI
            case 'anthropic':
                return ProviderDefaults.ANTHROPIC
            case 'openrouter':
                return ProviderDefaults.OPENROUTER
            case _:
                raise ValueError(f'Unknown provider: {provider}')


class ProviderResponse(BaseModel):
    id: str
    model: str
    choices: list[dict]
    usage: dict[str, int]
    created: int


class ModelInfo(BaseModel):
    name: str
    provider: str
    features: list[str]
