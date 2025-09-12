"""
GitOps Monitoring Dashboard

Provides real-time monitoring and analytics for GitOps operations,
including Git events, webhooks, workflows, and system health metrics.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from aiohttp import web, WSMsgType
from aiohttp.web import Request, Response, WebSocketResponse
import weakref

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class Metric:
    """Represents a metric"""
    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class DashboardData:
    """Dashboard data container"""
    git_events: List[Dict[str, Any]] = field(default_factory=list)
    webhook_events: List[Dict[str, Any]] = field(default_factory=list)
    workflow_executions: List[Dict[str, Any]] = field(default_factory=list)
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    repository_status: Dict[str, Any] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DashboardMetricsCollector:
    """Collects metrics for the dashboard"""
    
    def __init__(self, redis_client=None, git_event_detector=None, webhook_handler=None, workflow_engine=None):
        """Initialize metrics collector"""
        self.redis_client = redis_client
        self.git_event_detector = git_event_detector
        self.webhook_handler = webhook_handler
        self.workflow_engine = workflow_engine
        self.logger = logging.getLogger(__name__)
        self.metrics_cache = {}
        self.last_update = datetime.utcnow()
    
    async def collect_git_events_metrics(self) -> Dict[str, Any]:
        """Collect Git events metrics"""
        try:
            metrics = {
                'total_events': 0,
                'events_by_type': {},
                'events_by_repository': {},
                'recent_events': [],
                'event_rate': 0.0
            }
            
            if self.git_event_detector:
                # Get status from git event detector
                status = self.git_event_detector.get_monitoring_status()
                
                # Check if any repositories are being monitored (even if by another process)
                monitored_repos = status.get('monitored_repositories', 0)
                
                # Also check Redis for recent events to determine if monitoring is active
                monitoring_active = status.get('running', False)
                if not monitoring_active and self.redis_client and monitored_repos > 0:
                    # If local detector isn't running but repos are configured,
                    # check for recent events in Redis to see if another process is monitoring
                    try:
                        for repo_info in status.get('repositories', []):
                            repo_path = repo_info.get('path', '')
                            if repo_path:
                                list_key = f"git_events:list:{repo_path}"
                                # Check if there are any events in Redis
                                if hasattr(self.redis_client, 'lrange'):
                                    events = await self.redis_client.lrange(list_key, 0, 0)
                                    if events:
                                        monitoring_active = True  # Events exist, so something is monitoring
                                        break
                    except:
                        pass  # Ignore errors in detection
                
                metrics.update({
                    'monitoring_active': monitoring_active,
                    'monitored_repositories': monitored_repos,
                    'repositories': status.get('repositories', [])
                })
                
                # Get recent events
                if self.redis_client:
                    recent_events = await self.git_event_detector.get_recent_events(limit=50)
                    
                    # If we have recent events (within last 5 minutes), monitoring is likely active
                    if recent_events and not monitoring_active:
                        latest_event_time = recent_events[0].timestamp
                        time_since_last = (datetime.utcnow() - latest_event_time).total_seconds()
                        if time_since_last < 300:  # 5 minutes
                            monitoring_active = True
                            metrics['monitoring_active'] = True
                    metrics['recent_events'] = [
                        {
                            'event_type': event.event_type.value,
                            'repository': event.repository_path,
                            'branch': event.branch,
                            'author': event.author,
                            'timestamp': event.timestamp.isoformat(),
                            'files_changed': len(event.files_changed)
                        }
                        for event in recent_events
                    ]
                    
                    # Calculate metrics
                    metrics['total_events'] = len(recent_events)
                    
                    # Events by type
                    for event in recent_events:
                        event_type = event.event_type.value
                        metrics['events_by_type'][event_type] = metrics['events_by_type'].get(event_type, 0) + 1
                    
                    # Events by repository
                    for event in recent_events:
                        repo = event.repository_path
                        metrics['events_by_repository'][repo] = metrics['events_by_repository'].get(repo, 0) + 1
                    
                    # Calculate event rate (events per hour)
                    if recent_events:
                        time_span = (datetime.utcnow() - recent_events[-1].timestamp).total_seconds() / 3600
                        if time_span > 0:
                            metrics['event_rate'] = len(recent_events) / time_span
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting Git events metrics: {e}")
            return {'error': str(e)}
    
    async def collect_webhook_metrics(self) -> Dict[str, Any]:
        """Collect webhook metrics"""
        try:
            metrics = {
                'total_webhooks': 0,
                'webhooks_by_source': {},
                'webhooks_by_type': {},
                'recent_webhooks': [],
                'webhook_rate': 0.0,
                'configured_endpoints': 0
            }
            
            if self.webhook_handler:
                # Get webhook statistics
                stats = await self.webhook_handler.get_webhook_statistics()
                metrics.update({
                    'configured_endpoints': stats.get('configured_endpoints', 0),
                    'endpoints': stats.get('endpoints', {}),
                    'handlers_registered': stats.get('handlers_registered', {})
                })
                
                # Get recent webhook events
                recent_webhooks = await self.webhook_handler.get_recent_webhook_events(limit=50)
                metrics['recent_webhooks'] = recent_webhooks
                metrics['total_webhooks'] = len(recent_webhooks)
                
                # Webhooks by source
                for webhook in recent_webhooks:
                    source = webhook.get('source', 'unknown')
                    metrics['webhooks_by_source'][source] = metrics['webhooks_by_source'].get(source, 0) + 1
                
                # Webhooks by type
                for webhook in recent_webhooks:
                    event_type = webhook.get('event_type', 'unknown')
                    metrics['webhooks_by_type'][event_type] = metrics['webhooks_by_type'].get(event_type, 0) + 1
                
                # Calculate webhook rate
                if recent_webhooks:
                    # Assume timestamps are ISO format strings
                    try:
                        latest_time = datetime.fromisoformat(recent_webhooks[0]['timestamp'])
                        oldest_time = datetime.fromisoformat(recent_webhooks[-1]['timestamp'])
                        time_span = (latest_time - oldest_time).total_seconds() / 3600
                        if time_span > 0:
                            metrics['webhook_rate'] = len(recent_webhooks) / time_span
                    except:
                        pass
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting webhook metrics: {e}")
            return {'error': str(e)}
    
    async def collect_workflow_metrics(self) -> Dict[str, Any]:
        """Collect workflow execution metrics"""
        try:
            metrics = {
                'total_workflows': 0,
                'active_workflows': 0,
                'workflow_success_rate': 0.0,
                'average_execution_time': 0.0,
                'recent_executions': []
            }
            
            if self.workflow_engine:
                # Get workflow performance metrics
                perf_metrics = self.workflow_engine.get_performance_metrics()
                metrics.update({
                    'total_workflows': perf_metrics.get('total_workflows_executed', 0),
                    'successful_workflows': perf_metrics.get('successful_workflows', 0),
                    'failed_workflows': perf_metrics.get('failed_workflows', 0),
                    'success_rate': perf_metrics.get('success_rate', 0.0),
                    'average_execution_time': perf_metrics.get('average_execution_time', 0.0),
                    'active_workflows': perf_metrics.get('active_workflows', 0),
                    'resource_utilization': perf_metrics.get('resource_utilization', {}),
                    'failure_statistics': perf_metrics.get('failure_statistics', {})
                })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting workflow metrics: {e}")
            return {'error': str(e)}
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        try:
            import psutil
            import sys
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                'system_health': {
                    'cpu_usage_percent': cpu_percent,
                    'memory_usage_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_usage_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024**3)
                },
                'application_info': {
                    'python_version': sys.version,
                    'uptime_seconds': (datetime.utcnow() - self.last_update).total_seconds(),
                    'process_id': psutil.Process().pid
                },
                'redis_status': {'connected': False},
                'component_status': {
                    'git_event_detector': self.git_event_detector is not None,
                    'webhook_handler': self.webhook_handler is not None,
                    'workflow_engine': self.workflow_engine is not None
                }
            }
            
            # Check Redis connection
            if self.redis_client:
                try:
                    # Check if redis_client is a RedisManager instance
                    if hasattr(self.redis_client, 'check_health'):
                        # Use RedisManager's check_health method
                        health = await self.redis_client.check_health()
                        metrics['redis_status']['connected'] = health.get('healthy', False)
                        if health.get('healthy'):
                            metrics['redis_status'].update({
                                'ping_time_seconds': health.get('ping_time_seconds', 0),
                                'connected_clients': health.get('connected_clients', 0),
                                'used_memory_human': health.get('used_memory_human', 'unknown')
                            })
                    else:
                        # Fallback for raw Redis client
                        await self.redis_client.ping()
                        metrics['redis_status']['connected'] = True
                        
                        # Get Redis info
                        info = await self.redis_client.info()
                        metrics['redis_status'].update({
                            'used_memory_mb': info.get('used_memory', 0) / (1024**2),
                            'connected_clients': info.get('connected_clients', 0),
                            'total_commands_processed': info.get('total_commands_processed', 0)
                        })
                except Exception as e:
                    metrics['redis_status']['error'] = str(e)
            
            return metrics
            
        except ImportError:
            return {'error': 'psutil not available for system metrics'}
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {'error': str(e)}
    
    async def collect_all_metrics(self) -> DashboardData:
        """Collect all metrics and return dashboard data"""
        try:
            # Collect all metrics in parallel
            git_metrics, webhook_metrics, workflow_metrics, system_metrics = await asyncio.gather(
                self.collect_git_events_metrics(),
                self.collect_webhook_metrics(),
                self.collect_workflow_metrics(),
                self.collect_system_metrics(),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(git_metrics, Exception):
                git_metrics = {'error': str(git_metrics)}
            if isinstance(webhook_metrics, Exception):
                webhook_metrics = {'error': str(webhook_metrics)}
            if isinstance(workflow_metrics, Exception):
                workflow_metrics = {'error': str(workflow_metrics)}
            if isinstance(system_metrics, Exception):
                system_metrics = {'error': str(system_metrics)}
            
            # Create dashboard data
            dashboard_data = DashboardData(
                git_events=git_metrics.get('recent_events', []),
                webhook_events=webhook_metrics.get('recent_webhooks', []),
                workflow_executions=workflow_metrics.get('recent_executions', []),
                system_metrics={
                    'git_events': git_metrics,
                    'webhooks': webhook_metrics,
                    'workflows': workflow_metrics,
                    'system': system_metrics
                },
                repository_status={
                    'monitored_count': git_metrics.get('monitored_repositories', 0),
                    'repositories': git_metrics.get('repositories', [])
                },
                alerts=await self._generate_alerts(git_metrics, webhook_metrics, workflow_metrics, system_metrics),
                timestamp=datetime.utcnow()
            )
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error collecting all metrics: {e}")
            return DashboardData(
                system_metrics={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _generate_alerts(self, git_metrics: Dict, webhook_metrics: Dict, 
                             workflow_metrics: Dict, system_metrics: Dict) -> List[Dict[str, Any]]:
        """Generate alerts based on metrics"""
        alerts = []
        
        try:
            # System health alerts
            if 'system_health' in system_metrics:
                health = system_metrics['system_health']
                
                if health.get('cpu_usage_percent', 0) > 80:
                    alerts.append({
                        'level': 'warning',
                        'message': f"High CPU usage: {health['cpu_usage_percent']:.1f}%",
                        'timestamp': datetime.utcnow().isoformat(),
                        'category': 'system'
                    })
                
                if health.get('memory_usage_percent', 0) > 85:
                    alerts.append({
                        'level': 'warning',
                        'message': f"High memory usage: {health['memory_usage_percent']:.1f}%",
                        'timestamp': datetime.utcnow().isoformat(),
                        'category': 'system'
                    })
                
                if health.get('disk_usage_percent', 0) > 90:
                    alerts.append({
                        'level': 'critical',
                        'message': f"Low disk space: {health['disk_usage_percent']:.1f}% used",
                        'timestamp': datetime.utcnow().isoformat(),
                        'category': 'system'
                    })
            
            # Redis connection alert
            if not system_metrics.get('redis_status', {}).get('connected', False):
                alerts.append({
                    'level': 'error',
                    'message': "Redis connection lost",
                    'timestamp': datetime.utcnow().isoformat(),
                    'category': 'database'
                })
            
            # Workflow failure rate alert
            if workflow_metrics.get('success_rate', 1.0) < 0.8:
                alerts.append({
                    'level': 'warning',
                    'message': f"Low workflow success rate: {workflow_metrics['success_rate']:.1%}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'category': 'workflows'
                })
            
            # Git monitoring alert
            if not git_metrics.get('monitoring_active', False):
                alerts.append({
                    'level': 'warning',
                    'message': "Git event monitoring is not active",
                    'timestamp': datetime.utcnow().isoformat(),
                    'category': 'git'
                })
        
        except Exception as e:
            self.logger.error(f"Error generating alerts: {e}")
        
        return alerts


class DashboardWebSocket:
    """WebSocket handler for real-time dashboard updates"""
    
    def __init__(self, metrics_collector: DashboardMetricsCollector):
        self.metrics_collector = metrics_collector
        self.clients: weakref.WeakSet = weakref.WeakSet()
        self.update_interval = 5.0  # seconds
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def add_client(self, websocket: WebSocketResponse):
        """Add a WebSocket client"""
        self.clients.add(websocket)
        self.logger.info("WebSocket client connected")
    
    def remove_client(self, websocket: WebSocketResponse):
        """Remove a WebSocket client"""
        try:
            self.clients.discard(websocket)
            self.logger.info("WebSocket client disconnected")
        except Exception as e:
            self.logger.debug(f"Error removing client: {e}")
    
    async def start_broadcast(self):
        """Start broadcasting dashboard updates"""
        self.running = True
        self.logger.info("Started dashboard WebSocket broadcasting")
        
        while self.running:
            try:
                if self.clients:
                    # Collect latest metrics
                    dashboard_data = await self.metrics_collector.collect_all_metrics()
                    
                    # Convert to JSON
                    message = {
                        'type': 'dashboard_update',
                        'data': {
                            'git_events': dashboard_data.git_events,
                            'webhook_events': dashboard_data.webhook_events,
                            'workflow_executions': dashboard_data.workflow_executions,
                            'system_metrics': dashboard_data.system_metrics,
                            'repository_status': dashboard_data.repository_status,
                            'alerts': dashboard_data.alerts,
                            'timestamp': dashboard_data.timestamp.isoformat()
                        }
                    }
                    
                    # Broadcast to all clients
                    await self._broadcast_message(json.dumps(message))
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in dashboard broadcast: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _broadcast_message(self, message: str):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        # Create a copy of clients to iterate over
        clients_copy = list(self.clients)
        
        for client in clients_copy:
            try:
                if client.closed:
                    self.clients.discard(client)
                    continue
                
                await client.send_str(message)
                
            except Exception as e:
                self.logger.debug(f"Error sending to WebSocket client: {e}")
                self.clients.discard(client)
    
    def stop_broadcast(self):
        """Stop broadcasting"""
        self.running = False
        self.logger.info("Stopped dashboard WebSocket broadcasting")


class GitOpsDashboard:
    """GitOps monitoring dashboard web application"""
    
    def __init__(self, metrics_collector: DashboardMetricsCollector, 
                 host: str = '0.0.0.0', port: int = 8090):
        """Initialize dashboard"""
        self.metrics_collector = metrics_collector
        self.websocket_handler = DashboardWebSocket(metrics_collector)
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.broadcast_task = None
        self.logger = logging.getLogger(__name__)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup dashboard routes"""
        # API endpoints
        self.app.router.add_get('/api/dashboard', self._api_dashboard_data)
        self.app.router.add_get('/api/metrics', self._api_metrics)
        self.app.router.add_get('/api/health', self._api_health)
        
        # WebSocket endpoint
        self.app.router.add_get('/ws', self._websocket_handler)
        
        # Static files (dashboard UI)
        self.app.router.add_get('/', self._dashboard_index)
        self.app.router.add_get('/dashboard', self._dashboard_index)
    
    async def _api_dashboard_data(self, request: Request) -> Response:
        """API endpoint for dashboard data"""
        try:
            dashboard_data = await self.metrics_collector.collect_all_metrics()
            
            response_data = {
                'git_events': dashboard_data.git_events,
                'webhook_events': dashboard_data.webhook_events,
                'workflow_executions': dashboard_data.workflow_executions,
                'system_metrics': dashboard_data.system_metrics,
                'repository_status': dashboard_data.repository_status,
                'alerts': dashboard_data.alerts,
                'timestamp': dashboard_data.timestamp.isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            self.logger.error(f"Error in dashboard API: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_metrics(self, request: Request) -> Response:
        """API endpoint for raw metrics"""
        try:
            metrics = await self.metrics_collector.collect_all_metrics()
            return web.json_response(metrics.system_metrics)
            
        except Exception as e:
            self.logger.error(f"Error in metrics API: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_health(self, request: Request) -> Response:
        """Health check endpoint"""
        try:
            system_metrics = await self.metrics_collector.collect_system_metrics()
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'components': system_metrics.get('component_status', {}),
                'redis_connected': system_metrics.get('redis_status', {}).get('connected', False)
            }
            
            # Determine overall health
            if not health_status['redis_connected']:
                health_status['status'] = 'degraded'
            
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return web.json_response(health_status, status=status_code)
            
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
            return web.json_response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)
    
    async def _websocket_handler(self, request: Request) -> WebSocketResponse:
        """WebSocket handler for real-time updates"""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_handler.add_client(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Handle client messages if needed
                    pass
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
                    break
        
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        
        finally:
            self.websocket_handler.remove_client(ws)
        
        return ws
    
    async def _dashboard_index(self, request: Request) -> Response:
        """Serve dashboard index page"""
        # Simple HTML dashboard (in a real implementation, this would serve a React/Vue app)
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>KiroLinter DevOps Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #27ae60; }
        .metric-label { color: #7f8c8d; margin-top: 5px; }
        .alerts { background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .status-healthy { background-color: #27ae60; }
        .status-warning { background-color: #f39c12; }
        .status-error { background-color: #e74c3c; }
        #connection-status { position: fixed; top: 10px; right: 10px; padding: 8px 16px; border-radius: 4px; }
        .connected { background-color: #27ae60; color: white; }
        .disconnected { background-color: #e74c3c; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div id="connection-status" class="disconnected">Connecting...</div>
        
        <div class="header">
            <h1>🤖 KiroLinter DevOps Dashboard</h1>
            <p>Real-time GitOps monitoring and analytics</p>
        </div>
        
        <div id="alerts-container"></div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="git-events-count">0</div>
                <div class="metric-label">Git Events (24h)</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value" id="webhook-count">0</div>
                <div class="metric-label">Webhook Events</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value" id="workflow-count">0</div>
                <div class="metric-label">Workflow Executions</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value" id="repo-count">0</div>
                <div class="metric-label">Monitored Repositories</div>
            </div>
        </div>
        
        <div class="metrics-grid" style="margin-top: 20px;">
            <div class="metric-card">
                <h3>System Health</h3>
                <div id="system-health"></div>
            </div>
            
            <div class="metric-card">
                <h3>Component Status</h3>
                <div id="component-status"></div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let reconnectTimer = null;
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                updateConnectionStatus(true);
                clearTimeout(reconnectTimer);
            };
            
            ws.onmessage = function(event) {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'dashboard_update') {
                        updateDashboard(message.data);
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                // Reconnect after 5 seconds
                reconnectTimer = setTimeout(connect, 5000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
        }
        
        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connection-status');
            if (connected) {
                statusEl.textContent = 'Connected';
                statusEl.className = 'connected';
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'disconnected';
            }
        }
        
        function updateDashboard(data) {
            // Update metrics
            document.getElementById('git-events-count').textContent = data.git_events?.length || 0;
            document.getElementById('webhook-count').textContent = data.webhook_events?.length || 0;
            document.getElementById('workflow-count').textContent = data.system_metrics?.workflows?.total_workflows || 0;
            document.getElementById('repo-count').textContent = data.repository_status?.monitored_count || 0;
            
            // Update system health
            const systemHealth = data.system_metrics?.system?.system_health;
            if (systemHealth) {
                document.getElementById('system-health').innerHTML = `
                    <p>CPU: ${systemHealth.cpu_usage_percent?.toFixed(1)}%</p>
                    <p>Memory: ${systemHealth.memory_usage_percent?.toFixed(1)}%</p>
                    <p>Disk: ${systemHealth.disk_usage_percent?.toFixed(1)}%</p>
                `;
            }
            
            // Update component status
            const componentStatus = data.system_metrics?.system?.component_status;
            if (componentStatus) {
                const statusHtml = Object.entries(componentStatus).map(([key, value]) => {
                    const statusClass = value ? 'status-healthy' : 'status-error';
                    const statusText = value ? 'Online' : 'Offline';
                    return `<p><span class="status-indicator ${statusClass}"></span>${key}: ${statusText}</p>`;
                }).join('');
                document.getElementById('component-status').innerHTML = statusHtml;
            }
            
            // Update alerts
            const alertsContainer = document.getElementById('alerts-container');
            if (data.alerts && data.alerts.length > 0) {
                const alertsHtml = data.alerts.map(alert => 
                    `<div class="alerts">${alert.level.toUpperCase()}: ${alert.message}</div>`
                ).join('');
                alertsContainer.innerHTML = alertsHtml;
            } else {
                alertsContainer.innerHTML = '';
            }
        }
        
        // Start connection
        connect();
        
        // Fallback: refresh data via API every 30 seconds
        setInterval(async function() {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();
                    updateDashboard(data);
                } catch (e) {
                    console.error('Error fetching dashboard data:', e);
                }
            }
        }, 30000);
    </script>
</body>
</html>
        """
        
        return web.Response(text=html_content, content_type='text/html')
    
    async def start(self):
        """Start dashboard server"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            # Start WebSocket broadcasting
            self.broadcast_task = asyncio.create_task(self.websocket_handler.start_broadcast())
            
            self.logger.info(f"GitOps Dashboard started on http://{self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")
            raise
    
    async def stop(self):
        """Stop dashboard server"""
        try:
            # Stop WebSocket broadcasting
            if self.broadcast_task:
                self.websocket_handler.stop_broadcast()
                self.broadcast_task.cancel()
                try:
                    await self.broadcast_task
                except asyncio.CancelledError:
                    pass
            
            # Stop web server
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            self.logger.info("GitOps Dashboard stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping dashboard: {e}")
    
    def get_dashboard_info(self) -> Dict[str, Any]:
        """Get dashboard information"""
        return {
            'host': self.host,
            'port': self.port,
            'running': self.site is not None,
            'websocket_clients': len(self.websocket_handler.clients),
            'update_interval': self.websocket_handler.update_interval,
            'dashboard_url': f'http://{self.host}:{self.port}',
            'api_endpoints': [
                '/api/dashboard',
                '/api/metrics', 
                '/api/health'
            ]
        }