from datetime import datetime


def render_health_report(health_data: dict) -> str:
    """Render health check data as HTML"""
    return f"""
    <html>
    <head>
        <style>
            :root {{
                --color-bg: #f8fafc;
                --color-card: #ffffff;
                --color-text: #1e293b;
                --color-border: #e2e8f0;
                --color-healthy: #22c55e;
                --color-warning: #f59e0b;
                --color-error: #ef4444;
                --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
                --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            }}
            body {{ 
                font-family: system-ui, -apple-system, sans-serif;
                line-height: 1.5;
                padding: 2rem;
                max-width: 1200px;
                margin: 0 auto;
                background: var(--color-bg);
                color: var(--color-text);
            }}
            h1 {{ 
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 2rem;
                color: var(--color-text);
                text-align: center;
            }}
            h2 {{
                font-size: 1.25rem;
                font-weight: 600;
                margin: 0 0 1rem 0;
                color: var(--color-text);
            }}
            .card {{ 
                background: var(--color-card);
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1.5rem 0;
                box-shadow: var(--shadow-md);
                border: 1px solid var(--color-border);
            }}
            .metric {{ 
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                border-bottom: 1px solid var(--color-border);
                font-size: 0.95rem;
            }}
            .metric:last-child {{ border: none; }}
            .metric span:first-child {{ font-weight: 500; }}
            .healthy {{ 
                color: var(--color-healthy);
                font-weight: 600;
            }}
            .warning {{ 
                color: var(--color-warning);
                font-weight: 600;
            }}
            .error {{ 
                color: var(--color-error);
                font-weight: 600;
            }}
            .gpu-info {{ 
                font-family: ui-monospace, monospace;
                white-space: pre;
                background: var(--color-bg);
                padding: 1rem;
                border-radius: 8px;
                font-size: 0.9rem;
                border: 1px solid var(--color-border);
                margin-top: 0.5rem;
            }}
            .timestamp {{
                text-align: center;
                color: #64748b;
                font-size: 0.9rem;
                margin-top: 2rem;
            }}
            .nested {{
                padding-left: 1.5rem;
                border-left: 2px solid var(--color-border);
                margin: 0.5rem 0 0.5rem 0.5rem;
            }}
        </style>
    </head>
    <body>
        <h1>System Health Report</h1>
        <div class="card">
            <h2>System Resources</h2>
            <div class="metric">
                <span>CPU Usage</span>
                <span class="{get_status_class(health_data['system']['cpu']['usage_percent'], 80)}">
                    {health_data['system']['cpu']['usage_percent']:.1f}%
                </span>
            </div>
            <div class="metric">
                <span>Memory Usage</span>
                <span class="{get_status_class(health_data['system']['memory']['usage_percent'], 85)}">
                    {health_data['system']['memory']['usage_percent']:.1f}%
                </span>
            </div>
            <div class="metric">
                <span>Disk Space</span>
                <span class="{get_status_class(health_data['system']['disk']['usage_percent'], 85)}">
                    {health_data['system']['disk']['used']:.1f}GB / {health_data['system']['disk']['total']:.1f}GB
                    ({health_data['system']['disk']['usage_percent']:.1f}%)
                </span>
            </div>
            {health_data['system']['gpu']['available'] and
             f'''<div class="metric">
                <span>GPU Memory Usage</span>
                <span class="{get_status_class(health_data['system']['gpu']['memory_used'] / health_data['system']['gpu']['memory_total'] * 100, 85)}">
                    {health_data['system']['gpu']['memory_used']:.0f}MB / {health_data['system']['gpu']['memory_total']:.0f}MB
                </span>
            </div>''' or ''}
        </div>

        <div class="card">
            <h2>GPU Status</h2>
            <div class="metric">
                <span>PyTorch CUDA Available</span>
                <span class="{'healthy' if health_data['system']['gpu']['available'] else 'error'}">
                    {health_data['system']['gpu']['available'] and '✓' or '✗'}
                </span>
            </div>
            <div class="metric">
                <span>NVIDIA Driver</span>
                <span class="{'healthy' if health_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in health_data['system']['gpu']['driver_info'] else 'error'}">
                    {health_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in health_data['system']['gpu']['driver_info'] and '✓' or '✗'}
                </span>
            </div>
            {health_data['system']['gpu'].get('driver_info') and
             f'<div class="gpu-info">{health_data["system"]["gpu"]["driver_info"]}</div>' or
             '<div class="metric error">No NVIDIA driver information available</div>'}
            {not health_data['system']['gpu']['available'] and health_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in health_data['system']['gpu']['driver_info'] and
             f'''<div class="metric warning">
                    <span>GPU detected but PyTorch cannot access it</span>
                </div>
                <div class="gpu-info">
                    CUDA Version (PyTorch): {health_data['system']['gpu'].get('cuda_version', 'Not found')}
                    PyTorch Version: {health_data['system']['gpu'].get('torch_version', 'Not found')}
                    NVCC Version: {health_data['system']['gpu'].get('nvcc_version', 'Not found')}
                    CUDA Libraries: {'Found' if health_data['system']['gpu'].get('cuda_lib_exists') else 'Not found'}
                    
                    Environment Variables:
                    CUDA_VISIBLE_DEVICES: {health_data['system']['gpu'].get('env_vars', {}).get('CUDA_VISIBLE_DEVICES') or 'Not set'}
                    CUDA_DEVICE_ORDER: {health_data['system']['gpu'].get('env_vars', {}).get('CUDA_DEVICE_ORDER') or 'Not set'}
                    LD_LIBRARY_PATH: {health_data['system']['gpu'].get('env_vars', {}).get('LD_LIBRARY_PATH') or 'Not set'}
                    
                    CUDA Init Error: {health_data['system']['gpu'].get('cuda_init_error', 'No error information')}
                </div>''' or ''}
        </div>

        <div class="card">
            <h2>Service Status</h2>
            {render_services(health_data['services'])}
        </div>

        <div class="timestamp">
            Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </body>
    </html>
    """


