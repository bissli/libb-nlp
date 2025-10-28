"""Local metrics service tests - no API required."""
import time

import pytest
from lnlp.utils.metrics import EndpointMetric, MetricsService


def test_endpoint_metric_initialization():
    """Test EndpointMetric initialization and properties."""
    metric = EndpointMetric(path='/test', method='GET')
    
    assert metric.path == '/test'
    assert metric.method == 'GET'
    assert metric.count == 0
    assert metric.total_time == 0.0
    assert metric.last_called == 0.0
    assert metric.avg_time == 0


def test_endpoint_metric_avg_time():
    """Test average time calculation."""
    metric = EndpointMetric(path='/test', method='GET', count=3, total_time=6.0)
    assert metric.avg_time == 2.0
    
    metric_zero = EndpointMetric(path='/test', method='GET', count=0, total_time=0.0)
    assert metric_zero.avg_time == 0


def test_metrics_service_initialization():
    """Test MetricsService initialization."""
    service = MetricsService(max_history=10)
    
    assert service._max_history == 10
    assert len(service._endpoints) == 0
    assert len(service._cpu_usage) > 0  # Should have initial datapoint
    assert len(service._memory_usage) > 0


def test_track_request():
    """Test tracking endpoint requests."""
    service = MetricsService()
    
    service.track_request('/api/test', 'GET', 0.5)
    service.track_request('/api/test', 'GET', 1.5)
    service.track_request('/api/other', 'POST', 0.3)
    
    metrics = service.get_metrics()
    endpoints = metrics['endpoints']
    
    assert len(endpoints) == 2
    
    # Find the /api/test endpoint
    test_endpoint = next(e for e in endpoints if e['path'] == '/api/test')
    assert test_endpoint['count'] == 2
    assert test_endpoint['total_time'] == 2.0
    assert test_endpoint['avg_time'] == 1.0
    assert test_endpoint['method'] == 'GET'


def test_system_metrics_recorded():
    """Test that system metrics are recorded."""
    service = MetricsService(max_history=5)
    
    # Wait a bit and record more metrics
    time.sleep(0.1)
    metrics = service.get_metrics()
    
    assert 'system' in metrics
    assert 'cpu_usage' in metrics['system']
    assert 'memory_usage' in metrics['system']
    assert 'uptime' in metrics['system']
    
    assert len(metrics['system']['cpu_usage']) > 0
    assert len(metrics['system']['memory_usage']) > 0
    
    # Check that values are tuples of (timestamp, value)
    cpu_sample = metrics['system']['cpu_usage'][0]
    assert len(cpu_sample) == 2
    assert isinstance(cpu_sample[0], float)  # timestamp
    assert isinstance(cpu_sample[1], float)  # cpu percent


def test_max_history_limit():
    """Test that metrics history respects max_history limit."""
    service = MetricsService(max_history=3)
    
    # Record multiple metrics to exceed max_history
    for _ in range(5):
        service._record_system_metrics()
    
    metrics = service.get_metrics()
    
    # Should not exceed max_history + 1 (the extra one from get_metrics call)
    assert len(metrics['system']['cpu_usage']) <= 4
    assert len(metrics['system']['memory_usage']) <= 4


def test_endpoint_sorting():
    """Test that endpoints are sorted by count."""
    service = MetricsService()
    
    service.track_request('/low', 'GET', 0.1)
    service.track_request('/medium', 'POST', 0.1)
    service.track_request('/medium', 'POST', 0.1)
    service.track_request('/high', 'GET', 0.1)
    service.track_request('/high', 'GET', 0.1)
    service.track_request('/high', 'GET', 0.1)
    
    metrics = service.get_metrics()
    endpoints = metrics['endpoints']
    
    # Should be sorted by count descending
    assert endpoints[0]['path'] == '/high'
    assert endpoints[0]['count'] == 3
    assert endpoints[1]['path'] == '/medium'
    assert endpoints[1]['count'] == 2
    assert endpoints[2]['path'] == '/low'
    assert endpoints[2]['count'] == 1


def test_uptime_calculation():
    """Test uptime calculation."""
    service = MetricsService()
    time.sleep(0.1)
    
    metrics = service.get_metrics()
    
    assert metrics['system']['uptime'] > 0
    assert metrics['system']['uptime'] < 1.0  # Should be less than 1 second


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
