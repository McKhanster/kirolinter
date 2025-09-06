import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from kirolinter.devops.orchestration.universal_pipeline_manager import (
    UniversalPipelineManager,
    PipelineRegistry,
    CrossPlatformCoordinator,
    PipelineRegistryEntry,
    CrossPlatformOperation,
    PipelineCoordinationRule,
    PipelineOperationStatus
)
from kirolinter.devops.integrations.cicd.base_connector import (
    PlatformType,
    WorkflowStatus,
    UniversalWorkflowInfo,
    TriggerResult
)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.hset = AsyncMock(return_value=True)
    redis.sadd = AsyncMock(return_value=True)
    redis.hget = AsyncMock(return_value=None)
    return redis


@pytest.fixture
def pipeline_registry(mock_redis):
    """Create pipeline registry for testing"""
    return PipelineRegistry(mock_redis)


@pytest.fixture
def cross_platform_coordinator(pipeline_registry):
    """Create cross-platform coordinator for testing"""
    return CrossPlatformCoordinator(pipeline_registry)


@pytest.fixture
def universal_manager(mock_redis):
    """Create universal pipeline manager for testing"""
    return UniversalPipelineManager(mock_redis)


@pytest.fixture
def sample_workflow():
    """Create sample workflow info"""
    return UniversalWorkflowInfo(
        id="123",
        name="Test Workflow",
        platform=PlatformType.GITHUB_ACTIONS,
        status=WorkflowStatus.SUCCESS,
        repository="test/repo",
        branch="main",
        commit_sha="abc123",
        url="https://github.com/test/repo/actions/workflows/123",
        created_at="2023-12-01T10:00:00Z",
        updated_at="2023-12-01T12:00:00Z",
        metadata={"duration": 300}
    )


@pytest.fixture
def sample_registry_entry():
    """Create sample pipeline registry entry"""
    return PipelineRegistryEntry(
        pipeline_id="github:test/repo:123",
        platform=PlatformType.GITHUB_ACTIONS,
        repository="test/repo",
        workflow_id="123",
        name="Test Workflow",
        status=WorkflowStatus.SUCCESS,
        success_rate=85.0,
        avg_duration=300.0
    )


class TestPipelineRegistry:
    """Test suite for PipelineRegistry"""

    @pytest.mark.asyncio
    async def test_register_pipeline(self, pipeline_registry, sample_registry_entry):
        """Test pipeline registration"""
        result = await pipeline_registry.register_pipeline(sample_registry_entry)
        
        assert result is True
        assert sample_registry_entry.pipeline_id in pipeline_registry.pipelines
        assert PlatformType.GITHUB_ACTIONS in pipeline_registry.platform_mappings
        assert sample_registry_entry.pipeline_id in pipeline_registry.platform_mappings[PlatformType.GITHUB_ACTIONS]

    @pytest.mark.asyncio
    async def test_get_pipeline(self, pipeline_registry, sample_registry_entry):
        """Test getting pipeline by ID"""
        await pipeline_registry.register_pipeline(sample_registry_entry)
        
        retrieved = await pipeline_registry.get_pipeline(sample_registry_entry.pipeline_id)
        
        assert retrieved is not None
        assert retrieved.pipeline_id == sample_registry_entry.pipeline_id
        assert retrieved.name == sample_registry_entry.name

    @pytest.mark.asyncio
    async def test_get_pipelines_by_platform(self, pipeline_registry, sample_registry_entry):
        """Test getting pipelines by platform"""
        await pipeline_registry.register_pipeline(sample_registry_entry)
        
        pipelines = await pipeline_registry.get_pipelines_by_platform(PlatformType.GITHUB_ACTIONS)
        
        assert len(pipelines) == 1
        assert pipelines[0].pipeline_id == sample_registry_entry.pipeline_id

    @pytest.mark.asyncio
    async def test_get_pipelines_by_repository(self, pipeline_registry, sample_registry_entry):
        """Test getting pipelines by repository"""
        await pipeline_registry.register_pipeline(sample_registry_entry)
        
        pipelines = await pipeline_registry.get_pipelines_by_repository("test/repo")
        
        assert len(pipelines) == 1
        assert pipelines[0].repository == "test/repo"

    @pytest.mark.asyncio
    async def test_update_pipeline_stats(self, pipeline_registry, sample_registry_entry):
        """Test updating pipeline statistics"""
        await pipeline_registry.register_pipeline(sample_registry_entry)
        
        new_success_rate = 90.0
        new_avg_duration = 250.0
        last_run = datetime.now(timezone.utc)
        
        result = await pipeline_registry.update_pipeline_stats(
            sample_registry_entry.pipeline_id,
            new_success_rate,
            new_avg_duration,
            last_run
        )
        
        assert result is True
        
        updated_pipeline = await pipeline_registry.get_pipeline(sample_registry_entry.pipeline_id)
        assert updated_pipeline.success_rate == new_success_rate
        assert updated_pipeline.avg_duration == new_avg_duration
        assert updated_pipeline.last_run == last_run


