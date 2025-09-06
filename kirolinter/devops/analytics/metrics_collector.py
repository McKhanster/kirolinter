"""
Metrics Collector

Collects, aggregates, and stores DevOps metrics from various sources
including pipelines, deployments, and quality measurements.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict
import asyncio

from ..models.metrics import (
    MetricValue, QualityMetrics, PerformanceMetrics, 
    DeploymentMetrics, AnalyticsData
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates DevOps metrics from multiple sources"""
    
    def __init__(self, storage_backend=None, collection_interval_seconds=300):
        """
        Initialize metrics collector
        
        Args:
            storage_backend: Backend for storing metrics data
            collection_interval_seconds: How often to collect metrics
        """
        self.storage = storage_backend
        self.collection_interval = collection_interval_seconds
        self.metric_sources = {}
        self.active_collectors = {}
        self.collection_running = False
    
    def register_metric_source(self, source_name: str, source_config: Dict[str, Any]):
        """
        Register a metric source for collection
        
        Args:
            source_name: Unique name for the metric source
            source_config: Configuration for the metric source
        """
        self.metric_sources[source_name] = source_config
        logger.info(f"Registered metric source: {source_name}")
    
    async def start_collection(self):
        """Start continuous metric collection"""
        if self.collection_running:
            logger.warning("Metric collection is already running")
            return
        
        self.collection_running = True
        logger.info("Starting metric collection")
        
        # Start collection tasks for each source
        for source_name, config in self.metric_sources.items():
            task = asyncio.create_task(self._collect_from_source(source_name, config))
            self.active_collectors[source_name] = task
        
        logger.info(f"Started {len(self.active_collectors)} metric collectors")
    
    async def stop_collection(self):
        """Stop metric collection"""
        if not self.collection_running:
            return
        
        self.collection_running = False
        logger.info("Stopping metric collection")
        
        # Cancel all collection tasks
        for source_name, task in self.active_collectors.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.active_collectors.clear()
        logger.info("Stopped all metric collectors")
    
    async def collect_quality_metrics(self, application: str, 
                                    source_data: Dict[str, Any]) -> QualityMetrics:
        """
        Collect quality metrics for an application
        
        Args:
            application: Application name
            source_data: Raw data from quality analysis tools
            
        Returns:
            QualityMetrics: Processed quality metrics
        """
        logger.debug(f"Collecting quality metrics for {application}")
        
        # Extract metrics from source data
        metrics = QualityMetrics(
            code_coverage=source_data.get("coverage", 0.0),
            test_pass_rate=source_data.get("test_pass_rate", 0.0),
            bug_density=source_data.get("bug_density", 0.0),
            technical_debt_ratio=source_data.get("technical_debt", 0.0),
            maintainability_index=source_data.get("maintainability", 0.0),
            cyclomatic_complexity=source_data.get("complexity", 0.0),
            duplication_percentage=source_data.get("duplication", 0.0),
            security_hotspots=source_data.get("security_hotspots", 0),
            vulnerabilities=source_data.get("vulnerabilities", 0),
            code_smells=source_data.get("code_smells", 0),
            lines_of_code=source_data.get("lines_of_code", 0),
            timestamp=datetime.utcnow()
        )
        
        # Store metrics if storage is available
        if self.storage:
            await self._store_metrics(f"{application}_quality", asdict(metrics))
        
        return metrics
    
    async def collect_performance_metrics(self, service: str, 
                                        monitoring_data: Dict[str, Any]) -> PerformanceMetrics:
        """
        Collect performance metrics for a service
        
        Args:
            service: Service name
            monitoring_data: Raw monitoring data
            
        Returns:
            PerformanceMetrics: Processed performance metrics
        """
        logger.debug(f"Collecting performance metrics for {service}")
        
        metrics = PerformanceMetrics(
            response_time_ms=monitoring_data.get("response_time", 0.0),
            throughput_rps=monitoring_data.get("throughput", 0.0),
            error_rate=monitoring_data.get("error_rate", 0.0),
            availability=monitoring_data.get("availability", 0.0),
            cpu_usage=monitoring_data.get("cpu_usage", 0.0),
            memory_usage=monitoring_data.get("memory_usage", 0.0),
            disk_usage=monitoring_data.get("disk_usage", 0.0),
            network_io=monitoring_data.get("network_io", 0.0),
            active_connections=monitoring_data.get("connections", 0),
            queue_depth=monitoring_data.get("queue_depth", 0),
            timestamp=datetime.utcnow()
        )
        
        if self.storage:
            await self._store_metrics(f"{service}_performance", asdict(metrics))
        
        return metrics
    
    async def collect_deployment_metrics(self, application: str, 
                                       deployment_data: List[Dict[str, Any]]) -> DeploymentMetrics:
        """
        Collect deployment metrics for an application
        
        Args:
            application: Application name
            deployment_data: List of deployment records
            
        Returns:
            DeploymentMetrics: Processed deployment metrics
        """
        logger.debug(f"Collecting deployment metrics for {application}")
        
        if not deployment_data:
            return DeploymentMetrics(timestamp=datetime.utcnow())
        
        # Calculate metrics from deployment data
        total_deployments = len(deployment_data)
        successful_deployments = sum(1 for d in deployment_data if d.get("success", False))
        failed_deployments = total_deployments - successful_deployments
        rollbacks = sum(1 for d in deployment_data if d.get("rolled_back", False))
        
        # Calculate averages
        durations = [d.get("duration_hours", 0) for d in deployment_data if d.get("duration_hours")]
        lead_times = [d.get("lead_time_hours", 0) for d in deployment_data if d.get("lead_time_hours")]
        
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0.0
        
        # Calculate deployment frequency (deployments per day)
        if deployment_data:
            date_range = (datetime.utcnow() - datetime.fromisoformat(deployment_data[0].get("date", "2024-01-01"))).days
            deployment_frequency = total_deployments / max(date_range, 1)
        else:
            deployment_frequency = 0.0
        
        metrics = DeploymentMetrics(
            deployment_frequency=deployment_frequency,
            lead_time_hours=avg_lead_time,
            mttr_hours=avg_duration,  # Simplified - would calculate actual MTTR
            change_failure_rate=failed_deployments / total_deployments if total_deployments > 0 else 0.0,
            deployment_success_rate=successful_deployments / total_deployments if total_deployments > 0 else 0.0,
            rollback_rate=rollbacks / total_deployments if total_deployments > 0 else 0.0,
            time_to_restore_hours=avg_duration,  # Simplified
            batch_size=1,  # Would calculate from actual change data
            timestamp=datetime.utcnow()
        )
        
        if self.storage:
            await self._store_metrics(f"{application}_deployment", asdict(metrics))
        
        return metrics
    
    async def aggregate_metrics(self, metric_name: str, 
                              time_range_hours: int = 24,
                              aggregation_type: str = "avg") -> Optional[float]:
        """
        Aggregate metrics over a time range
        
        Args:
            metric_name: Name of the metric to aggregate
            time_range_hours: Time range for aggregation
            aggregation_type: Type of aggregation (avg, sum, min, max, count)
            
        Returns:
            Aggregated metric value or None if no data
        """
        if not self.storage:
            logger.warning("No storage backend configured for metric aggregation")
            return None
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Get metric data from storage
        metric_data = await self._get_metrics_from_storage(metric_name, start_time, end_time)
        
        if not metric_data:
            return None
        
        values = [point["value"] for point in metric_data if "value" in point]
        
        if not values:
            return None
        
        if aggregation_type == "avg":
            return sum(values) / len(values)
        elif aggregation_type == "sum":
            return sum(values)
        elif aggregation_type == "min":
            return min(values)
        elif aggregation_type == "max":
            return max(values)
        elif aggregation_type == "count":
            return len(values)
        else:
            logger.warning(f"Unknown aggregation type: {aggregation_type}")
            return None
    
    async def generate_analytics_report(self, applications: List[str], 
                                      time_range_hours: int = 168) -> AnalyticsData:
        """
        Generate comprehensive analytics report
        
        Args:
            applications: List of applications to include
            time_range_hours: Time range for the report (default: 1 week)
            
        Returns:
            AnalyticsData: Comprehensive analytics report
        """
        logger.info(f"Generating analytics report for {len(applications)} applications")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        analytics = AnalyticsData(
            id=f"report_{int(end_time.timestamp())}",
            name="DevOps Analytics Report",
            description=f"Analytics report for {len(applications)} applications over {time_range_hours} hours",
            time_range_start=start_time,
            time_range_end=end_time
        )
        
        # Collect metrics for each application
        for app in applications:
            # Quality metrics
            quality_data = await self._get_metrics_from_storage(f"{app}_quality", start_time, end_time)
            if quality_data:
                for point in quality_data:
                    analytics.add_metric(f"{app}_quality", point.get("overall_quality_score", 0), 
                                       timestamp=datetime.fromisoformat(point.get("timestamp", str(end_time))))
            
            # Performance metrics
            perf_data = await self._get_metrics_from_storage(f"{app}_performance", start_time, end_time)
            if perf_data:
                for point in perf_data:
                    analytics.add_metric(f"{app}_performance", point.get("health_score", 0),
                                       timestamp=datetime.fromisoformat(point.get("timestamp", str(end_time))))
            
            # Deployment metrics
            deploy_data = await self._get_metrics_from_storage(f"{app}_deployment", start_time, end_time)
            if deploy_data:
                for point in deploy_data:
                    analytics.add_metric(f"{app}_deployment_success", point.get("deployment_success_rate", 0),
                                       timestamp=datetime.fromisoformat(point.get("timestamp", str(end_time))))
        
        # Calculate aggregations
        for metric_name in analytics.metrics:
            analytics.aggregations[f"{metric_name}_avg"] = analytics.calculate_aggregation(metric_name, "avg")
            analytics.aggregations[f"{metric_name}_min"] = analytics.calculate_aggregation(metric_name, "min")
            analytics.aggregations[f"{metric_name}_max"] = analytics.calculate_aggregation(metric_name, "max")
        
        return analytics
    
    async def _collect_from_source(self, source_name: str, config: Dict[str, Any]):
        """Continuously collect metrics from a source"""
        logger.info(f"Starting collection from source: {source_name}")
        
        while self.collection_running:
            try:
                # Mock metric collection - would integrate with actual sources
                await self._collect_source_metrics(source_name, config)
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting from {source_name}: {e}")
                await asyncio.sleep(self.collection_interval)
        
        logger.info(f"Stopped collection from source: {source_name}")
    
    async def _collect_source_metrics(self, source_name: str, config: Dict[str, Any]):
        """Collect metrics from a specific source"""
        source_type = config.get("type", "unknown")
        
        if source_type == "quality":
            # Mock quality metrics collection
            mock_data = {
                "coverage": 0.85,
                "test_pass_rate": 0.95,
                "bug_density": 2.5,
                "technical_debt": 0.15,
                "maintainability": 75.0,
                "complexity": 8.2,
                "duplication": 5.0,
                "security_hotspots": 3,
                "vulnerabilities": 1,
                "code_smells": 12,
                "lines_of_code": 15000
            }
            await self.collect_quality_metrics(config.get("application", "unknown"), mock_data)
        
        elif source_type == "performance":
            # Mock performance metrics collection
            mock_data = {
                "response_time": 150.0,
                "throughput": 1000.0,
                "error_rate": 0.02,
                "availability": 0.999,
                "cpu_usage": 45.0,
                "memory_usage": 60.0,
                "disk_usage": 30.0,
                "network_io": 100.0,
                "connections": 250,
                "queue_depth": 5
            }
            await self.collect_performance_metrics(config.get("service", "unknown"), mock_data)
    
    async def _store_metrics(self, metric_key: str, metric_data: Dict[str, Any]):
        """Store metrics in the backend"""
        if not self.storage:
            return
        
        try:
            # Mock storage - would use actual storage backend
            logger.debug(f"Storing metrics for {metric_key}")
        except Exception as e:
            logger.error(f"Failed to store metrics for {metric_key}: {e}")
    
    async def _get_metrics_from_storage(self, metric_name: str, 
                                      start_time: datetime, 
                                      end_time: datetime) -> List[Dict[str, Any]]:
        """Get metrics from storage backend"""
        if not self.storage:
            return []
        
        try:
            # Mock data retrieval - would query actual storage
            return []
        except Exception as e:
            logger.error(f"Failed to get metrics {metric_name}: {e}")
            return []