"""Local template rendering tests - no API required."""
import pendulum
import pytest
from lnlp.utils.templates import get_status_class, render_health_report, render_metrics_report


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return {
        'endpoints': [
            {
                'method': 'GET',
                'path': '/api/test',
                'count': 10,
                'avg_time': 0.5,
                'last_called': pendulum.now().timestamp()
            },
            {
                'method': 'POST',
                'path': '/api/create',
                'count': 5,
                'avg_time': 1.2,
                'last_called': 0
            }
        ],
        'system': {
            'uptime': 3600,
            'cpu_usage': [[pendulum.now().timestamp(), 45.0]],
            'memory_usage': [[pendulum.now().timestamp(), 60.0]],
            'gpu_usage': [[pendulum.now().timestamp(), 30.0]]
        }
    }


@pytest.fixture
def sample_health_data():
    """Sample health data for testing."""
    return {
        'status': 'healthy',
        'system': {
            'cpu': {
                'usage_percent': 45.0,
                'healthy': True
            },
            'memory': {
                'usage_percent': 60.0,
                'healthy': True
            },
            'disk': {
                'total': 100.0,
                'used': 50.0,
                'free': 50.0,
                'usage_percent': 50.0,
                'healthy': True
            },
            'gpu': {
                'available': True,
                'driver_info': 'NVIDIA Driver Version: 525.0',
                'memory_used': 1024.0,
                'memory_total': 8192.0
            }
        },
        'services': {
            'splitter_manager': {
                'healthy': True,
                'details': {
                    'spacy': {'loaded': True, 'error': None},
                    'similarity': {'loaded': True, 'gpu_available': True, 'error': None}
                }
            },
            'provider': {
                'healthy': True,
                'details': {
                    'openrouter_configured': True,
                    'error': None
                }
            }
        }
    }


def test_get_status_class_healthy():
    """Test status class for healthy metrics."""
    assert get_status_class(50.0, 80.0) == 'healthy'
    assert get_status_class(0.0, 80.0) == 'healthy'
    assert get_status_class(60.0, 80.0) == 'healthy'


def test_get_status_class_warning():
    """Test status class for warning metrics."""
    assert get_status_class(70.0, 80.0) == 'warning'
    assert get_status_class(64.0, 80.0) == 'warning'


def test_get_status_class_error():
    """Test status class for error metrics."""
    assert get_status_class(80.0, 80.0) == 'error'
    assert get_status_class(90.0, 80.0) == 'error'
    assert get_status_class(100.0, 80.0) == 'error'


def test_render_metrics_report_structure(sample_metrics_data):
    """Test that metrics report has correct HTML structure."""
    html = render_metrics_report(sample_metrics_data)
    
    assert '<html>' in html
    assert '</html>' in html
    assert '<head>' in html
    assert '<body>' in html
    assert 'Application Metrics' in html
    assert 'System Resources' in html
    assert 'Endpoint Usage' in html


def test_render_metrics_report_endpoints(sample_metrics_data):
    """Test that endpoints are rendered correctly."""
    html = render_metrics_report(sample_metrics_data)
    
    assert 'GET /api/test' in html
    assert 'POST /api/create' in html
    assert 'Count: 10' in html
    assert 'Count: 5' in html
    assert 'Avg Time: 0.500s' in html
    assert 'Avg Time: 1.200s' in html


def test_render_metrics_report_never_called(sample_metrics_data):
    """Test that endpoints with last_called=0 show 'Never'."""
    html = render_metrics_report(sample_metrics_data)
    
    assert 'Last Called: Never' in html


def test_render_metrics_report_highcharts(sample_metrics_data):
    """Test that Highcharts is included."""
    html = render_metrics_report(sample_metrics_data)
    
    assert 'highcharts.js' in html
    assert 'Highcharts.chart' in html
    assert 'resourceChart' in html


def test_render_metrics_report_uptime(sample_metrics_data):
    """Test that uptime is displayed."""
    html = render_metrics_report(sample_metrics_data)
    
    assert 'Server Uptime:' in html


def test_render_health_report_structure(sample_health_data):
    """Test that health report has correct HTML structure."""
    html = render_health_report(sample_health_data)
    
    assert '<html>' in html
    assert '</html>' in html
    assert '<head>' in html
    assert '<body>' in html
    assert 'System Health Report' in html
    assert 'System Resources' in html
    assert 'GPU Status' in html
    assert 'Service Status' in html


def test_render_health_report_cpu(sample_health_data):
    """Test CPU metrics rendering."""
    html = render_health_report(sample_health_data)
    
    assert 'CPU Usage' in html
    assert '45.0%' in html
    assert 'healthy' in html


def test_render_health_report_memory(sample_health_data):
    """Test memory metrics rendering."""
    html = render_health_report(sample_health_data)
    
    assert 'Memory Usage' in html
    assert '60.0%' in html


def test_render_health_report_disk(sample_health_data):
    """Test disk metrics rendering."""
    html = render_health_report(sample_health_data)
    
    assert 'Disk Space' in html
    assert '50.0GB / 100.0GB' in html
    assert '50.0%' in html


def test_render_health_report_gpu_available(sample_health_data):
    """Test GPU rendering when available."""
    html = render_health_report(sample_health_data)
    
    assert 'PyTorch CUDA Available' in html
    assert 'NVIDIA Driver' in html
    assert 'GPU Memory Usage' in html
    assert '1024MB / 8192MB' in html


def test_render_health_report_gpu_unavailable():
    """Test GPU rendering when unavailable."""
    health_data = {
        'status': 'healthy',
        'system': {
            'cpu': {'usage_percent': 45.0, 'healthy': True},
            'memory': {'usage_percent': 60.0, 'healthy': True},
            'disk': {'total': 100.0, 'used': 50.0, 'free': 50.0, 'usage_percent': 50.0, 'healthy': True},
            'gpu': {
                'available': False,
                'driver_info': 'nvidia-smi not found'
            }
        },
        'services': {}
    }
    
    html = render_health_report(health_data)
    
    assert 'PyTorch CUDA Available' in html
    assert 'nvidia-smi not found' in html or 'No NVIDIA driver information available' in html


def test_render_health_report_services(sample_health_data):
    """Test service status rendering."""
    html = render_health_report(sample_health_data)
    
    assert 'splitter_manager' in html
    assert 'provider' in html


def test_render_health_report_timestamp(sample_health_data):
    """Test that timestamp is included."""
    html = render_health_report(sample_health_data)
    
    assert 'Generated at' in html


def test_render_health_report_css_classes(sample_health_data):
    """Test that appropriate CSS classes are applied."""
    html = render_health_report(sample_health_data)
    
    # Should have healthy classes for good metrics
    assert 'class="healthy"' in html or 'class=\'healthy\'' in html


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