def get_status_class(value: float, threshold: float) -> str:
    """Get CSS class based on metric value"""
    if value >= threshold:
        return 'error'
    elif value >= threshold * 0.8:
        return 'warning'
    return 'healthy'


def render_services(services: dict) -> str:
    """Render service status section with detailed diagnostics"""
    html = []

    for service, info in services.items():
        if service == 'error':
            html.append(f"""
                <div class="metric error">
                    <span>Service Check Error</span>
                    <span>{info}</span>
                </div>
            """)
            continue

        status = info.get('healthy', False)
        status_class = 'healthy' if status else 'error'

        # Main service status
        html.append(f"""
            <div class="metric">
                <span>{service}</span>
                <span class="{status_class}">{'✓' if status else '✗'}</span>
            </div>
        """)

        # Show error if present
        if 'error' in info and info['error']:
            html.append(f"""
                <div class="metric error" style="padding-left: 2rem;">
                    <span>Error</span>
                    <span>{info['error']}</span>
                </div>
            """)

        # Show detailed status for each service
        if 'details' in info:
            for component, details in info['details'].items():
                if isinstance(details, dict):
                    # For complex component status (like models)
                    for key, value in details.items():
                        if key != 'error' or value is not None:
                            status_class = 'healthy' if value else 'warning'
                            html.append(f"""
                                <div class="metric" style="padding-left: 2rem;">
                                    <span>{component} - {key}</span>
                                    <span class="{status_class}">{value}</span>
                                </div>
                            """)
                else:
                    # For simple component status
                    status_class = 'healthy' if details else 'warning'
                    html.append(f"""
                        <div class="metric" style="padding-left: 2rem;">
                            <span>{component}</span>
                            <span class="{status_class}">{details}</span>
                        </div>
                    """)

    return '\n'.join(html)
