"""Local dashboard service tests - no API required."""
import pytest
import torch
from lnlp.utils.dashboard import DashboardService


@pytest.fixture
def dashboard_service():
    """Create a dashboard service instance."""
    return DashboardService()


def test_check_gpu(dashboard_service):
    """Test GPU status check."""
    gpu_info = dashboard_service.check_gpu()
    
    assert 'available' in gpu_info
    assert 'torch_version' in gpu_info
    assert 'env_vars' in gpu_info
    assert isinstance(gpu_info['available'], bool)
    assert isinstance(gpu_info['torch_version'], str)
    
    if gpu_info['available']:
        assert 'count' in gpu_info
        assert 'current_device' in gpu_info
        assert 'device_name' in gpu_info
        assert 'memory_allocated' in gpu_info


def test_check_system(dashboard_service):
    """Test system resource check."""
    system_info = dashboard_service.check_system()
    
    assert 'cpu' in system_info
    assert 'memory' in system_info
    assert 'disk' in system_info
    assert 'gpu' in system_info
    
    # CPU checks
    assert 'usage_percent' in system_info['cpu']
    assert 'healthy' in system_info['cpu']
    assert isinstance(system_info['cpu']['usage_percent'], float)
    assert isinstance(system_info['cpu']['healthy'], bool)
    assert 0 <= system_info['cpu']['usage_percent'] <= 100
    
    # Memory checks
    assert 'usage_percent' in system_info['memory']
    assert 'healthy' in system_info['memory']
    assert isinstance(system_info['memory']['usage_percent'], float)
    assert isinstance(system_info['memory']['healthy'], bool)
    assert 0 <= system_info['memory']['usage_percent'] <= 100
    
    # Disk checks
    assert 'total' in system_info['disk']
    assert 'used' in system_info['disk']
    assert 'free' in system_info['disk']
    assert 'usage_percent' in system_info['disk']
    assert 'healthy' in system_info['disk']
    assert system_info['disk']['total'] > 0
    assert system_info['disk']['used'] >= 0
    assert system_info['disk']['free'] >= 0
    
    # GPU checks
    assert 'available' in system_info['gpu']
    assert isinstance(system_info['gpu']['available'], bool)


def test_cpu_health_threshold(dashboard_service):
    """Test CPU health threshold logic."""
    system_info = dashboard_service.check_system()
    
    # CPU should be marked unhealthy if usage >= 80%
    if system_info['cpu']['usage_percent'] >= 80:
        assert not system_info['cpu']['healthy']
    else:
        assert system_info['cpu']['healthy']


def test_memory_health_threshold(dashboard_service):
    """Test memory health threshold logic."""
    system_info = dashboard_service.check_system()
    
    # Memory should be marked unhealthy if usage >= 85%
    if system_info['memory']['usage_percent'] >= 85:
        assert not system_info['memory']['healthy']
    else:
        assert system_info['memory']['healthy']


def test_disk_health_threshold(dashboard_service):
    """Test disk health threshold logic."""
    system_info = dashboard_service.check_system()
    
    # Disk should be marked unhealthy if usage >= 85%
    if system_info['disk']['usage_percent'] >= 85:
        assert not system_info['disk']['healthy']
    else:
        assert system_info['disk']['healthy']


def test_gpu_driver_info(dashboard_service):
    """Test GPU driver information."""
    gpu_info = dashboard_service.check_gpu()
    
    if torch.cuda.is_available():
        # If GPU is available, should have driver info
        assert 'driver_info' in gpu_info
    else:
        # If no GPU, driver_info might indicate nvidia-smi not found
        assert 'driver_info' in gpu_info


def test_env_vars_captured(dashboard_service):
    """Test that GPU environment variables are captured."""
    gpu_info = dashboard_service.check_gpu()
    
    assert 'env_vars' in gpu_info
    assert 'CUDA_VISIBLE_DEVICES' in gpu_info['env_vars']
    assert 'CUDA_DEVICE_ORDER' in gpu_info['env_vars']
    assert 'LD_LIBRARY_PATH' in gpu_info['env_vars']


if __name__ == '__main__':
    __import__('pytest').main([__file__, '-v'])
