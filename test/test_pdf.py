import os

import requests
from lnlp.loaders.pdf import PDFTextExtractor


def verify_pdf_content(html_content: str):
    """Verify the content of the SPOT earnings call PDF"""
    # Test content length
    assert len(html_content) > 10000, 'Content suspiciously short'

    # Test major document sections exist and are in correct order
    sections = [
        'Spotify Technology SA (SPOT US Equity) Q4',  # Header section
        '>Company Participants</h4>',  # Company Participants section
        '>Presentation</h4>',  # Presentation section
        '>Questions And Answers</h4>'  # Q&A section
    ]

    # Check sections appear in correct order
    last_pos = -1
    for section in sections:
        pos = html_content.find(section)
        assert pos != -1, f'Section "{section}" not found'
        assert pos > last_pos, f'Section "{section}" out of order'
        last_pos = pos

    # Test all participants are listed
    participants = [
        'Alex Norstrom , Co-President, Chief Business Officer',
        'Bryan Goldberg , Head of Investor Relations',
        'Christian Luiga, Chief Financial Officer',
        'Daniel Ek , Founder, Chief Executive Officer and Chairman',
        'Gustav Soderstrom , Co-President, Chief Product and Technology Officer'
    ]

    for participant in participants:
        assert participant in html_content, f'Participant not found: {participant}'

    # Test document beginning and end
    header = 'Spotify Technology SA (SPOT US Equity) Q4 2024 Earnings Call'
    conclusion = "This concludes Spotify's Fourth Quarter 2024 Earnings Call and Webcast"

    assert header in html_content, 'Document header not found'
    assert conclusion in html_content, 'Document conclusion not found'

    # Verify key structural elements
    assert 'Operator' in html_content, 'Missing Operator section'
    assert 'Questions And Answers' in html_content, 'Missing Q&A section'

    # Test for presence of key discussion topics
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
    pdf_path = os.path.join(test_data_dir, 'SPOT.pdf')

    with open(pdf_path, 'rb') as pdf_file:
        files = {'file': ('SPOT.pdf', pdf_file, 'application/pdf')}
        response = requests.post(
            'http://localhost:8000/extract/pdf',
            files=files,
            params={'include_page_numbers': False}
        )

    assert response.status_code == 200
    result = response.json()

    # Test response structure
    assert 'text' in result
    assert 'html' in result
    assert isinstance(result['text'], list)
    assert isinstance(result['html'], str)
    assert len(result['text']) > 0
    assert len(result['html']) > 0

    # Verify PDF content
    verify_pdf_content(result['html'])


def test_pdf_extraction_local(test_data_dir):
    """Test PDF text extraction for SPOT earnings transcript"""
    pdf_path = os.path.join(test_data_dir, 'SPOT.pdf')
    extractor = PDFTextExtractor(pdf_path)
    extracted_html = extractor.extract_html()

    # Verify PDF content
    verify_pdf_content(extracted_html)


if __name__ == '__main__':
    __import__('pytest').main([__file__])
