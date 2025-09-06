import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from kirolinter.devops.integrations.cicd.gitlab_ci import (
    GitLabCIConnector,
    GitLabPipelineStatus,
    GitLabJobStatus,
    GitLabPipelineInfo,
    GitLabJobInfo,
    GitLabProjectInfo,
    GitLabCIQualityGateIntegration
)
from kirolinter.devops.integrations.cicd.base_connector import (
    BaseCICDConnector,
    PlatformType,
    WorkflowStatus,
    UniversalWorkflowInfo,
    TriggerResult
)


class TestGitLabCIConnector:
    """Test suite for GitLabCIConnector."""

    def test_initialization(self):
        """Test GitLab CI connector initialization."""
        connector = GitLabCIConnector(
            gitlab_token="test-token",
            gitlab_url="https://gitlab.example.com",
            webhook_token="webhook-secret"
        )
        
        assert connector.gitlab_token == "test-token"
        assert connector.gitlab_url == "https://gitlab.example.com"
        assert connector.webhook_token == "webhook-secret"
        assert connector.api_url == "https://gitlab.example.com/api/v4"
        assert connector.platform_type == PlatformType.GITLAB_CI
        assert isinstance(connector, BaseCICDConnector)

    def test_initialization_defaults(self):
        """Test GitLab CI connector initialization with defaults."""
        connector = GitLabCIConnector(gitlab_token="test-token")
        
        assert connector.gitlab_token == "test-token"
        assert connector.gitlab_url == "https://gitlab.com"
        assert connector.webhook_token is None
        assert connector.api_url == "https://gitlab.com/api/v4"

    def test_gitlab_pipeline_status_enum(self):
        """Test GitLab pipeline status enum values."""
        assert GitLabPipelineStatus.CREATED.value == "created"
        assert GitLabPipelineStatus.WAITING_FOR_RESOURCE.value == "waiting_for_resource"
        assert GitLabPipelineStatus.PREPARING.value == "preparing"
        assert GitLabPipelineStatus.PENDING.value == "pending"
        assert GitLabPipelineStatus.RUNNING.value == "running"
        assert GitLabPipelineStatus.SUCCESS.value == "success"
        assert GitLabPipelineStatus.FAILED.value == "failed"
        assert GitLabPipelineStatus.CANCELED.value == "canceled"
        assert GitLabPipelineStatus.SKIPPED.value == "skipped"
        assert GitLabPipelineStatus.MANUAL.value == "manual"
        assert GitLabPipelineStatus.SCHEDULED.value == "scheduled"

    def test_gitlab_job_status_enum(self):
        """Test GitLab job status enum values."""
        assert GitLabJobStatus.CREATED.value == "created"
        assert GitLabJobStatus.PENDING.value == "pending"
        assert GitLabJobStatus.RUNNING.value == "running"
        assert GitLabJobStatus.FAILED.value == "failed"
        assert GitLabJobStatus.SUCCESS.value == "success"
        assert GitLabJobStatus.CANCELED.value == "canceled"
        assert GitLabJobStatus.SKIPPED.value == "skipped"
        assert GitLabJobStatus.MANUAL.value == "manual"

    def test_status_mapping(self):
        """Test GitLab status to universal status mapping."""
        connector = GitLabCIConnector("test-token")
        
        # Test success status
        assert connector._map_gitlab_status_to_universal("success") == WorkflowStatus.SUCCESS
        
        # Test failed status
        assert connector._map_gitlab_status_to_universal("failed") == WorkflowStatus.FAILED
        
        # Test running status
        assert connector._map_gitlab_status_to_universal("running") == WorkflowStatus.RUNNING
        
        # Test queued statuses
        assert connector._map_gitlab_status_to_universal("created") == WorkflowStatus.QUEUED
        assert connector._map_gitlab_status_to_universal("pending") == WorkflowStatus.QUEUED
        assert connector._map_gitlab_status_to_universal("preparing") == WorkflowStatus.QUEUED
        assert connector._map_gitlab_status_to_universal("waiting_for_resource") == WorkflowStatus.QUEUED
        assert connector._map_gitlab_status_to_universal("manual") == WorkflowStatus.QUEUED
        assert connector._map_gitlab_status_to_universal("scheduled") == WorkflowStatus.QUEUED
        
        # Test cancelled statuses
        assert connector._map_gitlab_status_to_universal("canceled") == WorkflowStatus.CANCELLED
        assert connector._map_gitlab_status_to_universal("cancelled") == WorkflowStatus.CANCELLED
        
        # Test skipped status
        assert connector._map_gitlab_status_to_universal("skipped") == WorkflowStatus.SKIPPED
        
        # Test unknown status
        assert connector._map_gitlab_status_to_universal("unknown_status") == WorkflowStatus.UNKNOWN

    def test_data_classes(self):
        """Test data class creation."""
        # Test GitLabProjectInfo
        project = GitLabProjectInfo(
            id=123,
            name="test-project",
            path="test-project",
            path_with_namespace="group/test-project",
            web_url="https://gitlab.example.com/group/test-project",
            default_branch="main",
            visibility="private",
            archived=False,
            issues_enabled=True,
            merge_requests_enabled=True,
            wiki_enabled=True,
            jobs_enabled=True,
            snippets_enabled=True,
            container_registry_enabled=True
        )
        
        assert project.id == 123
        assert project.name == "test-project"
        assert project.path_with_namespace == "group/test-project"
        
        # Test GitLabPipelineInfo
        created_time = datetime.now(timezone.utc)
        pipeline = GitLabPipelineInfo(
            id=456,
            project_id=123,
            status=GitLabPipelineStatus.SUCCESS,
            ref="main",
            sha="abc123def456",
            before_sha="def456ghi789",
            tag=False,
            yaml_errors=None,
            user={"name": "Test User"},
            created_at=created_time,
            updated_at=created_time,
            started_at=created_time,
            finished_at=created_time,
            committed_at=created_time,
            duration=1800,
            queued_duration=60,
            coverage="85.5",
            web_url="https://gitlab.example.com/pipeline/456"
        )
        
        assert pipeline.id == 456
        assert pipeline.status == GitLabPipelineStatus.SUCCESS
        assert pipeline.ref == "main"
        assert pipeline.duration == 1800
        
        # Test GitLabJobInfo
        job = GitLabJobInfo(
            id=789,
            status=GitLabJobStatus.SUCCESS,
            stage="test",
            name="unit-tests",
            ref="main",
            tag=False,
            coverage="90.0",
            allow_failure=False,
            created_at=created_time,
            started_at=created_time,
            finished_at=created_time,
            duration=780.5,
            queued_duration=60.0,
            web_url="https://gitlab.example.com/job/789",
            commit={"id": "abc123"},
            pipeline={"id": 456}
        )
        
        assert job.id == 789
        assert job.status == GitLabJobStatus.SUCCESS
        assert job.stage == "test"
        assert job.duration == 780.5

    @pytest.mark.asyncio
    async def test_async_methods_exist(self):
        """Test that async methods exist and are callable."""
        connector = GitLabCIConnector("test-token")
        
        # Verify methods exist
        assert hasattr(connector, 'discover_workflows')
        assert hasattr(connector, 'trigger_workflow') 
        assert hasattr(connector, 'get_workflow_status')
        assert hasattr(connector, 'cancel_workflow')
        assert hasattr(connector, 'get_connector_status')
        assert hasattr(connector, 'get_pipeline_jobs')
        assert hasattr(connector, 'get_job_logs')
        
        # These should be async methods
        assert asyncio.iscoroutinefunction(connector.discover_workflows)
        assert asyncio.iscoroutinefunction(connector.trigger_workflow)
        assert asyncio.iscoroutinefunction(connector.get_workflow_status)
        assert asyncio.iscoroutinefunction(connector.cancel_workflow)
        assert asyncio.iscoroutinefunction(connector.get_connector_status)
        assert asyncio.iscoroutinefunction(connector.get_pipeline_jobs)
        assert asyncio.iscoroutinefunction(connector.get_job_logs)

    def test_platform_type(self):
        """Test platform type is correctly set."""
        connector = GitLabCIConnector("test-token")
        
        assert connector.get_platform_type() == PlatformType.GITLAB_CI
        assert connector.platform_type == PlatformType.GITLAB_CI

    def test_inheritance(self):
        """Test that GitLabCIConnector inherits from BaseCICDConnector."""
        connector = GitLabCIConnector("test-token")
        
        assert isinstance(connector, BaseCICDConnector)
        assert connector.name == "gitlab_ci_connector"

    def test_callback_management(self):
        """Test status callback management."""
        connector = GitLabCIConnector("test-token")
        
        def test_callback(pipeline_info):
            pass
        
        # Initially no callbacks
        assert len(connector.status_callbacks) == 0
        
        # Add callback
        connector.add_status_callback(test_callback)
        assert len(connector.status_callbacks) == 1
        assert test_callback in connector.status_callbacks
        
        # Remove callback
        connector.remove_status_callback(test_callback)
        assert len(connector.status_callbacks) == 0
        assert test_callback not in connector.status_callbacks

    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test HTTP session management."""
        connector = GitLabCIConnector("test-token")
        
        # Initially no session
        assert connector.session is None
        
        # Ensure session creates one
        await connector._ensure_session()
        assert connector.session is not None
        
        # Close session
        await connector._close_session()
        assert connector.session is None

    def test_configuration_properties(self):
        """Test configuration and properties."""
        connector = GitLabCIConnector(
            gitlab_token="test-token",
            gitlab_url="https://custom.gitlab.com",
            webhook_token="webhook-secret"
        )
        
        assert connector.gitlab_token == "test-token"
        assert connector.gitlab_url == "https://custom.gitlab.com"
        assert connector.webhook_token == "webhook-secret"
        assert connector.api_url == "https://custom.gitlab.com/api/v4"
        
        # Test caches are initialized
        assert isinstance(connector.pipeline_cache, dict)
        assert isinstance(connector.job_cache, dict)
        assert isinstance(connector.project_cache, dict)
        assert isinstance(connector.status_callbacks, list)


class TestGitLabCIQualityGateIntegration:
    """Test suite for GitLabCIQualityGateIntegration."""

    def test_initialization(self):
        """Test quality gate integration initialization."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        assert integration.connector is connector
        assert hasattr(integration, 'logger')

    @pytest.mark.asyncio
    async def test_create_quality_gate_pipeline(self):
        """Test creating quality gate pipeline configuration."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        result = await integration.create_quality_gate_pipeline("group/test-project")
        
        # Since this is a mock implementation, it should always return True
        assert result is True

    @pytest.mark.asyncio
    async def test_check_quality_gate_with_mock_jobs(self):
        """Test checking quality gate status with mocked jobs."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        # Create mock jobs
        mock_quality_job = GitLabJobInfo(
            id=1, status=GitLabJobStatus.SUCCESS, stage="quality", name="kirolinter-check",
            ref="main", tag=False, coverage=None, allow_failure=False,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            duration=120.0, queued_duration=10.0, web_url="https://example.com/job/1",
            commit={}, pipeline={}
        )
        
        mock_test_job = GitLabJobInfo(
            id=2, status=GitLabJobStatus.SUCCESS, stage="test", name="unit-tests",
            ref="main", tag=False, coverage="90.0", allow_failure=False,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            duration=300.0, queued_duration=15.0, web_url="https://example.com/job/2",
            commit={}, pipeline={}
        )
        
        # Mock the connector's get_pipeline_jobs method
        connector.get_pipeline_jobs = AsyncMock(return_value=[mock_quality_job, mock_test_job])
        
        result = await integration.check_quality_gate("group/test-project", "456")
        
        assert result["passed"] is True
        assert result["total_jobs"] == 1  # Only quality jobs are counted
        assert result["passed_jobs"] == 1
        assert result["failed_jobs"] == 0
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["name"] == "kirolinter-check"
        assert result["jobs"][0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_check_quality_gate_no_quality_jobs(self):
        """Test checking quality gate when no quality jobs exist."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        # Create mock jobs without quality jobs
        mock_test_job = GitLabJobInfo(
            id=2, status=GitLabJobStatus.SUCCESS, stage="test", name="unit-tests",
            ref="main", tag=False, coverage="90.0", allow_failure=False,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            duration=300.0, queued_duration=15.0, web_url="https://example.com/job/2",
            commit={}, pipeline={}
        )
        
        # Mock the connector's get_pipeline_jobs method
        connector.get_pipeline_jobs = AsyncMock(return_value=[mock_test_job])
        
        result = await integration.check_quality_gate("group/test-project", "456")
        
        assert result["passed"] is False
        assert result["reason"] == "No quality gate jobs found"
        assert result["jobs_checked"] == 0

    @pytest.mark.asyncio
    async def test_check_quality_gate_with_failed_job(self):
        """Test checking quality gate with failed quality job."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        # Create mock jobs with a failed quality job
        mock_failed_quality_job = GitLabJobInfo(
            id=1, status=GitLabJobStatus.FAILED, stage="quality", name="quality-gate",
            ref="main", tag=False, coverage=None, allow_failure=False,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            duration=60.0, queued_duration=5.0, web_url="https://example.com/job/1",
            commit={}, pipeline={}
        )
        
        mock_success_quality_job = GitLabJobInfo(
            id=3, status=GitLabJobStatus.SUCCESS, stage="quality", name="kirolinter-scan",
            ref="main", tag=False, coverage=None, allow_failure=False,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            duration=90.0, queued_duration=8.0, web_url="https://example.com/job/3",
            commit={}, pipeline={}
        )
        
        # Mock the connector's get_pipeline_jobs method
        connector.get_pipeline_jobs = AsyncMock(return_value=[mock_failed_quality_job, mock_success_quality_job])
        
        result = await integration.check_quality_gate("group/test-project", "456")
        
        assert result["passed"] is False  # Not all quality jobs passed
        assert result["total_jobs"] == 2
        assert result["passed_jobs"] == 1
        assert result["failed_jobs"] == 1
        assert len(result["jobs"]) == 2

    def test_async_methods_exist(self):
        """Test that async methods exist in quality gate integration."""
        connector = GitLabCIConnector("test-token")
        integration = GitLabCIQualityGateIntegration(connector)
        
        assert hasattr(integration, 'create_quality_gate_pipeline')
        assert hasattr(integration, 'check_quality_gate')
        
        assert asyncio.iscoroutinefunction(integration.create_quality_gate_pipeline)
        assert asyncio.iscoroutinefunction(integration.check_quality_gate)


if __name__ == "__main__":
    pytest.main([__file__])