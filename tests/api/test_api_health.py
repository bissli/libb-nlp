"""API endpoint tests for dashboard and health check - require docker container."""
import requests


def test_root_dashboard(docker_container):
    """Test root endpoint returns dashboard with all sections.
    """
    response = requests.get('http://localhost:8000/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'System Dashboard' in response.text
    assert 'System Resources' in response.text
    assert 'Service Status' in response.text
    assert 'GPU Status' in response.text
    assert 'Endpoint Usage' in response.text


def test_health_endpoint_returns_json(docker_container):
    """Test /health endpoint returns simple JSON for load balancer.
    """
    response = requests.get('http://localhost:8000/health')
    assert response.status_code == 200
    assert 'application/json' in response.headers['content-type']
    assert response.json() == {'status': 'ok'}


if __name__ == '__main__':
    __import__('pytest').main([__file__])
