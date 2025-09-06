"""
Monitoring Worker

Celery worker for collecting real-time monitoring data from various
integrations and systems for DevOps analytics and insights.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from .celery_app import app, BaseTask, get_retry_config

logger = logging.getLogger(__name__)


class MonitoringDataCollector:
    """Collects monitoring data from various sources"""
    
    def __init__(self):
        """Initialize monitoring data collector"""
        self.collectors = {}
        self.last_collection_times = {}
    
    async def collect_ci_cd_metrics(self, platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect CI/CD pipeline metrics
        
        Args:
            platform: CI/CD platform name (github, gitlab, jenkins, etc.)
            config: Platform-specific configuration
            
        Returns:
            Dict containing collected metrics
        """
        try:
            if platform == 'github':
                return await self._collect_github_metrics(config)
            elif platform == 'gitlab':
                return await self._collect_gitlab_metrics(config)
            elif platform == 'jenkins':
                return await self._collect_jenkins_metrics(config)
            elif platform == 'azure_devops':
                return await self._collect_azure_devops_metrics(config)
            elif platform == 'circleci':
                return await self._collect_circleci_metrics(config)
            else:
                return {'error': f'Unsupported platform: {platform}'}
                
        except Exception as e:
            logger.error(f"Failed to collect {platform} metrics: {e}")
            return {'error': str(e), 'platform': platform}
    
    async def collect_infrastructure_metrics(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect infrastructure monitoring metrics
        
        Args:
            provider: Infrastructure provider (aws, gcp, azure, etc.)
            config: Provider-specific configuration
            
        Returns:
            Dict containing collected metrics
        """
        try:
            if provider == 'aws':
                return await self._collect_aws_metrics(config)
            elif provider == 'gcp':
                return await self._collect_gcp_metrics(config)
            elif provider == 'azure':
                return await self._collect_azure_metrics(config)
            elif provider == 'kubernetes':
                return await self._collect_kubernetes_metrics(config)
            else:
                return {'error': f'Unsupported provider: {provider}'}
                
        except Exception as e:
            logger.error(f"Failed to collect {provider} metrics: {e}")
            return {'error': str(e), 'provider': provider}
    
    async def collect_application_metrics(self, source: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect application performance metrics
        
        Args:
            source: Monitoring source (prometheus, datadog, newrelic, etc.)
            config: Source-specific configuration
            
        Returns:
            Dict containing collected metrics
        """
        try:
            if source == 'prometheus':
                return await self._collect_prometheus_metrics(config)
            elif source == 'datadog':
                return await self._collect_datadog_metrics(config)
            elif source == 'newrelic':
                return await self._collect_newrelic_metrics(config)
            elif source == 'grafana':
                return await self._collect_grafana_metrics(config)
            else:
                return {'error': f'Unsupported source: {source}'}
                
        except Exception as e:
            logger.error(f"Failed to collect {source} metrics: {e}")
            return {'error': str(e), 'source': source}
    
    # Platform-specific collection methods (mock implementations)
    async def _collect_github_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect GitHub Actions metrics"""
        # Mock implementation - would use GitHub API
        await asyncio.sleep(0.5)  # Simulate API call
        
        return {
            'platform': 'github',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'total_workflows': 25,
                'successful_runs': 22,
                'failed_runs': 3,
                'average_duration_minutes': 8.5,
                'queue_time_minutes': 1.2,
                'success_rate': 0.88,
                'active_runners': 5,
                'pending_jobs': 2
            }
        }
    
    async def _collect_gitlab_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect GitLab CI metrics"""
        # Mock implementation - would use GitLab API
        await asyncio.sleep(0.4)
        
        return {
            'platform': 'gitlab',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'total_pipelines': 18,
                'successful_pipelines': 16,
                'failed_pipelines': 2,
                'average_duration_minutes': 12.3,
                'queue_time_minutes': 0.8,
                'success_rate': 0.89,
                'active_runners': 3,
                'pending_jobs': 1
            }
        }
    
    async def _collect_jenkins_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Jenkins metrics"""
        # Mock implementation - would use Jenkins API
        await asyncio.sleep(0.6)
        
        return {
            'platform': 'jenkins',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'total_builds': 45,
                'successful_builds': 38,
                'failed_builds': 7,
                'average_duration_minutes': 15.2,
                'queue_time_minutes': 2.1,
                'success_rate': 0.84,
                'active_executors': 8,
                'queue_length': 3
            }
        }
    
    async def _collect_azure_devops_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Azure DevOps metrics"""
        # Mock implementation - would use Azure DevOps API
        await asyncio.sleep(0.5)
        
        return {
            'platform': 'azure_devops',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'total_builds': 32,
                'successful_builds': 29,
                'failed_builds': 3,
                'average_duration_minutes': 10.8,
                'queue_time_minutes': 1.5,
                'success_rate': 0.91,
                'active_agents': 4,
                'pending_builds': 1
            }
        }
    
    async def _collect_circleci_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect CircleCI metrics"""
        # Mock implementation - would use CircleCI API
        await asyncio.sleep(0.4)
        
        return {
            'platform': 'circleci',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'total_workflows': 28,
                'successful_workflows': 25,
                'failed_workflows': 3,
                'average_duration_minutes': 7.2,
                'queue_time_minutes': 0.5,
                'success_rate': 0.89,
                'credits_used': 1250,
                'credits_remaining': 8750
            }
        }
    
    async def _collect_aws_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect AWS CloudWatch metrics"""
        # Mock implementation - would use AWS CloudWatch API
        await asyncio.sleep(0.7)
        
        return {
            'provider': 'aws',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'ec2_instances': {
                    'running': 12,
                    'stopped': 3,
                    'cpu_utilization_avg': 45.2,
                    'memory_utilization_avg': 62.1
                },
                'lambda_functions': {
                    'total_invocations': 15420,
                    'errors': 23,
                    'duration_avg_ms': 245,
                    'throttles': 2
                },
                'rds_instances': {
                    'cpu_utilization_avg': 35.8,
                    'connections': 45,
                    'read_latency_ms': 12.3,
                    'write_latency_ms': 8.7
                }
            }
        }
    
    async def _collect_kubernetes_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Kubernetes metrics"""
        # Mock implementation - would use Kubernetes API
        await asyncio.sleep(0.6)
        
        return {
            'provider': 'kubernetes',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'nodes': {
                    'total': 5,
                    'ready': 5,
                    'cpu_utilization_avg': 52.3,
                    'memory_utilization_avg': 68.9
                },
                'pods': {
                    'total': 48,
                    'running': 45,
                    'pending': 2,
                    'failed': 1
                },
                'deployments': {
                    'total': 12,
                    'available': 11,
                    'unavailable': 1
                }
            }
        }
    
    async def _collect_prometheus_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Prometheus metrics"""
        # Mock implementation - would use Prometheus API
        await asyncio.sleep(0.5)
        
        return {
            'source': 'prometheus',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'http_requests_total': 125420,
                'http_request_duration_seconds': 0.245,
                'error_rate': 0.012,
                'cpu_usage_percent': 45.2,
                'memory_usage_bytes': 2147483648,
                'disk_usage_percent': 72.1
            }
        }
    
    async def _collect_datadog_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Datadog metrics"""
        # Mock implementation - would use Datadog API
        await asyncio.sleep(0.4)
        
        return {
            'source': 'datadog',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'apm_traces': 45230,
                'error_rate': 0.008,
                'latency_p95_ms': 125,
                'throughput_rpm': 2340,
                'infrastructure_hosts': 15,
                'logs_ingested': 1250000
            }
        }
    
    async def _collect_newrelic_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect New Relic metrics"""
        # Mock implementation - would use New Relic API
        await asyncio.sleep(0.5)
        
        return {
            'source': 'newrelic',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'apdex_score': 0.92,
                'response_time_ms': 185,
                'throughput_rpm': 1850,
                'error_rate': 0.015,
                'database_time_ms': 45,
                'external_time_ms': 23
            }
        }
    
    async def _collect_grafana_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Grafana dashboard metrics"""
        # Mock implementation - would use Grafana API
        await asyncio.sleep(0.3)
        
        return {
            'source': 'grafana',
            'collected_at': datetime.utcnow().isoformat(),
            'metrics': {
                'dashboards_total': 25,
                'alerts_firing': 2,
                'alerts_pending': 1,
                'data_sources': 8,
                'users_active': 45,
                'queries_per_second': 125
            }
        }


# Global monitoring collector instance
monitoring_collector = MonitoringDataCollector()


# Celery Tasks
@app.task(bind=True, base=BaseTask, name='monitoring_worker.collect_ci_cd_metrics')
def collect_ci_cd_metrics_task(self, platform: str, config: Dict[str, Any]):
    """
    Celery task for collecting CI/CD metrics
    
    Args:
        platform: CI/CD platform name
        config: Platform-specific configuration
        
    Returns:
        Dict containing collected metrics
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Collecting {platform} metrics'})
        
        # Collect metrics asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                monitoring_collector.collect_ci_cd_metrics(platform, config)
            )
            
            # Store metrics in Redis for real-time access
            try:
                from ..cache.redis_client import get_redis_client
                redis_client = get_redis_client()
                if redis_client:
                    key = f"ci_cd_metrics:{platform}:{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
                    redis_client.setex(key, 3600, json.dumps(result))  # 1 hour TTL
            except Exception as e:
                logger.warning(f"Failed to store metrics in Redis: {e}")
            
            self.update_state(state='SUCCESS', meta=result)
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"CI/CD metrics collection failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('monitoring_collection')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='monitoring_worker.collect_infrastructure_metrics')
def collect_infrastructure_metrics_task(self, provider: str, config: Dict[str, Any]):
    """
    Celery task for collecting infrastructure metrics
    
    Args:
        provider: Infrastructure provider name
        config: Provider-specific configuration
        
    Returns:
        Dict containing collected metrics
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Collecting {provider} metrics'})
        
        # Collect metrics asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                monitoring_collector.collect_infrastructure_metrics(provider, config)
            )
            
            # Store metrics in Redis
            try:
                from ..cache.redis_client import get_redis_client
                redis_client = get_redis_client()
                if redis_client:
                    key = f"infra_metrics:{provider}:{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
                    redis_client.setex(key, 3600, json.dumps(result))  # 1 hour TTL
            except Exception as e:
                logger.warning(f"Failed to store metrics in Redis: {e}")
            
            self.update_state(state='SUCCESS', meta=result)
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Infrastructure metrics collection failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('monitoring_collection')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='monitoring_worker.collect_application_metrics')
def collect_application_metrics_task(self, source: str, config: Dict[str, Any]):
    """
    Celery task for collecting application metrics
    
    Args:
        source: Monitoring source name
        config: Source-specific configuration
        
    Returns:
        Dict containing collected metrics
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Collecting {source} metrics'})
        
        # Collect metrics asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                monitoring_collector.collect_application_metrics(source, config)
            )
            
            # Store metrics in Redis
            try:
                from ..cache.redis_client import get_redis_client
                redis_client = get_redis_client()
                if redis_client:
                    key = f"app_metrics:{source}:{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
                    redis_client.setex(key, 3600, json.dumps(result))  # 1 hour TTL
            except Exception as e:
                logger.warning(f"Failed to store metrics in Redis: {e}")
            
            self.update_state(state='SUCCESS', meta=result)
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Application metrics collection failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('monitoring_collection')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='monitoring_worker.collect_all_metrics')
def collect_all_metrics_task(self, monitoring_config: Dict[str, Any]):
    """
    Collect metrics from all configured sources
    
    Args:
        monitoring_config: Configuration for all monitoring sources
        
    Returns:
        Dict containing all collected metrics
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Collecting metrics from all sources'})
        
        all_metrics = {
            'collected_at': datetime.utcnow().isoformat(),
            'ci_cd_metrics': {},
            'infrastructure_metrics': {},
            'application_metrics': {},
            'errors': []
        }
        
        # Collect CI/CD metrics
        ci_cd_config = monitoring_config.get('ci_cd', {})
        for platform, config in ci_cd_config.items():
            try:
                task = collect_ci_cd_metrics_task.delay(platform, config)
                result = task.get(timeout=60)  # 1 minute timeout
                all_metrics['ci_cd_metrics'][platform] = result
            except Exception as e:
                error_msg = f"Failed to collect {platform} metrics: {str(e)}"
                logger.error(error_msg)
                all_metrics['errors'].append(error_msg)
        
        # Collect infrastructure metrics
        infra_config = monitoring_config.get('infrastructure', {})
        for provider, config in infra_config.items():
            try:
                task = collect_infrastructure_metrics_task.delay(provider, config)
                result = task.get(timeout=60)  # 1 minute timeout
                all_metrics['infrastructure_metrics'][provider] = result
            except Exception as e:
                error_msg = f"Failed to collect {provider} metrics: {str(e)}"
                logger.error(error_msg)
                all_metrics['errors'].append(error_msg)
        
        # Collect application metrics
        app_config = monitoring_config.get('application', {})
        for source, config in app_config.items():
            try:
                task = collect_application_metrics_task.delay(source, config)
                result = task.get(timeout=60)  # 1 minute timeout
                all_metrics['application_metrics'][source] = result
            except Exception as e:
                error_msg = f"Failed to collect {source} metrics: {str(e)}"
                logger.error(error_msg)
                all_metrics['errors'].append(error_msg)
        
        # Store aggregated metrics
        try:
            from ..cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                key = f"all_metrics:{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
                redis_client.setex(key, 3600, json.dumps(all_metrics))  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Failed to store aggregated metrics in Redis: {e}")
        
        self.update_state(state='SUCCESS', meta=all_metrics)
        return all_metrics
        
    except Exception as e:
        logger.error(f"All metrics collection failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'collected_at': datetime.utcnow().isoformat()
        }


@app.task(bind=True, base=BaseTask, name='monitoring_worker.analyze_metrics_trends')
def analyze_metrics_trends_task(self, time_range_hours: int = 24):
    """
    Analyze metrics trends over time
    
    Args:
        time_range_hours: Time range for trend analysis
        
    Returns:
        Dict containing trend analysis results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Analyzing trends for last {time_range_hours} hours'})
        
        # Get historical metrics from Redis
        try:
            from ..cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            
            if not redis_client:
                return {'error': 'Redis client not available'}
            
            # Get all metrics keys within time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            all_metrics = []
            patterns = ['ci_cd_metrics:*', 'infra_metrics:*', 'app_metrics:*', 'all_metrics:*']
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                for key in keys:
                    try:
                        # Extract timestamp from key
                        timestamp_str = key.decode().split(':')[-1]
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                        
                        if start_time <= timestamp <= end_time:
                            data = redis_client.get(key)
                            if data:
                                metrics = json.loads(data)
                                metrics['timestamp'] = timestamp.isoformat()
                                all_metrics.append(metrics)
                    except (ValueError, json.JSONDecodeError):
                        continue
            
            # Analyze trends (simplified analysis)
            trend_analysis = {
                'time_range_hours': time_range_hours,
                'total_data_points': len(all_metrics),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'trends': {
                    'ci_cd_success_rate': self._analyze_success_rate_trend(all_metrics, 'ci_cd'),
                    'infrastructure_utilization': self._analyze_utilization_trend(all_metrics, 'infrastructure'),
                    'application_performance': self._analyze_performance_trend(all_metrics, 'application')
                }
            }
            
            self.update_state(state='SUCCESS', meta=trend_analysis)
            return trend_analysis
            
        except Exception as e:
            logger.error(f"Failed to retrieve metrics from Redis: {e}")
            return {'error': f'Failed to retrieve metrics: {str(e)}'}
            
    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'time_range_hours': time_range_hours
        }
    
    def _analyze_success_rate_trend(self, metrics_data: List[Dict], category: str) -> Dict[str, Any]:
        """Analyze success rate trends"""
        success_rates = []
        
        for data in metrics_data:
            if category in data:
                for platform, platform_data in data[category].items():
                    if 'metrics' in platform_data and 'success_rate' in platform_data['metrics']:
                        success_rates.append(platform_data['metrics']['success_rate'])
        
        if not success_rates:
            return {'trend': 'no_data', 'average': 0, 'data_points': 0}
        
        average = sum(success_rates) / len(success_rates)
        trend = 'stable'
        
        if len(success_rates) >= 2:
            recent_avg = sum(success_rates[-5:]) / min(5, len(success_rates))
            older_avg = sum(success_rates[:5]) / min(5, len(success_rates))
            
            if recent_avg > older_avg + 0.05:
                trend = 'improving'
            elif recent_avg < older_avg - 0.05:
                trend = 'declining'
        
        return {
            'trend': trend,
            'average': average,
            'data_points': len(success_rates),
            'recent_average': recent_avg if len(success_rates) >= 2 else average
        }
    
    def _analyze_utilization_trend(self, metrics_data: List[Dict], category: str) -> Dict[str, Any]:
        """Analyze resource utilization trends"""
        utilizations = []
        
        for data in metrics_data:
            if category in data:
                for provider, provider_data in data[category].items():
                    if 'metrics' in provider_data:
                        # Extract CPU utilization from various sources
                        metrics = provider_data['metrics']
                        if 'cpu_utilization_avg' in metrics:
                            utilizations.append(metrics['cpu_utilization_avg'])
                        elif 'ec2_instances' in metrics and 'cpu_utilization_avg' in metrics['ec2_instances']:
                            utilizations.append(metrics['ec2_instances']['cpu_utilization_avg'])
        
        if not utilizations:
            return {'trend': 'no_data', 'average': 0, 'data_points': 0}
        
        average = sum(utilizations) / len(utilizations)
        trend = 'stable'
        
        if len(utilizations) >= 2:
            recent_avg = sum(utilizations[-5:]) / min(5, len(utilizations))
            older_avg = sum(utilizations[:5]) / min(5, len(utilizations))
            
            if recent_avg > older_avg + 5:
                trend = 'increasing'
            elif recent_avg < older_avg - 5:
                trend = 'decreasing'
        
        return {
            'trend': trend,
            'average': average,
            'data_points': len(utilizations),
            'recent_average': recent_avg if len(utilizations) >= 2 else average
        }
    
    def _analyze_performance_trend(self, metrics_data: List[Dict], category: str) -> Dict[str, Any]:
        """Analyze application performance trends"""
        response_times = []
        
        for data in metrics_data:
            if category in data:
                for source, source_data in data[category].items():
                    if 'metrics' in source_data:
                        metrics = source_data['metrics']
                        if 'response_time_ms' in metrics:
                            response_times.append(metrics['response_time_ms'])
                        elif 'http_request_duration_seconds' in metrics:
                            response_times.append(metrics['http_request_duration_seconds'] * 1000)
        
        if not response_times:
            return {'trend': 'no_data', 'average': 0, 'data_points': 0}
        
        average = sum(response_times) / len(response_times)
        trend = 'stable'
        
        if len(response_times) >= 2:
            recent_avg = sum(response_times[-5:]) / min(5, len(response_times))
            older_avg = sum(response_times[:5]) / min(5, len(response_times))
            
            if recent_avg > older_avg + 20:  # 20ms threshold
                trend = 'degrading'
            elif recent_avg < older_avg - 20:
                trend = 'improving'
        
        return {
            'trend': trend,
            'average': average,
            'data_points': len(response_times),
            'recent_average': recent_avg if len(response_times) >= 2 else average
        }


