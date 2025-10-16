from collections import deque
from dataclasses import dataclass
from threading import Lock

import pendulum
import psutil
import torch


@dataclass
class EndpointMetric:
    path: str
    method: str
    count: int = 0
    total_time: float = 0.0
    last_called: float = 0.0

    @property
    def avg_time(self) -> float:
        return self.total_time / self.count if self.count > 0 else 0


class MetricsService:
    """Service for tracking application metrics"""

    def __init__(self, max_history: int = 300):  # 5 minutes at 1s intervals
        self._endpoints = {}
        self._lock = Lock()
        self._max_history = max_history

        # Time series data stored as deques
        self._cpu_usage = deque(maxlen=max_history)
        self._memory_usage = deque(maxlen=max_history)
        self._gpu_usage = deque(maxlen=max_history) if torch.cuda.is_available() else None

        # Start time for uptime calculation
        self._start_time = pendulum.now().timestamp()

        # Initialize with first datapoint
        self._record_system_metrics()

    def track_request(self, path: str, method: str, duration: float):
        """Track an endpoint request"""
        with self._lock:
            key = (path, method)
            if key not in self._endpoints:
                self._endpoints[key] = EndpointMetric(path, method)

            metric = self._endpoints[key]
            metric.count += 1
            metric.total_time += duration
            metric.last_called = pendulum.now().in_timezone('local').timestamp()

    def _record_system_metrics(self):
        """Record current system metrics"""
        # Get local timestamp
        timestamp = pendulum.now().in_timezone('local').timestamp()

        # CPU and Memory
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        self._cpu_usage.append((timestamp, cpu_percent))
        self._memory_usage.append((timestamp, memory.percent))

        # GPU if available
        if self._gpu_usage is not None:
            gpu_percent = torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory * 100
            self._gpu_usage.append((timestamp, gpu_percent))

    def get_metrics(self) -> dict:
        """Get current metrics data"""
        with self._lock:
            # Record latest metrics
            self._record_system_metrics()

            # Calculate uptime
            uptime = pendulum.now().in_timezone('local').timestamp() - self._start_time

            return {
                'system': {
                    'uptime': uptime,
                    'uptime_formatted': str(pendulum.from_timestamp(uptime) - pendulum.from_timestamp(0)),
                    'cpu_usage': list(self._cpu_usage),
                    'memory_usage': list(self._memory_usage),
                    'gpu_usage': list(self._gpu_usage) if self._gpu_usage else None
                },
                'endpoints': [
                    {
                        'path': metric.path,
                        'method': metric.method,
                        'count': metric.count,
                        'avg_time': metric.avg_time,
                        'total_time': metric.total_time,
                        'last_called': metric.last_called
                    }
                    for metric in sorted(
                        self._endpoints.values(),
                        key=lambda x: x.count,
                        reverse=True
                    )
                ]
            }


# Singleton instance
metrics_service = MetricsService()