class TestCrossPlatformCoordinator:
    """Test suite for CrossPlatformCoordinator"""

    @pytest.mark.asyncio
    async def test_add_coordination_rule(self, cross_platform_coordinator):
        """Test adding coordination rule"""
        rule = PipelineCoordinationRule(
            rule_id="test_rule",
            name="Test Rule",
            condition='{"type": "platform_count", "min_platforms": 2}',
            action='{"type": "delay", "seconds": 5}',
            platforms=[PlatformType.GITHUB_ACTIONS, PlatformType.GITLAB_CI]
        )
        
        result = await cross_platform_coordinator.add_coordination_rule(rule)
        
        assert result is True
        assert rule.rule_id in cross_platform_coordinator.coordination_rules

    @pytest.mark.asyncio
    async def test_coordinate_cross_platform_operation(self, cross_platform_coordinator):
        """Test coordinating cross-platform operation"""
        platforms = [PlatformType.GITHUB_ACTIONS, PlatformType.GITLAB_CI]
        
        operation = await cross_platform_coordinator.coordinate_cross_platform_operation(
            operation_type="test_operation",
            platforms=platforms,
            repository="test/repo"
        )
        
        assert isinstance(operation, CrossPlatformOperation)
        assert operation.operation_type == "test_operation"
        assert operation.platforms == platforms
        assert operation.status in [PipelineOperationStatus.SUCCESS, PipelineOperationStatus.FAILED]

    @pytest.mark.asyncio
    async def test_resource_conflict_detection(self, cross_platform_coordinator):
        """Test resource conflict detection"""
        # Start first operation
        operation1 = await cross_platform_coordinator.coordinate_cross_platform_operation(
            operation_type="operation1",
            platforms=[PlatformType.GITHUB_ACTIONS],
            repository="test/repo"
        )
        
        # Reserve resources manually for testing
        await cross_platform_coordinator._reserve_resources(
            "test_op", "test/repo", [PlatformType.GITHUB_ACTIONS]
        )
        
        # Check for conflicts
        conflicts = await cross_platform_coordinator._check_resource_conflicts(
            "test/repo", [PlatformType.GITHUB_ACTIONS]
        )
        
        assert len(conflicts) > 0
        assert "github_actions platform busy" in conflicts[0]


