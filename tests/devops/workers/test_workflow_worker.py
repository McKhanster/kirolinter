"""
Tests for Workflow Worker

Comprehensive tests for Celery-based workflow execution workers.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import asyncio
import json

from kirolinter.workers.workflow_worker import (
    execute_workflow_task, execute_workflow_stage_task, execute_parallel_stages_task,
    generate_dynamic_workflow_task, get_workflow_engine
)
from kirolinter.devops.models.workflow import WorkflowDefinition, ExecutionContext, WorkflowStage, StageType


class TestWorkflowWorkerTasks:
    """Test cases for workflow worker Celery tasks"""
    
    @pytest.fixture
    def mock_celery_task(self):
        """Create a mock Celery task instance"""
        task = Mock()
        task.request = Mock()
        task.request.id = "test_task_id_123"
        task.update_state = Mock()
        task.retry = Mock()
        task.MaxRetriesExceededError = Exception
        return task
    
    @pytest.fixture
    def sample_workflow_definition_dict(self):
        """Create a sample workflow definition dictionary"""
        return {
            "id": "test_workflow_123",
            "name": "Test Workflow",
            "description": "A test workflow",
            "version": "1.0.0",
            "stages": [
                {
                    "id": "stage_1",
                    "name": "Analysis Stage",
                    "type": "analysis",
                    "dependencies": [],
                    "parameters": {"language": "python"},
                    "timeout_seconds": 300,
                    "allow_failure": False,
                    "retry_count": 0
                }
            ],
            "timeout_seconds": 3600,
            "max_parallel_stages": 5
        }
    
    @pytest.fixture
    def sample_context_dict(self):
        """Create a sample execution context dictionary"""
        return {
            "workflow_id": "test_workflow_123",
            "execution_id": "test_execution_456",
            "triggered_by": "test_user",
            "environment": "test",
            "parameters": {"test_param": "test_value"},
            "metadata": {"test_meta": "test_meta_value"}
        }
    
    @pytest.fixture
    def sample_stage_data(self):
        """Create sample stage data"""
        return {
            "id": "test_stage_1",
            "name": "Test Stage",
            "type": "analysis",
            "dependencies": [],
            "parameters": {"param1": "value1"},
            "timeout_seconds": 300,
            "allow_failure": False,
            "retry_count": 0
        }
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    @patch('kirolinter.workers.workflow_worker.WorkflowDefinition')
    @patch('kirolinter.workers.workflow_worker.ExecutionContext')
    def test_execute_workflow_task_success(self, mock_execution_context, mock_workflow_definition, 
                                         mock_get_engine, mock_celery_task, 
                                         sample_workflow_definition_dict, sample_context_dict):
        """Test successful workflow execution task"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_workflow_def = Mock()
        mock_workflow_def.id = "test_workflow_123"
        mock_workflow_definition.from_dict.return_value = mock_workflow_def
        
        mock_context = Mock()
        mock_execution_context.from_dict.return_value = mock_context
        
        # Mock successful workflow execution
        mock_result = Mock()
        mock_result.status.value = "completed"
        mock_result.workflow_id = "test_workflow_123"
        mock_result.execution_id = "test_execution_456"
        mock_result.duration_seconds = 45.5
        mock_result.stage_results = [Mock(), Mock()]
        mock_result.completed_at = datetime.utcnow()
        mock_result.error_message = None
        
        # Mock asyncio loop
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = mock_result
            
            # Bind the task method
            bound_task = execute_workflow_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            result = bound_task(sample_workflow_definition_dict, sample_context_dict)
            
            # Verify results
            assert result["success"] is True
            assert result["workflow_id"] == "test_workflow_123"
            assert result["execution_id"] == "test_execution_456"
            assert result["status"] == "completed"
            assert result["duration_seconds"] == 45.5
            assert result["stage_count"] == 2
            
            # Verify mocks were called
            mock_get_engine.assert_called_once()
            mock_celery_task.update_state.assert_called()
            mock_loop.close.assert_called_once()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    def test_execute_workflow_task_failure(self, mock_get_engine, mock_celery_task, 
                                         sample_workflow_definition_dict):
        """Test workflow execution task failure with retry"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock failure
        test_exception = Exception("Workflow execution failed")
        
        with patch('kirolinter.workers.workflow_worker.WorkflowDefinition') as mock_workflow_def, \
             patch('kirolinter.workers.workflow_worker.get_retry_config') as mock_retry_config:
            
            mock_workflow_def.from_dict.side_effect = test_exception
            mock_retry_config.return_value = {
                'countdown': 60,
                'max_retries': 3
            }
            
            # Setup retry mock
            mock_celery_task.retry.side_effect = mock_celery_task.MaxRetriesExceededError()
            
            # Bind the task method
            bound_task = execute_workflow_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            result = bound_task(sample_workflow_definition_dict)
            
            # Verify failure handling
            assert result["success"] is False
            assert "error" in result
            assert result["max_retries_exceeded"] is True
            
            # Verify retry was attempted
            mock_celery_task.retry.assert_called_once()
            mock_celery_task.update_state.assert_called()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    @patch('kirolinter.workers.workflow_worker.WorkflowStage')
    @patch('kirolinter.workers.workflow_worker.ExecutionContext')
    def test_execute_workflow_stage_task_success(self, mock_execution_context, mock_workflow_stage,
                                                mock_get_engine, mock_celery_task,
                                                sample_stage_data, sample_context_dict):
        """Test successful workflow stage execution task"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_stage = Mock()
        mock_stage.id = "test_stage_1"
        mock_workflow_stage.return_value = mock_stage
        
        mock_context = Mock()
        mock_context.execution_id = "test_execution_456"
        mock_execution_context.return_value = mock_context
        
        # Mock successful stage execution
        mock_stage_result = Mock()
        mock_stage_result.status.value = "completed"
        mock_stage_result.output = {"result": "success"}
        mock_stage_result.error_message = None
        mock_stage_result.started_at = datetime.utcnow()
        mock_stage_result.completed_at = datetime.utcnow()
        mock_stage_result.duration_seconds = 15.2
        
        # Mock asyncio loop
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = mock_stage_result
            
            # Bind the task method
            bound_task = execute_workflow_stage_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            result = bound_task(sample_stage_data, sample_context_dict)
            
            # Verify results
            assert result["success"] is True
            assert result["stage_id"] == "test_stage_1"
            assert result["execution_id"] == "test_execution_456"
            assert result["status"] == "completed"
            assert result["duration_seconds"] == 15.2
            
            # Verify mocks were called
            mock_get_engine.assert_called_once()
            mock_celery_task.update_state.assert_called()
            mock_loop.close.assert_called_once()
    
    @patch('kirolinter.workers.workflow_worker.execute_workflow_stage_task')
    def test_execute_parallel_stages_task_success(self, mock_stage_task, mock_celery_task,
                                                 sample_context_dict):
        """Test successful parallel stages execution task"""
        # Setup stage data
        stages_data = [
            {"id": "stage_1", "name": "Stage 1", "type": "analysis"},
            {"id": "stage_2", "name": "Stage 2", "type": "build"},
            {"id": "stage_3", "name": "Stage 3", "type": "test"}
        ]
        
        # Mock stage task results
        mock_task_results = [
            {"success": True, "stage_id": "stage_1", "status": "completed"},
            {"success": True, "stage_id": "stage_2", "status": "completed"},
            {"success": True, "stage_id": "stage_3", "status": "completed"}
        ]
        
        # Mock delay and get methods
        mock_tasks = []
        for i, result in enumerate(mock_task_results):
            mock_task = Mock()
            mock_task.get.return_value = result
            mock_tasks.append(mock_task)
        
        mock_stage_task.delay.side_effect = mock_tasks
        
        # Bind the task method
        bound_task = execute_parallel_stages_task.__get__(mock_celery_task, type(mock_celery_task))
        
        # Execute the task
        result = bound_task(stages_data, sample_context_dict)
        
        # Verify results
        assert len(result) == 3
        assert all(r["success"] for r in result)
        assert [r["stage_id"] for r in result] == ["stage_1", "stage_2", "stage_3"]
        
        # Verify stage tasks were created
        assert mock_stage_task.delay.call_count == 3
        mock_celery_task.update_state.assert_called()
    
    @patch('kirolinter.workers.workflow_worker.execute_workflow_stage_task')
    def test_execute_parallel_stages_task_partial_failure(self, mock_stage_task, mock_celery_task,
                                                         sample_context_dict):
        """Test parallel stages execution with partial failures"""
        # Setup stage data
        stages_data = [
            {"id": "stage_1", "name": "Stage 1", "type": "analysis"},
            {"id": "stage_2", "name": "Stage 2", "type": "build"}
        ]
        
        # Mock mixed results (one success, one failure)
        mock_task_results = [
            {"success": True, "stage_id": "stage_1", "status": "completed"},
            {"success": False, "stage_id": "stage_2", "status": "failed", "error": "Build failed"}
        ]
        
        # Mock delay and get methods
        mock_tasks = []
        for i, result in enumerate(mock_task_results):
            mock_task = Mock()
            if result["success"]:
                mock_task.get.return_value = result
            else:
                mock_task.get.side_effect = Exception("Task failed")
            mock_tasks.append(mock_task)
        
        mock_stage_task.delay.side_effect = mock_tasks
        
        # Bind the task method
        bound_task = execute_parallel_stages_task.__get__(mock_celery_task, type(mock_celery_task))
        
        # Execute the task
        result = bound_task(stages_data, sample_context_dict)
        
        # Verify results
        assert len(result) == 2
        assert result[0]["success"] is True
        assert result[1]["success"] is False
        assert "error" in result[1]
        
        # Verify update_state was called with failure
        mock_celery_task.update_state.assert_called()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    def test_generate_dynamic_workflow_task_success(self, mock_get_engine, mock_celery_task):
        """Test successful dynamic workflow generation task"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock workflow definition
        mock_workflow_def = Mock()
        mock_workflow_def.id = "dynamic_workflow_123"
        mock_workflow_def.name = "Dynamic Workflow"
        mock_workflow_def.description = "Generated workflow"
        mock_workflow_def.version = "1.0.0"
        mock_workflow_def.dependencies = []
        mock_workflow_def.metadata = {}
        mock_workflow_def.timeout_seconds = 3600
        mock_workflow_def.max_parallel_nodes = 5
        
        # Mock nodes
        mock_node = Mock()
        mock_node.id = "node_1"
        mock_node.name = "Analysis Node"
        mock_node.task_type = "analysis"
        mock_node.dependencies = []
        mock_node.parameters = {}
        mock_node.resource_requirements = {}
        mock_node.timeout_seconds = 300
        mock_node.max_retries = 3
        
        mock_workflow_def.nodes = [mock_node]
        
        # Mock asyncio loop
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = mock_workflow_def
            
            # Bind the task method
            bound_task = generate_dynamic_workflow_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            code_changes = {"files_modified": 5, "test_files_modified": 2}
            context = {"deployment_required": True}
            
            result = bound_task(code_changes, context)
            
            # Verify results
            assert result["id"] == "dynamic_workflow_123"
            assert result["name"] == "Dynamic Workflow"
            assert len(result["nodes"]) == 1
            assert result["nodes"][0]["id"] == "node_1"
            assert result["nodes"][0]["task_type"] == "analysis"
            
            # Verify mocks were called
            mock_get_engine.assert_called_once()
            mock_celery_task.update_state.assert_called()
            mock_loop.close.assert_called_once()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    def test_generate_dynamic_workflow_task_failure(self, mock_get_engine, mock_celery_task):
        """Test dynamic workflow generation task failure"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock failure
        test_exception = Exception("Workflow generation failed")
        
        # Mock asyncio loop
        with patch('asyncio.new_event_loop') as mock_new_loop, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = test_exception
            
            # Bind the task method
            bound_task = generate_dynamic_workflow_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            code_changes = {"files_modified": 5}
            context = {}
            
            result = bound_task(code_changes, context)
            
            # Verify failure handling
            assert result["success"] is False
            assert "error" in result
            assert result["code_changes"] == code_changes
            
            # Verify mocks were called
            mock_get_engine.assert_called_once()
            mock_loop.close.assert_called_once()


