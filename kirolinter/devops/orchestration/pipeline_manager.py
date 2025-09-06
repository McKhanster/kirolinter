"""
Pipeline Manager

Manages CI/CD pipeline integrations with unified interface for
cross-platform coordination and optimization.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from ..models.pipeline import PipelineIntegration, PipelineConfig, PlatformType
from ..integrations.cicd.connector_factory import CICDConnectorFactory
from ..integrations.cicd.base_connector import BaseCICDConnector

logger = logging.getLogger(__name__)


class PipelineManager:
    """Unified pipeline management interface"""
    
    def __init__(self):
        """Initialize pipeline manager"""
        self.integrations: Dict[str, PipelineIntegration] = {}
        self.connectors: Dict[str, BaseCICDConnector] = {}
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        self.sync_interval_seconds = 300  # 5 minutes
    
    async def add_integration(self, integration: PipelineIntegration) -> bool:
        """
        Add a new pipeline integration
        
        Args:
            integration: Pipeline integration configuration
            
        Returns:
            bool: True if integration added successfully
        """
        logger.info(f"Adding pipeline integration: {integration.name}")
        
        try:
            # Create connector
            connector = CICDConnectorFactory.create_connector(integration.configuration)
            if not connector:
                logger.error(f"Failed to create connector for platform: {integration.platform}")
                return False
            
            # Test connection
            connection_test = await connector.test_connection()
            if not connection_test.get("connected", False):
                logger.error(f"Connection test failed for {integration.name}: {connection_test.get('error')}")
                integration.status = integration.status.ERROR
                integration.error_message = connection_test.get("error", "Connection failed")
            else:
                integration.status = integration.status.ACTIVE
                integration.error_message = None
            
            # Store integration and connector
            self.integrations[integration.id] = integration
            self.connectors[integration.id] = connector
            
            # Start sync task
            await self._start_sync_task(integration.id)
            
            logger.info(f"Successfully added pipeline integration: {integration.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add pipeline integration {integration.name}: {e}")
            integration.status = integration.status.ERROR
            integration.error_message = str(e)
            return False
    
    async def remove_integration(self, integration_id: str) -> bool:
        """
        Remove a pipeline integration
        
        Args:
            integration_id: Integration identifier
            
        Returns:
            bool: True if integration removed successfully
        """
        if integration_id not in self.integrations:
            logger.warning(f"Integration not found: {integration_id}")
            return False
        
        logger.info(f"Removing pipeline integration: {integration_id}")
        
        # Stop sync task
        await self._stop_sync_task(integration_id)
        
        # Remove from storage
        del self.integrations[integration_id]
        if integration_id in self.connectors:
            del self.connectors[integration_id]
        
        return True
    
    async def trigger_pipeline(self, integration_id: str, pipeline_id: str,
                             parameters: Dict[str, Any] = None) -> Optional[str]:
        """
        Trigger a pipeline execution
        
        Args:
            integration_id: Integration identifier
            pipeline_id: Platform-specific pipeline identifier
            parameters: Optional parameters for the pipeline
            
        Returns:
            Run ID if successful, None otherwise
        """
        connector = self.connectors.get(integration_id)
        if not connector:
            logger.error(f"Connector not found for integration: {integration_id}")
            return None
        
        try:
            run_id = await connector.trigger_pipeline(pipeline_id, parameters)
            logger.info(f"Triggered pipeline {pipeline_id} on integration {integration_id}, run ID: {run_id}")
            return run_id
        except Exception as e:
            logger.error(f"Failed to trigger pipeline {pipeline_id}: {e}")
            return None
    
    async def get_pipeline_status(self, integration_id: str, pipeline_id: str, run_id: str):
        """
        Get pipeline run status
        
        Args:
            integration_id: Integration identifier
            pipeline_id: Platform-specific pipeline identifier
            run_id: Platform-specific run identifier
            
        Returns:
            PipelineRun or None if not found
        """
        connector = self.connectors.get(integration_id)
        if not connector:
            logger.error(f"Connector not found for integration: {integration_id}")
            return None
        
        try:
            return await connector.get_pipeline_status(pipeline_id, run_id)
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return None
    
    async def optimize_pipeline(self, integration_id: str, pipeline_id: str) -> Dict[str, Any]:
        """
        AI-powered pipeline optimization
        
        Args:
            integration_id: Integration identifier
            pipeline_id: Platform-specific pipeline identifier
            
        Returns:
            Dict containing optimization recommendations
        """
        connector = self.connectors.get(integration_id)
        if not connector:
            return {"error": "Connector not found"}
        
        try:
            # Get pipeline metrics
            metrics = await connector.get_pipeline_metrics(pipeline_id)
            
            # Generate optimization recommendations
            recommendations = []
            
            if metrics.average_duration_minutes > 10:
                recommendations.append({
                    "type": "performance",
                    "description": "Consider parallelizing jobs to reduce execution time",
                    "potential_savings": f"{metrics.average_duration_minutes * 0.3:.1f} minutes"
                })
            
            if metrics.failure_rate > 0.1:
                recommendations.append({
                    "type": "reliability",
                    "description": "High failure rate detected - review test stability",
                    "current_failure_rate": f"{metrics.failure_rate:.1%}"
                })
            
            if metrics.queue_time_minutes > 2:
                recommendations.append({
                    "type": "resource",
                    "description": "Long queue times - consider adding more runners",
                    "current_queue_time": f"{metrics.queue_time_minutes:.1f} minutes"
                })
            
            return {
                "pipeline_id": pipeline_id,
                "current_metrics": {
                    "average_duration": metrics.average_duration_minutes,
                    "success_rate": metrics.success_rate,
                    "failure_rate": metrics.failure_rate,
                    "queue_time": metrics.queue_time_minutes
                },
                "recommendations": recommendations,
                "optimization_score": self._calculate_optimization_score(metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize pipeline {pipeline_id}: {e}")
            return {"error": str(e)}
    
    async def get_integration_health(self, integration_id: str) -> Dict[str, Any]:
        """
        Get health status of an integration
        
        Args:
            integration_id: Integration identifier
            
        Returns:
            Dict containing health information
        """
        integration = self.integrations.get(integration_id)
        if not integration:
            return {"error": "Integration not found"}
        
        connector = self.connectors.get(integration_id)
        if not connector:
            return {"error": "Connector not found"}
        
        try:
            # Test connection
            connection_test = await connector.test_connection()
            
            # Get sync status
            last_sync = integration.last_sync
            sync_age_minutes = 0
            if last_sync:
                sync_age_minutes = (datetime.utcnow() - last_sync).total_seconds() / 60
            
            health_status = "healthy"
            if not connection_test.get("connected", False):
                health_status = "unhealthy"
            elif sync_age_minutes > 30:  # No sync in 30 minutes
                health_status = "degraded"
            
            return {
                "integration_id": integration_id,
                "name": integration.name,
                "platform": integration.platform,
                "status": integration.status,
                "health": health_status,
                "connection": connection_test,
                "last_sync": last_sync,
                "sync_age_minutes": sync_age_minutes,
                "error_message": integration.error_message
            }
            
        except Exception as e:
            logger.error(f"Failed to get health for integration {integration_id}: {e}")
            return {
                "integration_id": integration_id,
                "health": "unhealthy",
                "error": str(e)
            }
    
    async def sync_all_integrations(self) -> Dict[str, Any]:
        """
        Sync all integrations
        
        Returns:
            Dict containing sync results
        """
        logger.info("Syncing all pipeline integrations")
        
        sync_results = {}
        
        for integration_id, connector in self.connectors.items():
            try:
                sync_result = await connector.sync_status()
                sync_results[integration_id] = sync_result
                
                # Update integration status
                integration = self.integrations[integration_id]
                if sync_result.get("success", False):
                    integration.last_sync = datetime.utcnow()
                    integration.error_message = None
                else:
                    integration.error_message = sync_result.get("error", "Sync failed")
                
            except Exception as e:
                logger.error(f"Failed to sync integration {integration_id}: {e}")
                sync_results[integration_id] = {"success": False, "error": str(e)}
        
        return {
            "total_integrations": len(self.integrations),
            "successful_syncs": sum(1 for r in sync_results.values() if r.get("success", False)),
            "failed_syncs": sum(1 for r in sync_results.values() if not r.get("success", False)),
            "results": sync_results
        }
    
    def get_supported_platforms(self) -> List[PlatformType]:
        """Get list of supported CI/CD platforms"""
        return CICDConnectorFactory.get_supported_platforms()
    
    def get_integrations(self) -> List[PipelineIntegration]:
        """Get all pipeline integrations"""
        return list(self.integrations.values())
    
    async def _start_sync_task(self, integration_id: str):
        """Start background sync task for an integration"""
        if integration_id in self.sync_tasks:
            # Stop existing task
            await self._stop_sync_task(integration_id)
        
        async def sync_loop():
            while integration_id in self.integrations:
                try:
                    connector = self.connectors.get(integration_id)
                    if connector:
                        await connector.sync_status()
                        integration = self.integrations[integration_id]
                        integration.last_sync = datetime.utcnow()
                    
                    await asyncio.sleep(self.sync_interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Sync task error for {integration_id}: {e}")
                    await asyncio.sleep(self.sync_interval_seconds)
        
        task = asyncio.create_task(sync_loop())
        self.sync_tasks[integration_id] = task
        logger.debug(f"Started sync task for integration: {integration_id}")
    
    async def _stop_sync_task(self, integration_id: str):
        """Stop background sync task for an integration"""
        if integration_id in self.sync_tasks:
            task = self.sync_tasks[integration_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.sync_tasks[integration_id]
            logger.debug(f"Stopped sync task for integration: {integration_id}")
    
    def _calculate_optimization_score(self, metrics) -> float:
        """Calculate optimization score based on pipeline metrics"""
        # Simple scoring algorithm - would be more sophisticated in production
        score = 100.0
        
        # Penalize long execution times
        if metrics.average_duration_minutes > 5:
            score -= min((metrics.average_duration_minutes - 5) * 2, 30)
        
        # Penalize high failure rates
        score -= metrics.failure_rate * 50
        
        # Penalize long queue times
        if metrics.queue_time_minutes > 1:
            score -= min((metrics.queue_time_minutes - 1) * 10, 20)
        
        return max(0.0, min(100.0, score))