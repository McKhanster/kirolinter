import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any

from kirolinter.devops.integrations.cicd.base_connector import (
    BaseCICDConnector,
    UniversalWorkflowInfo,
    TriggerResult,
    PlatformType,
    WorkflowStatus
)


class TestUniversalWorkflowInfo:
    """Test suite for UniversalWorkflowInfo."""

    def test_initialization(self):
        """Test workflow info initialization."""
        workflow = UniversalWorkflowInfo(
            id="12345",
            name="CI Pipeline",
            platform=PlatformType.GITHUB_ACTIONS,
            status=WorkflowStatus.SUCCESS,
            repository="test/repo",
            branch="main",
            commit_sha="abc123def456",
            url="https://github.com/test/repo/actions/workflows/ci.yml",
            created_at="2023-12-01T10:00:00Z",
            updated_at="2023-12-01T12:00:00Z",
            metadata={"duration": 180}
        )
        
        assert workflow.id == "12345"
        assert workflow.name == "CI Pipeline"
        assert workflow.platform == PlatformType.GITHUB_ACTIONS
        assert workflow.status == WorkflowStatus.SUCCESS
        assert workflow.repository == "test/repo"
        assert workflow.branch == "main"
        assert workflow.commit_sha == "abc123def456"
        assert workflow.metadata["duration"] == 180


class TestTriggerResult:
    """Test suite for TriggerResult."""

    def test_initialization_success(self):
        """Test successful trigger result initialization."""
        result = TriggerResult(
            success=True,
            workflow_id="12345",
            run_id="67890",
            url="https://github.com/test/repo/actions/runs/67890",
            metadata={"triggered_by": "user"}
        )
        
        assert result.success is True
        assert result.workflow_id == "12345"
        assert result.run_id == "67890"
        assert result.url == "https://github.com/test/repo/actions/runs/67890"
        assert result.error is None
        assert result.metadata["triggered_by"] == "user"

    def test_initialization_failure(self):
        """Test failed trigger result initialization."""
        result = TriggerResult(
            success=False,
            error="Authentication failed"
        )
        
        assert result.success is False
        assert result.workflow_id is None
        assert result.run_id is None
        assert result.url is None
        assert result.error == "Authentication failed"


class TestPlatformType:
    """Test suite for PlatformType enum."""

    def test_platform_types(self):
        """Test all platform type values."""
        assert PlatformType.GITHUB_ACTIONS.value == "github_actions"
        assert PlatformType.GITLAB_CI.value == "gitlab_ci"
        assert PlatformType.JENKINS.value == "jenkins"
        assert PlatformType.AZURE_DEVOPS.value == "azure_devops"
        assert PlatformType.CIRCLECI.value == "circleci"
        assert PlatformType.GENERIC.value == "generic"


class TestWorkflowStatus:
    """Test suite for WorkflowStatus enum."""

    def test_workflow_statuses(self):
        """Test all workflow status values."""
        assert WorkflowStatus.QUEUED.value == "queued"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.SUCCESS.value == "success"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
        assert WorkflowStatus.SKIPPED.value == "skipped"
        assert WorkflowStatus.TIMEOUT.value == "timeout"
        assert WorkflowStatus.UNKNOWN.value == "unknown"


class MockCICDConnector(BaseCICDConnector):
    """Mock implementation of BaseCICDConnector for testing."""
    
    def __init__(self):
        super().__init__(PlatformType.GENERIC)
        self.workflows = {}
        self.executions = {}
    
    async def discover_workflows(self, repository: str, **kwargs):
        """Mock workflow discovery."""
        return [
            UniversalWorkflowInfo(
                id="mock-1",
                name="Mock Workflow",
                platform=PlatformType.GENERIC,
                status=WorkflowStatus.SUCCESS,
                repository=repository,
                branch="main",
                commit_sha="abc123",
                url=f"https://mock.platform/{repository}/workflows/1",
                created_at="2023-12-01T10:00:00Z",
                updated_at="2023-12-01T12:00:00Z",
                metadata={}
            )
        ]
    
    async def trigger_workflow(self, repository: str, workflow_id: str, branch: str = "main", inputs: Dict[str, Any] = None):
        """Mock workflow triggering."""
        return TriggerResult(
            success=True,
            workflow_id=workflow_id,
            run_id="run-123",
            url=f"https://mock.platform/{repository}/runs/123"
        )
    
    async def get_workflow_status(self, repository: str, workflow_id: str, run_id: str = None):
        """Mock status retrieval."""
        return UniversalWorkflowInfo(
            id=workflow_id,
            name="Mock Workflow",
            platform=PlatformType.GENERIC,
            status=WorkflowStatus.SUCCESS,
            repository=repository,
            branch="main",
            commit_sha="abc123",
            url=f"https://mock.platform/{repository}/workflows/{workflow_id}",
            created_at="2023-12-01T10:00:00Z",
            updated_at="2023-12-01T12:00:00Z",
            metadata={}
        )
    
    async def cancel_workflow(self, repository: str, run_id: str):
        """Mock workflow cancellation."""
        return True
    
    async def get_connector_status(self):
        """Mock connector status."""
        return {
            "status": "healthy",
            "platform": "Generic",
            "connected": True,
            "response_time": 0.1
        }


