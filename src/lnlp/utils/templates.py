import pendulum


def render_dashboard(dashboard_data: dict, metrics_data: dict) -> str:
    """Render unified dashboard with system health and metrics as HTML.
    """
    endpoints_html = []
    for endpoint in metrics_data['endpoints']:
        last_called = pendulum.from_timestamp(endpoint['last_called']).in_timezone(pendulum.now().timezone).format('YYYY-MM-DD HH:mm:ss z') if endpoint['last_called'] > 0 else 'Never'
        endpoints_html.append(f"""
            <div class="metric">
                <span>{endpoint['method']} {endpoint['path']}</span>
                <div class="metric-details">
                    <span>Count: {endpoint['count']}</span>
                    <span>Avg Time: {endpoint['avg_time']:.3f}s</span>
                    <span>Last Called: {last_called}</span>
                </div>
            </div>
        """)

    cpu_data = [[int(t * 1000), v] for t, v in metrics_data['system']['cpu_usage']]
    memory_data = [[int(t * 1000), v] for t, v in metrics_data['system']['memory_usage']]
    gpu_data = [[int(t * 1000), v] for t, v in metrics_data['system']['gpu_usage']] if metrics_data['system']['gpu_usage'] else None

    return f"""
    <html>
    <head>
        <script src="https://code.highcharts.com/highcharts.js"></script>
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
                max-width: 1400px;
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
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 1.5rem;
            }}
            .metric {{
                padding: 0.75rem;
                border-bottom: 1px solid var(--color-border);
                font-size: 0.95rem;
            }}
            .metric:last-child {{ border: none; }}
            .metric span:first-child {{ font-weight: 500; }}
            .metric-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .metric-details {{
                display: flex;
                gap: 1rem;
                margin-top: 0.5rem;
                color: #64748b;
                font-size: 0.9rem;
            }}
            .chart {{
                min-height: 300px;
                margin: 1rem 0;
            }}
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
                white-space: pre-wrap;
                word-wrap: break-word;
                background: var(--color-bg);
                padding: 1rem;
                border-radius: 8px;
                font-size: 0.9rem;
                border: 1px solid var(--color-border);
                margin-top: 0.5rem;
                max-height: 500px;
                overflow-y: auto;
            }}
            .footer {{
                text-align: center;
                color: #64748b;
                font-size: 0.9rem;
                margin-top: 2rem;
                padding-top: 1rem;
                border-top: 1px solid var(--color-border);
            }}
            .tabs {{
                display: flex;
                gap: 0.5rem;
                border-bottom: 2px solid var(--color-border);
                margin-bottom: 1.5rem;
            }}
            .tab {{
                padding: 0.75rem 1.5rem;
                background: transparent;
                border: none;
                border-bottom: 3px solid transparent;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 500;
                color: #64748b;
                transition: all 0.2s;
            }}
            .tab:hover {{
                color: var(--color-text);
                background: var(--color-bg);
            }}
            .tab.active {{
                color: #3b82f6;
                border-bottom-color: #3b82f6;
            }}
            .tab-content {{
                display: none;
            }}
            .tab-content.active {{
                display: block;
            }}
        </style>
    </head>
    <body>
        <h1>System Dashboard</h1>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('overview')">Overview</button>
            <button class="tab" onclick="switchTab('services')">Services</button>
            <button class="tab" onclick="switchTab('gpu')">GPU Details</button>
            <button class="tab" onclick="switchTab('endpoints')">Endpoints</button>
        </div>

        <div id="overview" class="tab-content active">
            <div class="card">
                <h2>System Resources</h2>
            <div class="metric metric-row">
                <span>CPU Usage</span>
                <span class="{get_status_class(dashboard_data['system']['cpu']['usage_percent'], 80)}">
                    {dashboard_data['system']['cpu']['usage_percent']:.1f}%
                </span>
            </div>
            <div class="metric metric-row">
                <span>Memory Usage</span>
                <span class="{get_status_class(dashboard_data['system']['memory']['usage_percent'], 85)}">
                    {dashboard_data['system']['memory']['usage_percent']:.1f}%
                </span>
            </div>
            <div class="metric metric-row">
                <span>Disk Space</span>
                <span class="{get_status_class(dashboard_data['system']['disk']['usage_percent'], 85)}">
                    {dashboard_data['system']['disk']['used']:.1f}GB / {dashboard_data['system']['disk']['total']:.1f}GB
                    ({dashboard_data['system']['disk']['usage_percent']:.1f}%)
                </span>
            </div>
            {dashboard_data['system']['gpu']['available'] and
             f'''<div class="metric metric-row">
                <span>GPU Memory Usage</span>
                <span class="{get_status_class(dashboard_data['system']['gpu']['memory_used'] / dashboard_data['system']['gpu']['memory_total'] * 100, 85)}">
                    {dashboard_data['system']['gpu']['memory_used']:.0f}MB / {dashboard_data['system']['gpu']['memory_total']:.0f}MB
                </span>
            </div>''' or ''}
                <div id="resourceChart" class="chart"></div>
            </div>

            <div class="card">
                <h2>Quick Status</h2>
                <div class="grid">
                    <div>
                        <h3 style="margin-top: 0; font-size: 1rem; color: #64748b;">Services</h3>
                        {render_services_summary(dashboard_data['services'])}
                    </div>
                    <div>
                        <h3 style="margin-top: 0; font-size: 1rem; color: #64748b;">GPU</h3>
                        <div class="metric metric-row">
                            <span>CUDA Available</span>
                            <span class="{'healthy' if dashboard_data['system']['gpu']['available'] else 'error'}">
                                {dashboard_data['system']['gpu']['available'] and '✓' or '✗'}
                            </span>
                        </div>
                        <div class="metric metric-row">
                            <span>Driver</span>
                            <span class="{'healthy' if dashboard_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in dashboard_data['system']['gpu']['driver_info'] else 'error'}">
                                {dashboard_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in dashboard_data['system']['gpu']['driver_info'] and '✓' or '✗'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="services" class="tab-content">
            <div class="card">
                <h2>Service Status</h2>
                {render_services(dashboard_data['services'])}
            </div>
        </div>

        <div id="gpu" class="tab-content">
            <div class="card">
                <h2>GPU Diagnostics</h2>
                <div class="metric metric-row">
                    <span>PyTorch CUDA Available</span>
                    <span class="{'healthy' if dashboard_data['system']['gpu']['available'] else 'error'}">
                        {dashboard_data['system']['gpu']['available'] and '✓' or '✗'}
                    </span>
                </div>
                <div class="metric metric-row">
                    <span>NVIDIA Driver</span>
                    <span class="{'healthy' if dashboard_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in dashboard_data['system']['gpu']['driver_info'] else 'error'}">
                        {dashboard_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in dashboard_data['system']['gpu']['driver_info'] and '✓' or '✗'}
                    </span>
                </div>
                {dashboard_data['system']['gpu'].get('driver_info') and
                 f'<div class="gpu-info">{dashboard_data["system"]["gpu"]["driver_info"]}</div>' or
                 '<div class="metric error">No NVIDIA driver information available</div>'}
                {not dashboard_data['system']['gpu']['available'] and dashboard_data['system']['gpu'].get('driver_info') and 'nvidia-smi not found' not in dashboard_data['system']['gpu']['driver_info'] and
                 f'''<div class="metric warning">
                        <span>GPU detected but PyTorch cannot access it</span>
                    </div>
                    <div class="gpu-info">
                        CUDA Version (PyTorch): {dashboard_data['system']['gpu'].get('cuda_version', 'Not found')}
                        PyTorch Version: {dashboard_data['system']['gpu'].get('torch_version', 'Not found')}
                        NVCC Version: {dashboard_data['system']['gpu'].get('nvcc_version', 'Not found')}
                        CUDA Libraries: {'Found' if dashboard_data['system']['gpu'].get('cuda_lib_exists') else 'Not found'}

                        Environment Variables:
                        CUDA_VISIBLE_DEVICES: {dashboard_data['system']['gpu'].get('env_vars', {}).get('CUDA_VISIBLE_DEVICES') or 'Not set'}
                        CUDA_DEVICE_ORDER: {dashboard_data['system']['gpu'].get('env_vars', {}).get('CUDA_DEVICE_ORDER') or 'Not set'}
                        LD_LIBRARY_PATH: {dashboard_data['system']['gpu'].get('env_vars', {}).get('LD_LIBRARY_PATH') or 'Not set'}

                        CUDA Init Error: {dashboard_data['system']['gpu'].get('cuda_init_error', 'No error information')}
                    </div>''' or ''}
            </div>
        </div>

        <div id="endpoints" class="tab-content">
            <div class="card">
                <h2>Endpoint Usage</h2>
                {''.join(endpoints_html) if endpoints_html else '<div class="metric">No endpoints called yet</div>'}
            </div>
        </div>

        <div class="footer">
            Uptime: {str(pendulum.duration(seconds=metrics_data['system']['uptime']).in_words())} |
            Generated at {pendulum.now().in_timezone(pendulum.now().timezone).format('YYYY-MM-DD HH:mm:ss z')}
        </div>

        <script>
            function switchTab(tabName) {{
                const tabs = document.querySelectorAll('.tab');
                const contents = document.querySelectorAll('.tab-content');
                
                tabs.forEach(tab => tab.classList.remove('active'));
                contents.forEach(content => content.classList.remove('active'));
                
                event.target.classList.add('active');
                document.getElementById(tabName).classList.add('active');
            }}

            Highcharts.chart('resourceChart', {{
                chart: {{
                    type: 'line',
                    zoomType: 'x'
                }},
                time: {{
                    timezone: '{pendulum.now().timezone_name}'
                }},
                title: {{ text: 'Resource Usage Over Time' }},
                legend: {{
                    align: 'center',
                    verticalAlign: 'top',
                    layout: 'horizontal',
                    margin: 5,
                    padding: 5
                }},
                xAxis: {{
                    type: 'datetime',
                    title: {{ text: 'Time' }},
                    labels: {{
                        format: '{{value:%H:%M:%S}}',
                        rotation: -45,
                        align: 'right'
                    }},
                    tickInterval: 10 * 1000,
                    useUTC: false
                }},
                yAxis: {{
                    title: {{ text: 'Usage %' }},
                    min: 0,
                    max: 100
                }},
                tooltip: {{
                    shared: true,
                    crosshairs: true
                }},
                series: [
                    {{
                        name: 'CPU',
                        data: {cpu_data},
                        color: '#3b82f6'
                    }},
                    {{
                        name: 'Memory',
                        data: {memory_data},
                        color: '#10b981'
                    }},
                    {f'''{{
                        name: 'GPU',
                        data: {gpu_data},
                        color: '#6366f1'
                    }},''' if gpu_data else ''}
                ]
            }});
        </script>
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


def render_services_summary(services: dict) -> str:
    """Render quick service status summary"""
    html = []
    for service, info in services.items():
        if service == 'error':
            continue
        status = info.get('healthy', False)
        status_class = 'healthy' if status else 'error'
        html.append(f"""
            <div class="metric metric-row">
                <span>{service}</span>
                <span class="{status_class}">{'✓' if status else '✗'}</span>
            </div>
        """)
    return '\n'.join(html)


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