class TestUniversalPipelineManager:
    """Test suite for UniversalPipelineManager"""

    def test_initialization(self, universal_manager):
        """Test universal pipeline manager initialization"""
        assert universal_manager.connectors == {}
        assert universal_manager.active_connections == {}
        assert isinstance(universal_manager.pipeline_registry, PipelineRegistry)
        assert isinstance(universal_manager.coordinator, CrossPlatformCoordinator)

    def test_register_github_connector(self, universal_manager):
        """Test registering GitHub connector"""
        with patch('kirolinter.devops.orchestration.universal_pipeline_manager.GitHubActionsConnector') as mock_github:
            result = universal_manager.register_github_connector("test-token", "webhook-secret")
            
            assert result is True
            mock_github.assert_called_once_with("test-token", "webhook-secret")
            assert PlatformType.GITHUB_ACTIONS in universal_manager.connectors

    def test_register_gitlab_connector(self, universal_manager):
        """Test registering GitLab connector"""
        with patch('kirolinter.devops.orchestration.universal_pipeline_manager.GitLabCIConnector') as mock_gitlab:
            result = universal_manager.register_gitlab_connector(
                "test-token", "https://gitlab.example.com", "webhook-token"
            )
            
            assert result is True
            mock_gitlab.assert_called_once_with("test-token", "https://gitlab.example.com", "webhook-token")
            assert PlatformType.GITLAB_CI in universal_manager.connectors

    @pytest.mark.asyncio
    async def test_test_connections(self, universal_manager):
        """Test testing connections to all platforms"""
        # Mock connectors
        github_connector = AsyncMock()
        github_connector.get_connector_status.return_value = {"status": "healthy"}
        
        gitlab_connector = AsyncMock()
        gitlab_connector.get_connector_status.return_value = {"status": "unhealthy", "error": "Connection failed"}
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        
        results = await universal_manager.test_connections()
        
        assert results[PlatformType.GITHUB_ACTIONS] is True
        assert results[PlatformType.GITLAB_CI] is False
        assert universal_manager.active_connections[PlatformType.GITHUB_ACTIONS] is True
        assert universal_manager.active_connections[PlatformType.GITLAB_CI] is False

    @pytest.mark.asyncio
    async def test_discover_all_workflows(self, universal_manager, sample_workflow):
        """Test discovering workflows across all platforms"""
        # Mock connectors
        github_connector = AsyncMock()
        github_connector.discover_workflows.return_value = [sample_workflow]
        
        gitlab_connector = AsyncMock()
        gitlab_connector.discover_workflows.return_value = []
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        universal_manager.active_connections = {
            PlatformType.GITHUB_ACTIONS: True,
            PlatformType.GITLAB_CI: True
        }
        
        results = await universal_manager.discover_all_workflows("test/repo")
        
        assert PlatformType.GITHUB_ACTIONS in results
        assert PlatformType.GITLAB_CI in results
        assert len(results[PlatformType.GITHUB_ACTIONS]) == 1
        assert len(results[PlatformType.GITLAB_CI]) == 0

    @pytest.mark.asyncio
    async def test_trigger_cross_platform_workflows(self, universal_manager):
        """Test triggering workflows across platforms"""
        # Mock connectors
        github_connector = AsyncMock()
        github_connector.trigger_workflow.return_value = TriggerResult(
            success=True, workflow_id="123", run_id="456", url="https://github.com/test"
        )
        
        gitlab_connector = AsyncMock()
        gitlab_connector.trigger_workflow.return_value = TriggerResult(
            success=True, workflow_id="789", run_id="101", url="https://gitlab.com/test"
        )
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        universal_manager.active_connections = {
            PlatformType.GITHUB_ACTIONS: True,
            PlatformType.GITLAB_CI: True
        }
        
        # Add some test pipelines to registry
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="github:test/repo:123",
                platform=PlatformType.GITHUB_ACTIONS,
                repository="test/repo",
                workflow_id="123",
                name="GitHub Workflow",
                status=WorkflowStatus.SUCCESS
            )
        )
        
        operation = await universal_manager.trigger_cross_platform_workflows(
            repository="test/repo",
            platforms=[PlatformType.GITHUB_ACTIONS, PlatformType.GITLAB_CI],
            branch="main",
            inputs={"test": "value"}
        )
        
        assert isinstance(operation, CrossPlatformOperation)
        assert operation.operation_type == "trigger_workflows"
        assert len(operation.platforms) == 2

    @pytest.mark.asyncio
    async def test_get_unified_status(self, universal_manager):
        """Test getting unified status across platforms"""
        # Add mock connectors
        github_connector = AsyncMock()
        gitlab_connector = AsyncMock()
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        universal_manager.active_connections = {
            PlatformType.GITHUB_ACTIONS: True,
            PlatformType.GITLAB_CI: True
        }
        
        # Add test pipelines
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="github:test/repo:123",
                platform=PlatformType.GITHUB_ACTIONS,
                repository="test/repo",
                workflow_id="123",
                name="GitHub Workflow",
                status=WorkflowStatus.SUCCESS
            )
        )
        
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="gitlab:test/repo:456",
                platform=PlatformType.GITLAB_CI,
                repository="test/repo",
                workflow_id="456",
                name="GitLab Pipeline",
                status=WorkflowStatus.RUNNING
            )
        )
        
        status = await universal_manager.get_unified_status("test/repo")
        
        assert status["repository"] == "test/repo"
        assert "platforms" in status
        assert "summary" in status
        assert status["summary"]["total_pipelines"] == 2
        assert status["summary"]["running_pipelines"] == 1

    @pytest.mark.asyncio
    async def test_get_cross_platform_analytics(self, universal_manager):
        """Test getting cross-platform analytics"""
        # Add mock connectors
        github_connector = AsyncMock()
        gitlab_connector = AsyncMock()
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        universal_manager.active_connections = {
            PlatformType.GITHUB_ACTIONS: True,
            PlatformType.GITLAB_CI: True
        }
        
        # Add test pipelines with stats
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="github:test/repo:123",
                platform=PlatformType.GITHUB_ACTIONS,
                repository="test/repo",
                workflow_id="123",
                name="GitHub Workflow",
                status=WorkflowStatus.SUCCESS,
                success_rate=90.0,
                avg_duration=300.0
            )
        )
        
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="gitlab:test/repo:456",
                platform=PlatformType.GITLAB_CI,
                repository="test/repo",
                workflow_id="456",
                name="GitLab Pipeline",
                status=WorkflowStatus.SUCCESS,
                success_rate=85.0,
                avg_duration=250.0
            )
        )
        
        analytics = await universal_manager.get_cross_platform_analytics("test/repo")
        
        assert "platforms" in analytics
        assert "summary" in analytics
        assert analytics["summary"]["total_executions"] == 2
        assert analytics["summary"]["average_success_rate"] > 0

    @pytest.mark.asyncio
    async def test_optimize_pipeline_execution(self, universal_manager):
        """Test pipeline execution optimization"""
        # Mock status and analytics
        universal_manager.get_unified_status = AsyncMock(return_value={
            'repository': 'test/repo',
            'summary': {
                'total_pipelines': 5,
                'success_rate': 75.0,  # Low success rate
                'running_pipelines': 1,
                'failed_pipelines': 1
            }
        })
        
        universal_manager.get_cross_platform_analytics = AsyncMock(return_value={
            'summary': {
                'average_duration': 900.0,  # 15 minutes - high duration
                'total_executions': 5
            },
            'platforms': {
                'github_actions': {'pipelines': 4},
                'gitlab_ci': {'pipelines': 1}
            }
        })
        
        optimization = await universal_manager.optimize_pipeline_execution("test/repo")
        
        assert "recommendations" in optimization
        assert len(optimization["recommendations"]) > 0
        
        # Should have recommendations for low success rate and high duration
        recommendation_types = [r["type"] for r in optimization["recommendations"]]
        assert "success_rate" in recommendation_types
        assert "duration" in recommendation_types

    @pytest.mark.asyncio
    async def test_cancel_cross_platform_workflows(self, universal_manager):
        """Test canceling workflows across platforms"""
        # Mock connectors
        github_connector = AsyncMock()
        github_connector.cancel_workflow.return_value = True
        
        gitlab_connector = AsyncMock()
        gitlab_connector.cancel_workflow.return_value = True
        
        universal_manager.connectors = {
            PlatformType.GITHUB_ACTIONS: github_connector,
            PlatformType.GITLAB_CI: gitlab_connector
        }
        universal_manager.active_connections = {
            PlatformType.GITHUB_ACTIONS: True,
            PlatformType.GITLAB_CI: True
        }
        
        # Add running pipelines
        await universal_manager.pipeline_registry.register_pipeline(
            PipelineRegistryEntry(
                pipeline_id="github:test/repo:123",
                platform=PlatformType.GITHUB_ACTIONS,
                repository="test/repo",
                workflow_id="123",
                name="Running Workflow",
                status=WorkflowStatus.RUNNING
            )
        )
        
        operation = await universal_manager.cancel_cross_platform_workflows(
            repository="test/repo",
            platforms=[PlatformType.GITHUB_ACTIONS, PlatformType.GITLAB_CI]
        )
        
        assert isinstance(operation, CrossPlatformOperation)
        assert operation.operation_type == "cancel_workflows"


if __name__ == "__main__":
    pytest.main([__file__])