class TestBaseCICDConnector:
    """Test suite for BaseCICDConnector."""

    def test_initialization_with_enum(self):
        """Test connector initialization with enum."""
        connector = MockCICDConnector()
        
        assert connector.platform_type == PlatformType.GENERIC
        assert connector.name == "generic_connector"
        assert connector.connected is False

    def test_initialization_with_string(self):
        """Test connector initialization with string."""
        class StringConnector(BaseCICDConnector):
            def __init__(self):
                super().__init__("github_actions")
            
            async def discover_workflows(self, repository: str, **kwargs):
                return []
            
            async def trigger_workflow(self, repository: str, workflow_id: str, branch: str = "main", inputs: Dict[str, Any] = None):
                return TriggerResult(success=True)
            
            async def get_workflow_status(self, repository: str, workflow_id: str, run_id: str = None):
                return UniversalWorkflowInfo(
                    id="1", name="test", platform=PlatformType.GITHUB_ACTIONS,
                    status=WorkflowStatus.SUCCESS, repository="test/repo",
                    branch="main", commit_sha="abc", url="test", 
                    created_at="2023-12-01T10:00:00Z", updated_at="2023-12-01T12:00:00Z",
                    metadata={}
                )
            
            async def cancel_workflow(self, repository: str, run_id: str):
                return True
            
            async def get_connector_status(self):
                return {"status": "healthy"}
        
        connector = StringConnector()
        assert connector.platform_type == PlatformType.GITHUB_ACTIONS

    @pytest.mark.asyncio
    async def test_discover_workflows(self):
        """Test workflow discovery through base class."""
        connector = MockCICDConnector()
        
        workflows = await connector.discover_workflows("test/repo")
        
        assert len(workflows) == 1
        assert workflows[0].name == "Mock Workflow"
        assert workflows[0].platform == PlatformType.GENERIC
        assert workflows[0].repository == "test/repo"

    @pytest.mark.asyncio
    async def test_trigger_workflow(self):
        """Test workflow triggering through base class."""
        connector = MockCICDConnector()
        
        result = await connector.trigger_workflow("test/repo", "mock-1", "main")
        
        assert isinstance(result, TriggerResult)
        assert result.success is True
        assert result.workflow_id == "mock-1"
        assert result.run_id == "run-123"

    @pytest.mark.asyncio
    async def test_get_workflow_status(self):
        """Test status retrieval through base class."""
        connector = MockCICDConnector()
        
        status = await connector.get_workflow_status("test/repo", "mock-1")
        
        assert isinstance(status, UniversalWorkflowInfo)
        assert status.id == "mock-1"
        assert status.status == WorkflowStatus.SUCCESS
        assert status.platform == PlatformType.GENERIC

    @pytest.mark.asyncio
    async def test_cancel_workflow(self):
        """Test workflow cancellation through base class."""
        connector = MockCICDConnector()
        
        result = await connector.cancel_workflow("test/repo", "run-123")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_connector_status(self):
        """Test connector status through base class."""
        connector = MockCICDConnector()
        
        status = await connector.get_connector_status()
        
        assert status["status"] == "healthy"
        assert status["platform"] == "Generic"
        assert status["connected"] is True
        assert "response_time" in status

    def test_get_platform_type(self):
        """Test getting platform type."""
        connector = MockCICDConnector()
        
        platform_type = connector.get_platform_type()
        
        assert platform_type == PlatformType.GENERIC

    def test_is_connected(self):
        """Test connection status check."""
        connector = MockCICDConnector()
        
        # Initially not connected
        assert connector.is_connected() is False
        
        # Simulate connection
        connector.connected = True
        assert connector.is_connected() is True

    @pytest.mark.asyncio
    async def test_trigger_workflow_with_inputs(self):
        """Test workflow triggering with custom inputs."""
        connector = MockCICDConnector()
        
        inputs = {"environment": "staging", "version": "1.2.3"}
        result = await connector.trigger_workflow("test/repo", "mock-1", "develop", inputs)
        
        assert result.success is True
        assert result.workflow_id == "mock-1"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in connector methods."""
        class ErrorConnector(BaseCICDConnector):
            def __init__(self):
                super().__init__(PlatformType.GENERIC)
            
            async def discover_workflows(self, repository: str, **kwargs):
                raise Exception("API Error")
            
            async def trigger_workflow(self, repository: str, workflow_id: str, branch: str = "main", inputs: Dict[str, Any] = None):
                return TriggerResult(success=False, error="Trigger failed")
            
            async def get_workflow_status(self, repository: str, workflow_id: str, run_id: str = None):
                raise Exception("Status check failed")
            
            async def cancel_workflow(self, repository: str, run_id: str):
                return False
            
            async def get_connector_status(self):
                return {"status": "unhealthy", "error": "Connection failed"}
        
        connector = ErrorConnector()
        
        # Test discovery error
        with pytest.raises(Exception, match="API Error"):
            await connector.discover_workflows("test/repo")
        
        # Test trigger failure
        result = await connector.trigger_workflow("test/repo", "workflow-1")
        assert result.success is False
        assert result.error == "Trigger failed"
        
        # Test status check error  
        with pytest.raises(Exception, match="Status check failed"):
            await connector.get_workflow_status("test/repo", "workflow-1")
        
        # Test cancellation failure
        cancel_result = await connector.cancel_workflow("test/repo", "run-1")
        assert cancel_result is False
        
        # Test unhealthy status
        status = await connector.get_connector_status()
        assert status["status"] == "unhealthy"
        assert "error" in status


if __name__ == "__main__":
    pytest.main([__file__])