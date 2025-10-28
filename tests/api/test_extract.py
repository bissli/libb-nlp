"""API endpoint tests for extraction - require docker container."""
import os

import requests


def verify_pdf_content(html_content: str):
    """Verify the content of the SPOT earnings call PDF"""
    assert len(html_content) > 10000, 'Content suspiciously short'

    sections = [
        'Spotify Technology SA (SPOT US Equity) Q4',
        '>Company Participants</h4>',
        '>Presentation</h4>',
        '>Questions And Answers</h4>'
    ]

    last_pos = -1
    for section in sections:
        pos = html_content.find(section)
        assert pos != -1, f'Section "{section}" not found'
        assert pos > last_pos, f'Section "{section}" out of order'
        last_pos = pos

    participants = [
        'Alex Norstrom , Co-President, Chief Business Officer',
        'Bryan Goldberg , Head of Investor Relations',
        'Christian Luiga, Chief Financial Officer',
        'Daniel Ek , Founder, Chief Executive Officer and Chairman',
        'Gustav Soderstrom , Co-President, Chief Product and Technology Officer'
    ]

    for participant in participants:
        assert participant in html_content, f'Participant not found: {participant}'

    header = 'Spotify Technology SA (SPOT US Equity) Q4 2024 Earnings Call'
    conclusion = "This concludes Spotify's Fourth Quarter 2024 Earnings Call and Webcast"

    assert header in html_content, 'Document header not found'
    assert conclusion in html_content, 'Document conclusion not found'

    assert 'Operator' in html_content, 'Missing Operator section'
    assert 'Questions And Answers' in html_content, 'Missing Q&A section'

    key_topics = [
        'earnings',
        'revenue',
        'growth',
        'subscribers',
        'premium',
        'margin'
    ]

    for topic in key_topics:
        assert topic.lower() in html_content.lower(), f'Missing key topic: {topic}'


def test_pdf_extraction_api(docker_container, test_data_dir):
    """Test PDF extraction endpoint with SPOT earnings transcript"""
    pdf_path = os.path.join(test_data_dir, 'transcripts', 'SPOT.pdf')

    with open(pdf_path, 'rb') as pdf_file:
        files = {'file': ('SPOT.pdf', pdf_file, 'application/pdf')}
        response = requests.post(
            'http://localhost:8000/extract/pdf',
            files=files,
            params={'include_page_numbers': False}
        )

    assert response.status_code == 200
    result = response.json()

    assert 'text' in result
    assert 'html' in result
    assert isinstance(result['text'], list)
    assert isinstance(result['html'], str)
    assert len(result['text']) > 0
    assert len(result['html']) > 0

    verify_pdf_content(result['html'])


if __name__ == '__main__':
    __import__('pytest').main([__file__])
