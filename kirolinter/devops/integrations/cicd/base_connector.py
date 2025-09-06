"""
Base CI/CD Platform Connector

Abstract base class for all CI/CD platform integrations, providing
a consistent interface for workflow management, triggering, and monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


class PlatformType(Enum):
    """Supported CI/CD platform types"""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"
    GENERIC = "generic"


class WorkflowStatus(Enum):
    """Universal workflow status"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class UniversalWorkflowInfo:
    """Universal workflow information"""
    id: Union[int, str]
    name: str
    platform: PlatformType
    status: WorkflowStatus
    repository: str
    branch: str
    commit_sha: str
    url: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


@dataclass
class TriggerResult:
    """Result of triggering a workflow"""
    success: bool
    workflow_id: Optional[Union[int, str]] = None
    run_id: Optional[Union[int, str]] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseCICDConnector(ABC):
    """Base class for CI/CD platform connectors"""
    
    def __init__(self, platform_type: Union[str, PlatformType]):
        """Initialize the connector"""
        if isinstance(platform_type, str):
            self.platform_type = PlatformType(platform_type)
        else:
            self.platform_type = platform_type
        
        self.name = f"{self.platform_type.value}_connector"
        self.connected = False
    
    @abstractmethod
    async def discover_workflows(self, repository: str, **kwargs) -> List[UniversalWorkflowInfo]:
        """Discover workflows in a repository"""
        pass
    
    @abstractmethod
    async def trigger_workflow(self, repository: str, workflow_id: Union[int, str], 
                              branch: str = "main", inputs: Optional[Dict[str, Any]] = None) -> TriggerResult:
        """Trigger a workflow"""
        pass
    
    @abstractmethod
    async def get_workflow_status(self, repository: str, workflow_id: Union[int, str], 
                                run_id: Optional[Union[int, str]] = None) -> UniversalWorkflowInfo:
        """Get workflow status"""
        pass
    
    @abstractmethod
    async def cancel_workflow(self, repository: str, run_id: Union[int, str]) -> bool:
        """Cancel a running workflow"""
        pass
    
    @abstractmethod
    async def get_connector_status(self) -> Dict[str, Any]:
        """Get connector status and health information"""
        pass
    
    def get_platform_type(self) -> PlatformType:
        """Get the platform type"""
        return self.platform_type
    
    def is_connected(self) -> bool:
        """Check if the connector is connected"""
        return self.connected