"""
CI/CD Connector Factory

Factory class for creating CI/CD platform connectors based on
platform type and configuration.
"""

from typing import Dict, Type, Optional
import logging

from .base_connector import BaseCICDConnector
from ...models.pipeline import PipelineConfig, PlatformType

logger = logging.getLogger(__name__)


class CICDConnectorFactory:
    """Factory for creating CI/CD platform connectors"""
    
    _connectors: Dict[PlatformType, Type[BaseCICDConnector]] = {}
    
    @classmethod
    def register_connector(cls, platform: PlatformType, 
                         connector_class: Type[BaseCICDConnector]):
        """
        Register a connector class for a platform
        
        Args:
            platform: The platform type
            connector_class: The connector class to register
        """
        cls._connectors[platform] = connector_class
        logger.info(f"Registered connector for platform: {platform}")
    
    @classmethod
    def create_connector(cls, config: PipelineConfig) -> Optional[BaseCICDConnector]:
        """
        Create a connector instance for the specified platform
        
        Args:
            config: Pipeline configuration containing platform information
            
        Returns:
            BaseCICDConnector instance or None if platform not supported
        """
        platform = config.platform
        
        if platform not in cls._connectors:
            logger.error(f"No connector registered for platform: {platform}")
            return None
        
        try:
            connector_class = cls._connectors[platform]
            connector = connector_class(config)
            logger.info(f"Created connector for platform: {platform}")
            return connector
        except Exception as e:
            logger.error(f"Failed to create connector for platform {platform}: {e}")
            return None
    
    @classmethod
    def get_supported_platforms(cls) -> list[PlatformType]:
        """
        Get list of supported platforms
        
        Returns:
            List of supported platform types
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def is_platform_supported(cls, platform: PlatformType) -> bool:
        """
        Check if a platform is supported
        
        Args:
            platform: Platform type to check
            
        Returns:
            True if platform is supported, False otherwise
        """
        return platform in cls._connectors
    
    @classmethod
    def get_connector_info(cls, platform: PlatformType) -> Optional[Dict[str, any]]:
        """
        Get information about a connector
        
        Args:
            platform: Platform type
            
        Returns:
            Dict containing connector information or None if not supported
        """
        if platform not in cls._connectors:
            return None
        
        connector_class = cls._connectors[platform]
        return {
            "platform": platform,
            "class_name": connector_class.__name__,
            "module": connector_class.__module__,
            "description": connector_class.__doc__ or "No description available"
        }


# Generic connector for unsupported platforms
class GenericCICDConnector(BaseCICDConnector):
    """Generic connector for unsupported or custom CI/CD platforms"""
    
    async def authenticate(self) -> bool:
        """Generic authentication - always returns True"""
        self._authenticated = True
        return True
    
    async def test_connection(self) -> Dict[str, any]:
        """Generic connection test"""
        return {
            "connected": True,
            "platform": "generic",
            "message": "Generic connector - limited functionality"
        }
    
    async def create_pipeline(self, pipeline_definition: Dict[str, any]) -> str:
        """Generic pipeline creation - returns mock ID"""
        return f"generic-pipeline-{hash(str(pipeline_definition))}"
    
    async def update_pipeline(self, pipeline_id: str, 
                            pipeline_definition: Dict[str, any]) -> bool:
        """Generic pipeline update - always returns True"""
        return True
    
    async def delete_pipeline(self, pipeline_id: str) -> bool:
        """Generic pipeline deletion - always returns True"""
        return True
    
    async def trigger_pipeline(self, pipeline_id: str, 
                             parameters: Dict[str, any] = None) -> str:
        """Generic pipeline trigger - returns mock run ID"""
        return f"generic-run-{hash(pipeline_id + str(parameters or {}))}"
    
    async def get_pipeline_status(self, pipeline_id: str, run_id: str):
        """Generic status check - returns mock status"""
        from ...models.pipeline import PipelineRun, PipelineEventType
        from datetime import datetime
        
        return PipelineRun(
            id=run_id,
            pipeline_id=pipeline_id,
            run_number=1,
            status=PipelineEventType.COMPLETED,
            branch="main",
            commit_sha="generic-commit",
            commit_message="Generic commit message",
            triggered_by="generic-user",
            started_at=datetime.utcnow()
        )
    
    async def get_pipeline_runs(self, pipeline_id: str, limit: int = 50):
        """Generic runs list - returns empty list"""
        return []
    
    async def get_pipeline_logs(self, pipeline_id: str, run_id: str) -> str:
        """Generic logs - returns placeholder"""
        return f"Generic logs for pipeline {pipeline_id}, run {run_id}"
    
    async def cancel_pipeline_run(self, pipeline_id: str, run_id: str) -> bool:
        """Generic cancellation - always returns True"""
        return True
    
    async def get_pipeline_metrics(self, pipeline_id: str, days: int = 30):
        """Generic metrics - returns empty metrics"""
        from ...models.pipeline import PipelineMetrics
        return PipelineMetrics()


# Register the generic connector as fallback
CICDConnectorFactory.register_connector(PlatformType.GENERIC, GenericCICDConnector)