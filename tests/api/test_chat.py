"""API endpoint tests for chat completion - require docker container."""
import os

import requests


def verify_chat_response(response_data: dict):
    """Verify the content of the chat completion response"""
    assert 'id' in response_data, 'Missing id field'
    assert 'model' in response_data, 'Missing model field'
    assert 'choices' in response_data, 'Missing choices field'
    assert 'usage' in response_data, 'Missing usage field'
    assert 'created' in response_data, 'Missing created field'

    assert isinstance(response_data['choices'], list), 'Choices should be a list'
    assert len(response_data['choices']) > 0, 'No choices returned'

    assert isinstance(response_data['usage'], dict), 'Usage should be a dict'
    assert 'prompt_tokens' in response_data['usage'], 'Missing prompt_tokens'
    assert 'completion_tokens' in response_data['usage'], 'Missing completion_tokens'
    assert 'total_tokens' in response_data['usage'], 'Missing total_tokens'

    first_choice = response_data['choices'][0]
    assert 'message' in first_choice, 'Missing message in first choice'
    assert 'content' in first_choice['message'], 'Missing content in message'
    assert len(first_choice['message']['content']) > 0, 'Empty content returned'


def test_chat_completion(docker_container, test_data_dir):
    """Test chat completion endpoint with SPOT transcript"""
    with open(os.path.join(test_data_dir, 'transcripts', 'SPOT.html')) as f:
        transcript = f.read()

    request = {
        'model': 'openrouter/openai/gpt-4o-mini',
        'messages': [
            {'content': transcript}
        ],
        'max_tokens': 100000,
    }

    response = requests.post(
        'http://localhost:8000/chat/query',
        json=request
    )

    if response.status_code != 200:
        raise AssertionError(response.__dict__)
    result = response.json()
    verify_chat_response(result)


if __name__ == '__main__':
    __import__('pytest').main([__file__])
