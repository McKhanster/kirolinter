"""
Tests for Workflow Orchestration Engine

Comprehensive tests for the core workflow orchestration functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from kirolinter.devops.orchestration.workflow_engine import WorkflowEngine, WorkflowDefinition
from kirolinter.devops.orchestration.workflow_graph import WorkflowGraph, WorkflowNode, NodeStatus
from kirolinter.devops.orchestration.resource_manager import ResourceManager, ResourceRequirement, ResourceType
from kirolinter.devops.orchestration.failure_handler import FailureHandler, FailureType, RecoveryStrategy
from kirolinter.devops.orchestration.execution_context import ExecutionContext, ExecutionStatus


class TestWorkflowEngine:
    """Test cases for WorkflowEngine"""
    
    @pytest.fixture
    def workflow_engine(self):
        """Create a workflow engine instance for testing"""
        return WorkflowEngine()
    
    @pytest.fixture
    def sample_workflow_definition(self):
        """Create a sample workflow definition for testing"""
        return WorkflowDefinition(
            id=str(uuid4()),
            name="Test Workflow",
            description="A test workflow for unit testing",
            version="1.0.0",
            nodes=[
                WorkflowNode(
                    id="node_1",
                    name="Code Analysis",
                    task_type="code_analysis",
                    dependencies=[],
                    parameters={"language": "python"},
                    timeout_seconds=300
                ),
                WorkflowNode(
                    id="node_2",
                    name="Quality Check",
                    task_type="quality_check",
                    dependencies=["node_1"],
                    parameters={"threshold": 80},
                    timeout_seconds=180
                ),
                WorkflowNode(
                    id="node_3",
                    name="Test Execution",
                    task_type="test_execution",
                    dependencies=["node_1"],
                    parameters={"test_suite": "unit"},
                    timeout_seconds=600
                ),
                WorkflowNode(
                    id="node_4",
                    name="Deployment",
                    task_type="deployment",
                    dependencies=["node_2", "node_3"],
                    parameters={"environment": "staging"},
                    timeout_seconds=900
                )
            ],
            dependencies=[
                ("node_1", "node_2"),
                ("node_1", "node_3"),
                ("node_2", "node_4"),
                ("node_3", "node_4")
            ],
            timeout_seconds=3600,
            max_parallel_nodes=3
        )
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_engine, sample_workflow_definition):
        """Test workflow creation"""
        workflow_id = await workflow_engine.create_workflow(sample_workflow_definition)
        
        assert workflow_id is not None
        assert workflow_id in workflow_engine.workflow_definitions
        assert workflow_id in workflow_engine.active_workflows
        
        # Verify workflow graph is created correctly
        graph = workflow_engine.active_workflows[workflow_id]
        assert len(graph.nodes) == 4
        assert "node_1" in graph.nodes
        assert "node_4" in graph.nodes
    
    @pytest.mark.asyncio
    async def test_workflow_validation(self, workflow_engine):
        """Test workflow validation with invalid definition"""
        # Test with circular dependency
        invalid_workflow = WorkflowDefinition(
            id=str(uuid4()),
            name="Invalid Workflow",
            description="Workflow with circular dependency",
            nodes=[
                WorkflowNode(id="node_1", name="Node 1", task_type="test", dependencies=["node_2"]),
                WorkflowNode(id="node_2", name="Node 2", task_type="test", dependencies=["node_1"])
            ],
            dependencies=[("node_1", "node_2"), ("node_2", "node_1")]
        )
        
        with pytest.raises(ValueError, match="Invalid workflow definition"):
            await workflow_engine.create_workflow(invalid_workflow)
    
    @pytest.mark.asyncio
    async def test_dynamic_workflow_generation(self, workflow_engine):
        """Test dynamic workflow generation based on code changes"""
        code_changes = {
            "files_modified": 5,
            "test_files_modified": 2,
            "languages": ["python", "javascript"]
        }
        
        context = {
            "deployment_required": True,
            "environment": "staging"
        }
        
        workflow_def = await workflow_engine.generate_dynamic_workflow(code_changes, context)
        
        assert workflow_def is not None
        assert workflow_def.name.startswith("Dynamic Workflow")
        assert len(workflow_def.nodes) > 0
        
        # Check that appropriate stages are included
        node_types = [node.task_type for node in workflow_def.nodes]
        assert "code_analysis" in node_types
        assert "quality_check" in node_types
        assert "deployment" in node_types
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow_engine, sample_workflow_definition):
        """Test complete workflow execution"""
        workflow_id = await workflow_engine.create_workflow(sample_workflow_definition)
        
        input_data = {"repository": "test-repo", "branch": "main"}
        result = await workflow_engine.execute_workflow(workflow_id, input_data)
        
        assert result["success"] is True
        assert result["workflow_id"] == workflow_id
        assert "execution_time_seconds" in result
        assert "node_results" in result
        assert len(result["node_results"]) == 4
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, workflow_engine, sample_workflow_definition):
        """Test workflow cancellation"""
        workflow_id = await workflow_engine.create_workflow(sample_workflow_definition)
        
        # Start workflow execution in background
        execution_task = asyncio.create_task(
            workflow_engine.execute_workflow(workflow_id, {})
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Cancel the workflow
        cancelled = await workflow_engine.cancel_workflow(workflow_id)
        assert cancelled is True
        
        # Wait for execution to complete
        result = await execution_task
        # The result might be successful or cancelled depending on timing
        assert "workflow_id" in result
    
    @pytest.mark.asyncio
    async def test_workflow_status_tracking(self, workflow_engine, sample_workflow_definition):
        """Test workflow status tracking"""
        workflow_id = await workflow_engine.create_workflow(sample_workflow_definition)
        
        # Check initial status
        status = workflow_engine.get_workflow_status(workflow_id)
        assert status is not None
        assert status["workflow_id"] == workflow_id
        
        # Execute workflow and check status updates
        result = await workflow_engine.execute_workflow(workflow_id, {})
        
        final_status = workflow_engine.get_workflow_status(workflow_id)
        assert final_status is not None
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, workflow_engine):
        """Test workflow performance optimization"""
        optimization_result = await workflow_engine.optimize_performance()
        
        assert "optimized" in optimization_result
        assert "actions_taken" in optimization_result
        assert isinstance(optimization_result["actions_taken"], list)
    
    def test_get_performance_metrics(self, workflow_engine):
        """Test performance metrics collection"""
        metrics = workflow_engine.get_performance_metrics()
        
        assert "total_workflows_executed" in metrics
        assert "average_execution_time" in metrics
        assert "success_rate" in metrics
        assert "resource_utilization" in metrics
        assert "context_manager_summary" in metrics


class TestWorkflowGraph:
    """Test cases for WorkflowGraph"""
    
    @pytest.fixture
    def workflow_graph(self):
        """Create a workflow graph for testing"""
        return WorkflowGraph()
    
    @pytest.fixture
    def sample_nodes(self):
        """Create sample workflow nodes"""
        return [
            WorkflowNode(id="node_1", name="Node 1", task_type="analysis"),
            WorkflowNode(id="node_2", name="Node 2", task_type="build", dependencies=["node_1"]),
            WorkflowNode(id="node_3", name="Node 3", task_type="test", dependencies=["node_1"]),
            WorkflowNode(id="node_4", name="Node 4", task_type="deploy", dependencies=["node_2", "node_3"])
        ]
    
    def test_add_nodes(self, workflow_graph, sample_nodes):
        """Test adding nodes to workflow graph"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        assert len(workflow_graph.nodes) == 4
        assert "node_1" in workflow_graph.nodes
        assert "node_4" in workflow_graph.nodes
    
    def test_add_dependencies(self, workflow_graph, sample_nodes):
        """Test adding dependencies between nodes"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        # Add explicit dependencies
        workflow_graph.add_dependency("node_1", "node_2")
        workflow_graph.add_dependency("node_1", "node_3")
        workflow_graph.add_dependency("node_2", "node_4")
        workflow_graph.add_dependency("node_3", "node_4")
        
        # Verify dependencies
        assert "node_1" in workflow_graph.nodes["node_2"].dependencies
        assert "node_1" in workflow_graph.nodes["node_3"].dependencies
        assert "node_2" in workflow_graph.nodes["node_4"].dependencies
        assert "node_3" in workflow_graph.nodes["node_4"].dependencies
    
    def test_validate_graph(self, workflow_graph, sample_nodes):
        """Test graph validation"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        is_valid, errors = workflow_graph.validate_graph()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_circular_dependency_detection(self, workflow_graph):
        """Test circular dependency detection"""
        # Create nodes with circular dependency
        node1 = WorkflowNode(id="node_1", name="Node 1", task_type="test", dependencies=["node_2"])
        node2 = WorkflowNode(id="node_2", name="Node 2", task_type="test", dependencies=["node_1"])
        
        workflow_graph.add_node(node1)
        workflow_graph.add_node(node2)
        
        is_valid, errors = workflow_graph.validate_graph()
        assert is_valid is False
        assert any("circular" in error.lower() for error in errors)
    
    def test_execution_order_computation(self, workflow_graph, sample_nodes):
        """Test execution order computation"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        execution_order = workflow_graph.compute_execution_order()
        
        assert len(execution_order) > 0
        # First level should contain node_1 (no dependencies)
        assert "node_1" in execution_order[0]
        # Last level should contain node_4 (depends on others)
        assert "node_4" in execution_order[-1]
    
    def test_ready_nodes_identification(self, workflow_graph, sample_nodes):
        """Test identification of ready-to-execute nodes"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        # Initially, only node_1 should be ready
        ready_nodes = workflow_graph.get_ready_nodes()
        assert len(ready_nodes) == 1
        assert ready_nodes[0] == "node_1"
        
        # Mark node_1 as completed
        workflow_graph.update_node_status("node_1", NodeStatus.COMPLETED)
        
        # Now node_2 and node_3 should be ready
        ready_nodes = workflow_graph.get_ready_nodes()
        assert len(ready_nodes) == 2
        assert "node_2" in ready_nodes
        assert "node_3" in ready_nodes
    
    def test_critical_path_calculation(self, workflow_graph, sample_nodes):
        """Test critical path calculation"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        critical_path = workflow_graph.get_critical_path()
        
        assert len(critical_path) > 0
        assert critical_path[0] == "node_1"  # Should start with root node
        assert critical_path[-1] == "node_4"  # Should end with final node
    
    def test_execution_summary(self, workflow_graph, sample_nodes):
        """Test execution summary generation"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        # Mark some nodes as completed
        workflow_graph.update_node_status("node_1", NodeStatus.COMPLETED)
        workflow_graph.update_node_status("node_2", NodeStatus.COMPLETED)
        workflow_graph.update_node_status("node_3", NodeStatus.FAILED)
        
        summary = workflow_graph.get_execution_summary()
        
        assert summary["total_nodes"] == 4
        assert summary["status_counts"]["completed"] == 2
        assert summary["status_counts"]["failed"] == 1
        assert summary["completion_rate"] == 0.5
        assert summary["failure_rate"] == 0.25
    
    def test_graph_serialization(self, workflow_graph, sample_nodes):
        """Test graph serialization and deserialization"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        # Mark some nodes with status
        workflow_graph.update_node_status("node_1", NodeStatus.COMPLETED)
        
        # Serialize to dict
        graph_dict = workflow_graph.to_dict()
        
        assert "nodes" in graph_dict
        assert "execution_order" in graph_dict
        assert "metadata" in graph_dict
        assert len(graph_dict["nodes"]) == 4
        
        # Deserialize from dict
        restored_graph = WorkflowGraph.from_dict(graph_dict)
        
        assert len(restored_graph.nodes) == 4
        assert restored_graph.nodes["node_1"].status == NodeStatus.COMPLETED
    
    def test_graph_cloning(self, workflow_graph, sample_nodes):
        """Test graph cloning"""
        for node in sample_nodes:
            workflow_graph.add_node(node)
        
        workflow_graph.update_node_status("node_1", NodeStatus.RUNNING)
        
        cloned_graph = workflow_graph.clone()
        
        assert len(cloned_graph.nodes) == len(workflow_graph.nodes)
        assert cloned_graph.nodes["node_1"].status == NodeStatus.RUNNING
        
        # Verify it's a deep copy
        cloned_graph.update_node_status("node_1", NodeStatus.COMPLETED)
        assert workflow_graph.nodes["node_1"].status == NodeStatus.RUNNING


@pytest.mark.asyncio
class TestWorkflowEngineIntegration:
    """Integration tests for WorkflowEngine with other components"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        return Mock()
    
    @pytest.fixture
    def mock_postgres(self):
        """Mock PostgreSQL client"""
        return Mock()
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Mock AI provider"""
        return Mock()
    
    @pytest.fixture
    def workflow_engine_with_mocks(self, mock_redis, mock_postgres, mock_ai_provider):
        """Create workflow engine with mocked dependencies"""
        return WorkflowEngine(mock_redis, mock_postgres, mock_ai_provider)
    
    async def test_workflow_with_resource_constraints(self, workflow_engine_with_mocks):
        """Test workflow execution with resource constraints"""
        # Create a workflow that requires specific resources
        workflow_def = WorkflowDefinition(
            id=str(uuid4()),
            name="Resource Intensive Workflow",
            description="Workflow requiring specific resources",
            nodes=[
                WorkflowNode(
                    id="heavy_node",
                    name="Heavy Processing",
                    task_type="analysis",
                    resource_requirements={"cpu_cores": 4, "memory_gb": 8}
                )
            ]
        )
        
        workflow_id = await workflow_engine_with_mocks.create_workflow(workflow_def)
        result = await workflow_engine_with_mocks.execute_workflow(workflow_id, {})
        
        # Should complete successfully with resource allocation
        assert result["success"] is True
    
    async def test_workflow_failure_recovery(self, workflow_engine_with_mocks):
        """Test workflow failure recovery mechanisms"""
        # Create a workflow that might fail
        workflow_def = WorkflowDefinition(
            id=str(uuid4()),
            name="Failure Test Workflow",
            description="Workflow for testing failure recovery",
            nodes=[
                WorkflowNode(
                    id="failing_node",
                    name="Potentially Failing Node",
                    task_type="test",
                    max_retries=2
                )
            ]
        )
        
        workflow_id = await workflow_engine_with_mocks.create_workflow(workflow_def)
        
        # Mock a failure scenario
        with patch.object(workflow_engine_with_mocks, '_execute_node_task', side_effect=Exception("Simulated failure")):
            result = await workflow_engine_with_mocks.execute_workflow(workflow_id, {})
            
            # Should handle failure gracefully
            assert "success" in result
            assert "error" in result or result["success"] is True  # Might recover
    
    async def test_concurrent_workflow_execution(self, workflow_engine_with_mocks):
        """Test concurrent execution of multiple workflows"""
        workflows = []
        
        # Create multiple simple workflows
        for i in range(3):
            workflow_def = WorkflowDefinition(
                id=str(uuid4()),
                name=f"Concurrent Workflow {i}",
                description=f"Workflow {i} for concurrent testing",
                nodes=[
                    WorkflowNode(
                        id=f"node_{i}",
                        name=f"Node {i}",
                        task_type="test"
                    )
                ]
            )
            workflow_id = await workflow_engine_with_mocks.create_workflow(workflow_def)
            workflows.append(workflow_id)
        
        # Execute all workflows concurrently
        tasks = [
            workflow_engine_with_mocks.execute_workflow(wf_id, {})
            for wf_id in workflows
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All workflows should complete
        assert len(results) == 3
        for result in results:
            assert "success" in result
            assert "workflow_id" in result


if __name__ == "__main__":
    pytest.main([__file__])