class TestWorkflowWorkerUtilities:
    """Test cases for workflow worker utility functions"""
    
    @patch('kirolinter.workers.workflow_worker.WorkflowEngine')
    def test_get_workflow_engine_singleton(self, mock_workflow_engine_class):
        """Test that get_workflow_engine returns singleton instance"""
        # Reset global variable
        import kirolinter.workers.workflow_worker
        kirolinter.workers.workflow_worker.workflow_engine = None
        
        mock_engine_instance = Mock()
        mock_workflow_engine_class.return_value = mock_engine_instance
        
        # First call should create instance
        engine1 = get_workflow_engine()
        assert engine1 == mock_engine_instance
        mock_workflow_engine_class.assert_called_once()
        
        # Second call should return same instance
        engine2 = get_workflow_engine()
        assert engine2 == mock_engine_instance
        assert engine1 is engine2
        
        # WorkflowEngine constructor should only be called once
        mock_workflow_engine_class.assert_called_once()


class TestWorkflowWorkerIntegration:
    """Integration tests for workflow worker"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        return Mock()
    
    @pytest.fixture
    def mock_app_json(self):
        """Mock app.json for serialization"""
        mock_json = Mock()
        mock_json.dumps.side_effect = json.dumps
        return mock_json
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    @patch('kirolinter.cache.redis_client.get_redis_client')
    def test_collect_workflow_metrics_task_with_redis(self, mock_get_redis, mock_get_engine, 
                                                     mock_celery_task, mock_redis_client):
        """Test workflow metrics collection with Redis storage"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_get_redis.return_value = mock_redis_client
        
        # Mock performance metrics
        mock_metrics = {
            "total_workflows_executed": 10,
            "average_execution_time": 45.5,
            "success_rate": 0.9,
            "resource_utilization": {"cpu": 75.0}
        }
        mock_engine.get_performance_metrics.return_value = mock_metrics
        
        # Mock app.json
        with patch('kirolinter.workers.workflow_worker.app') as mock_app:
            mock_app.json.dumps.side_effect = json.dumps
            
            # Import and bind the task
            from kirolinter.workers.workflow_worker import collect_workflow_metrics_task
            bound_task = collect_workflow_metrics_task.__get__(mock_celery_task, type(mock_celery_task))
            
            # Execute the task
            result = bound_task(time_range_hours=24)
            
            # Verify results
            assert result["total_workflows_executed"] == 10
            assert result["average_execution_time"] == 45.5
            assert result["success_rate"] == 0.9
            assert "collected_at" in result
            assert result["time_range_hours"] == 24
            
            # Verify Redis storage
            mock_redis_client.setex.assert_called_once()
            call_args = mock_redis_client.setex.call_args
            assert call_args[0][1] == 3600  # TTL
            
            # Verify mocks were called
            mock_get_engine.assert_called_once()
            mock_engine.get_performance_metrics.assert_called_once()
            mock_celery_task.update_state.assert_called()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    def test_workflow_health_check_task(self, mock_get_engine, mock_celery_task):
        """Test workflow health check task"""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock resource manager
        mock_resource_manager = Mock()
        mock_engine.resource_manager = mock_resource_manager
        mock_resource_manager.get_resource_utilization.return_value = {
            "cpu_pool": {"utilization_percentage": 45.0},
            "memory_pool": {"utilization_percentage": 60.0}
        }
        
        # Mock failure handler
        mock_failure_handler = Mock()
        mock_engine.failure_handler = mock_failure_handler
        mock_failure_handler.get_failure_statistics.return_value = {
            "total_failures": 25
        }
        
        # Mock performance metrics
        mock_engine.get_performance_metrics.return_value = {
            "success_rate": 0.95
        }
        
        # Import and bind the task
        from kirolinter.workers.workflow_worker import workflow_health_check_task
        bound_task = workflow_health_check_task.__get__(mock_celery_task, type(mock_celery_task))
        
        # Execute the task
        result = bound_task()
        
        # Verify results
        assert result["healthy"] is True
        assert result["health_score"] > 80
        assert "issues" in result
        assert "metrics" in result
        assert "resource_utilization" in result
        assert "failure_statistics" in result
        assert "checked_at" in result
        
        # Verify mocks were called
        mock_get_engine.assert_called_once()
        mock_resource_manager.get_resource_utilization.assert_called_once()
        mock_failure_handler.get_failure_statistics.assert_called_once()
        mock_engine.get_performance_metrics.assert_called_once()
    
    @patch('kirolinter.workers.workflow_worker.get_workflow_engine')
    def test_workflow_health_check_task_unhealthy(self, mock_get_engine, mock_celery_task):
        """Test workflow health check task with unhealthy conditions"""
        # Setup mocks for unhealthy conditions
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock high resource utilization
        mock_resource_manager = Mock()
        mock_engine.resource_manager = mock_resource_manager
        mock_resource_manager.get_resource_utilization.return_value = {
            "cpu_pool": {"utilization_percentage": 95.0},  # High utilization
            "memory_pool": {"utilization_percentage": 85.0}
        }
        
        # Mock high failure count
        mock_failure_handler = Mock()
        mock_engine.failure_handler = mock_failure_handler
        mock_failure_handler.get_failure_statistics.return_value = {
            "total_failures": 150  # High failure count
        }
        
        # Mock low success rate
        mock_engine.get_performance_metrics.return_value = {
            "success_rate": 0.75  # Low success rate
        }
        
        # Import and bind the task
        from kirolinter.workers.workflow_worker import workflow_health_check_task
        bound_task = workflow_health_check_task.__get__(mock_celery_task, type(mock_celery_task))
        
        # Execute the task
        result = bound_task()
        
        # Verify unhealthy results
        assert result["healthy"] is False
        assert result["health_score"] < 80
        assert len(result["issues"]) > 0
        
        # Check specific issues
        issues_text = " ".join(result["issues"])
        assert "high resource utilization" in issues_text.lower()
        assert "high failure count" in issues_text.lower()
        assert "low success rate" in issues_text.lower()


if __name__ == "__main__":
    pytest.main([__file__])