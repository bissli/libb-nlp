import logging
import os
import shutil
from typing import Any

import psutil
import torch

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for system dashboard with health checks and metrics.
    """

    def check_gpu(self) -> dict:
        """Check GPU status.
        """
        gpu_info = {
            'available': torch.cuda.is_available(),
            'cuda_version': None,
            'torch_version': torch.__version__,
            'env_vars': {
                'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES'),
                'CUDA_DEVICE_ORDER': os.getenv('CUDA_DEVICE_ORDER'),
                'LD_LIBRARY_PATH': os.getenv('LD_LIBRARY_PATH')
            }
        }

        if hasattr(torch, 'version') and hasattr(torch.version, 'cuda'):
            gpu_info['cuda_version'] = torch.version.cuda

        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                text=True,
                check=False,
                env=os.environ
            )
            if result.returncode == 0:
                gpu_info['driver_info'] = result.stdout.strip()
            else:
                gpu_info['driver_info'] = f'nvidia-smi returned error code {result.returncode}'

            if not gpu_info['available'] and gpu_info.get('driver_info'):
                    gpu_info['cuda_built'] = hasattr(torch, 'cuda')

                    import sys
                    cuda_in_path = any('cuda' in p.lower() for p in sys.path)
                    gpu_info['cuda_in_path'] = cuda_in_path

                    try:
                        gpu_info['cuda_import'] = True
                        try:
                            torch.cuda.init()
                            gpu_info['cuda_init'] = True
                        except Exception as e:
                            gpu_info['cuda_init'] = False
                            gpu_info['cuda_init_error'] = str(e)
                    except Exception as e:
                        gpu_info['cuda_import'] = False
                        gpu_info['cuda_import_error'] = str(e)

                    gpu_info['torch_config'] = {
                        'is_cuda_available': torch.cuda.is_available(),
                        'cuda_version': torch.version.cuda if hasattr(torch.version, 'cuda') else None,
                        'cudnn_version': torch.backends.cudnn.version() if hasattr(torch.backends, 'cudnn') else None,
                    }

        except FileNotFoundError:
            gpu_info['driver_info'] = 'nvidia-smi not found'

        if gpu_info['available']:
            try:
                gpu_info.update({
                    'count': torch.cuda.device_count(),
                    'current_device': torch.cuda.current_device(),
                    'device_name': torch.cuda.get_device_name(0),
                    'memory_allocated': torch.cuda.memory_allocated(0) / 1024**2,
                    'memory_reserved': torch.cuda.memory_reserved(0) / 1024**2,
                    'max_memory_allocated': torch.cuda.max_memory_allocated(0) / 1024**2,
                })
            except Exception as e:
                logger.error(f'Error getting detailed GPU info: {e}')
                gpu_info['error'] = str(e)

        logger.info(f'GPU Status: {gpu_info}')
        return gpu_info

    def check_system(self) -> dict:
        """Check system resources.
        """
        try:
            import subprocess
            nvidia_smi = subprocess.run(['nvidia-smi'], capture_output=True, text=True, check=False)
            gpu_info = nvidia_smi.stdout if nvidia_smi.returncode == 0 else 'No GPU detected'
        except FileNotFoundError:
            gpu_info = 'nvidia-smi not found'

        return {
            'cpu': {
                'usage_percent': psutil.cpu_percent(),
                'healthy': psutil.cpu_percent() < 80.0
            },
            'memory': {
                'usage_percent': psutil.virtual_memory().percent,
                'healthy': psutil.virtual_memory().percent < 85.0
            },
            'disk': {
                'total': shutil.disk_usage('/').total / (1024**3),
                'used': shutil.disk_usage('/').used / (1024**3),
                'free': shutil.disk_usage('/').free / (1024**3),
                'usage_percent': (shutil.disk_usage('/').used / shutil.disk_usage('/').total) * 100,
                'healthy': (shutil.disk_usage('/').used / shutil.disk_usage('/').total) < 0.85
            },
            'gpu': {
                'available': torch.cuda.is_available(),
                'driver_info': gpu_info,
                'memory_used': torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0,
                'memory_total': torch.cuda.get_device_properties(0).total_memory / 1024**2 if torch.cuda.is_available() else 0
            }
        }

    def check_services(self, app) -> dict:
        """Check critical service health with detailed diagnostics.
        """
        services_status = {}

        try:
            if hasattr(app.state, 'splitter_manager'):
                splitter_health = app.state.splitter_manager.health_check()
                services_status['splitter_manager'] = {
                    'healthy': all(status['loaded'] for status in splitter_health.values()),
                    'details': {
                        'spacy': {
                            'loaded': splitter_health['spacy']['loaded'],
                            'error': None if splitter_health['spacy']['loaded'] else 'Spacy model not loaded'
                        },
                        'similarity': {
                            'loaded': splitter_health['similarity']['loaded'],
                            'gpu_available': splitter_health['similarity'].get('gpu_available', False),
                            'error': None if splitter_health['similarity']['loaded'] else 'Similarity model not loaded'
                        }
                    }
                }
            else:
                services_status['splitter_manager'] = {
                    'healthy': False,
                    'error': 'Splitter manager not initialized'
                }

            if hasattr(app.state, 'provider'):
                provider = app.state.provider
                if provider is None:
                    services_status['provider'] = {
                        'healthy': False,
                        'error': 'Provider not initialized'
                    }
                else:
                    has_openrouter = bool(provider.openrouter_key)
                    services_status['provider'] = {
                        'healthy': has_openrouter,
                        'details': {
                            'openrouter_configured': has_openrouter,
                            'error': None if has_openrouter else 'OpenRouter API key not configured'
                        }
                    }
            else:
                services_status['provider'] = {
                    'healthy': False,
                    'error': 'Provider service not initialized'
                }

        except Exception as e:
            logger.error(f'Error checking services: {e}')
            services_status['error'] = str(e)

        return services_status

    def get_dashboard_data(self, app) -> dict[str, Any]:
        """Generate comprehensive dashboard data.
        """
        system_status = self.check_system()
        services_status = self.check_services(app)

        return {
            'status': 'healthy' if all(services_status.values()) else 'unhealthy',
            'system': system_status,
            'services': services_status
        }


dashboard_service = DashboardService()