# Periodic monitoring tasks
@app.task(bind=True, base=BaseTask, name='monitoring_worker.cleanup_old_metrics')
def cleanup_old_metrics_task(self, max_age_hours: int = 168):  # 7 days default
    """
    Clean up old monitoring metrics from Redis
    
    Args:
        max_age_hours: Maximum age of metrics to keep
        
    Returns:
        Dict containing cleanup statistics
    """
    try:
        logger.info(f"Cleaning up monitoring metrics older than {max_age_hours} hours")
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        try:
            from ..cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            
            if redis_client:
                patterns = ['ci_cd_metrics:*', 'infra_metrics:*', 'app_metrics:*', 'all_metrics:*']
                
                for pattern in patterns:
                    keys = redis_client.keys(pattern)
                    for key in keys:
                        try:
                            # Extract timestamp from key
                            timestamp_str = key.decode().split(':')[-1]
                            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                            
                            if timestamp < cutoff_time:
                                redis_client.delete(key)
                                cleaned_count += 1
                        except (ValueError, IndexError):
                            continue
        except Exception as e:
            logger.warning(f"Failed to clean up metrics from Redis: {e}")
        
        result = {
            'success': True,
            'cleaned_metrics': cleaned_count,
            'max_age_hours': max_age_hours,
            'cutoff_time': cutoff_time.isoformat(),
            'cleaned_at': datetime.utcnow().isoformat()
        }
        
        self.update_state(state='SUCCESS', meta=result)
        return result
        
    except Exception as e:
        logger.error(f"Metrics cleanup failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'max_age_hours': max_age_hours
        }