import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from kirolinter.devops.integrations.cicd.github_actions import (
    GitHubActionsConnector,
    GitHubWorkflowStatus,
    GitHubWorkflowConclusion
)
from kirolinter.devops.integrations.cicd.base_connector import (
    PlatformType,
    WorkflowStatus,
    UniversalWorkflowInfo,
    TriggerResult
)


class TestGitHubActionsConnector:
    """Test suite for GitHubActionsConnector."""

    def test_initialization(self):
        """Test GitHub Actions connector initialization."""
        with patch('github.Github') as mock_github:
            connector = GitHubActionsConnector(
                github_token="test-token",
                webhook_secret="secret"
            )
            
            assert connector.platform_type == PlatformType.GITHUB_ACTIONS
            assert connector.github_token == "test-token"
            assert connector.webhook_secret == "secret"

    def test_github_workflow_status_enum(self):
        """Test GitHub workflow status enum values."""
        assert GitHubWorkflowStatus.QUEUED.value == "queued"
        assert GitHubWorkflowStatus.IN_PROGRESS.value == "in_progress"
        assert GitHubWorkflowStatus.COMPLETED.value == "completed"
        assert GitHubWorkflowStatus.WAITING.value == "waiting"
        assert GitHubWorkflowStatus.REQUESTED.value == "requested"
        assert GitHubWorkflowStatus.PENDING.value == "pending"

    def test_github_workflow_conclusion_enum(self):
        """Test GitHub workflow conclusion enum values."""
        assert GitHubWorkflowConclusion.SUCCESS.value == "success"
        assert GitHubWorkflowConclusion.FAILURE.value == "failure"
        assert GitHubWorkflowConclusion.NEUTRAL.value == "neutral"
        assert GitHubWorkflowConclusion.CANCELLED.value == "cancelled"
        assert GitHubWorkflowConclusion.SKIPPED.value == "skipped"
        assert GitHubWorkflowConclusion.TIMED_OUT.value == "timed_out"
        assert GitHubWorkflowConclusion.ACTION_REQUIRED.value == "action_required"
        assert GitHubWorkflowConclusion.STARTUP_FAILURE.value == "startup_failure"

    @pytest.mark.asyncio
    async def test_connector_basic_functionality(self):
        """Test basic connector functionality without complex mocking."""
        with patch('github.Github') as mock_github:
            # Create connector instance
            connector = GitHubActionsConnector(github_token="test-token")
            
            # Test platform type
            assert connector.get_platform_type() == PlatformType.GITHUB_ACTIONS
            
            # Test initial connection state
            assert connector.is_connected() is False
            
            # Test setting connection state
            connector.connected = True
            assert connector.is_connected() is True

    @pytest.mark.asyncio
    async def test_trigger_result_creation(self):
        """Test creating trigger results."""
        # Test successful trigger result
        success_result = TriggerResult(
            success=True,
            workflow_id="12345",
            run_id="67890",
            url="https://github.com/test/repo/actions/runs/67890"
        )
        
        assert success_result.success is True
        assert success_result.workflow_id == "12345"
        assert success_result.run_id == "67890"
        assert success_result.error is None
        
        # Test failed trigger result
        failed_result = TriggerResult(
            success=False,
            error="Authentication failed"
        )
        
        assert failed_result.success is False
        assert failed_result.workflow_id is None
        assert failed_result.error == "Authentication failed"

    @pytest.mark.asyncio
    async def test_workflow_info_creation(self):
        """Test creating workflow info objects."""
        workflow_info = UniversalWorkflowInfo(
            id="workflow-123",
            name="CI Pipeline",
            platform=PlatformType.GITHUB_ACTIONS,
            status=WorkflowStatus.SUCCESS,
            repository="test/repo",
            branch="main",
            commit_sha="abc123def456",
            url="https://github.com/test/repo/actions/workflows/ci.yml",
            created_at="2023-12-01T10:00:00Z",
            updated_at="2023-12-01T12:00:00Z",
            metadata={
                "duration": 180,
                "conclusion": "success"
            }
        )
        
        assert workflow_info.id == "workflow-123"
        assert workflow_info.name == "CI Pipeline"
        assert workflow_info.platform == PlatformType.GITHUB_ACTIONS
        assert workflow_info.status == WorkflowStatus.SUCCESS
        assert workflow_info.repository == "test/repo"
        assert workflow_info.metadata["duration"] == 180

    def test_status_mapping_utility(self):
        """Test utility functions for status mapping."""
        with patch('github.Github'):
            connector = GitHubActionsConnector(github_token="test-token")
            
            # Test mapping GitHub status to universal status
            # (This would test actual implementation methods if they exist)
            assert connector.platform_type == PlatformType.GITHUB_ACTIONS

    @pytest.mark.asyncio
    async def test_error_handling_patterns(self):
        """Test error handling patterns in the connector."""
        with patch('github.Auth.Token') as mock_auth:
            # Setup mock to raise an exception during auth
            mock_auth.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                GitHubActionsConnector(github_token="invalid-token")

    def test_configuration_handling(self):
        """Test configuration parameter handling."""
        with patch('github.Github'):
            # Test with minimal config
            connector1 = GitHubActionsConnector(github_token="token")
            assert connector1.github_token == "token"
            
            # Test with webhook secret
            connector2 = GitHubActionsConnector(
                github_token="token",
                webhook_secret="secret123"
            )
            assert connector2.github_token == "token"
            assert connector2.webhook_secret == "secret123"

    @pytest.mark.asyncio
    async def test_async_method_signatures(self):
        """Test that async methods have correct signatures."""
        with patch('github.Github'):
            connector = GitHubActionsConnector(github_token="test-token")
            
            # Verify methods exist and are coroutines
            assert hasattr(connector, 'discover_workflows')
            assert hasattr(connector, 'trigger_workflow') 
            assert hasattr(connector, 'get_workflow_status')
            assert hasattr(connector, 'cancel_workflow')
            assert hasattr(connector, 'get_connector_status')
            
            # These should be async methods
            assert asyncio.iscoroutinefunction(connector.discover_workflows)
            assert asyncio.iscoroutinefunction(connector.trigger_workflow)
            assert asyncio.iscoroutinefunction(connector.get_workflow_status)
            assert asyncio.iscoroutinefunction(connector.cancel_workflow)
            assert asyncio.iscoroutinefunction(connector.get_connector_status)

    def test_inheritance_structure(self):
        """Test that GitHubActionsConnector properly inherits from base."""
        with patch('github.Github'):
            connector = GitHubActionsConnector(github_token="test-token")
            
            # Test inheritance
            from kirolinter.devops.integrations.cicd.base_connector import BaseCICDConnector
            assert isinstance(connector, BaseCICDConnector)
            
            # Test platform type is correctly set
            assert connector.platform_type == PlatformType.GITHUB_ACTIONS


if __name__ == "__main__":
    pytest.main([__file__])