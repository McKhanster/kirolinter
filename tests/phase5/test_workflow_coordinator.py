"""
Tests for Phase 5 Workflow Coordinator.

Tests autonomous workflow execution, interactive/background modes,
and workflow analytics with Redis-based PatternMemory integration.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from kirolinter.orchestration.workflow_coordinator import WorkflowCoordinator
from kirolinter.models.issue import Issue, IssueSeverity
from kirolinter.models.suggestion import Suggestion


class TestWorkflowCoordinator:
    """Test autonomous workflow coordination and orchestration."""
    
    @pytest.fixture
    def temp_repo_dir(self):
        """Create temporary repository directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.py")
            with open(test_file, 'w') as f:
                f.write("import os\nimport sys\n\ndef test_function():\n    pass\n")
            yield temp_dir
    
    @pytest.fixture
    def mock_memory(self):
        """Create mock PatternMemory."""
        memory = Mock()
        memory.get_team_patterns.return_value = []
        memory.store_pattern.return_value = True
        return memory
    
    @pytest.fixture(autouse=True)
    def mock_agents(self):
        """Mock all agent dependencies."""
        with patch('kirolinter.orchestration.workflow_coordinator.ReviewerAgent') as mock_reviewer:
            with patch('kirolinter.orchestration.workflow_coordinator.FixerAgent') as mock_fixer:
                with patch('kirolinter.orchestration.workflow_coordinator.IntegratorAgent') as mock_integrator:
                    with patch('kirolinter.orchestration.workflow_coordinator.LearnerAgent') as mock_learner:
                        with patch('kirolinter.orchestration.workflow_coordinator.CoordinatorAgent') as mock_coordinator:
                            
                            # Setup mock instances
                            mock_reviewer_instance = Mock()
                            mock_fixer_instance = Mock()
                            mock_integrator_instance = Mock()
                            mock_learner_instance = Mock()
                            mock_coordinator_instance = Mock()
                            
                            mock_reviewer.return_value = mock_reviewer_instance
                            mock_fixer.return_value = mock_fixer_instance
                            mock_integrator.return_value = mock_integrator_instance
                            mock_learner.return_value = mock_learner_instance
                            mock_coordinator.return_value = mock_coordinator_instance
                            
                            # Setup default returns
                            mock_learner_instance.predict_issues.return_value = [{"rule_id": "test", "probability": 0.8}]
                            mock_reviewer_instance.analyze.return_value = [Mock()]
                            mock_reviewer_instance.prioritize_issues.return_value = [Mock()]
                            mock_reviewer_instance.notify_stakeholders.return_value = None
                            mock_fixer_instance.apply_fixes.return_value = ["fix_1"]
                            mock_fixer_instance.learn_from_fixes.return_value = None
                            mock_integrator_instance.create_pr.return_value = {"pr_created": True, "pr_number": 123}
                            mock_learner_instance.learn_from_analysis.return_value = {"patterns_learned": 1}
                            
                            yield {
                                "reviewer": mock_reviewer_instance,
                                "fixer": mock_fixer_instance,
                                "integrator": mock_integrator_instance,
                                "learner": mock_learner_instance,
                                "coordinator": mock_coordinator_instance
                            }
    
    # Task 20.1: Autonomous Workflow Execution Engine Tests
    
    def test_workflow_execution_full_review(self, temp_repo_dir, mock_memory, mock_agents):
        """Test complete autonomous workflow execution."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        result = coordinator.execute_workflow("full_review")
        
        # Verify workflow completion
        assert result["status"] == "complete"
        assert result["template"] == "full_review"
        assert result["progress"] == 100.0
        assert len(result["steps"]) == 5  # predict, analyze, fix, integrate, learn
        
        # Verify all steps were executed
        step_names = [step["step"] for step in result["steps"]]
        assert "predict" in step_names
        assert "analyze" in step_names
        assert "fix" in step_names
        assert "integrate" in step_names
        assert "learn" in step_names
        
        # Verify agent method calls
        mock_agents["learner"].predict_issues.assert_called_once()
        mock_agents["reviewer"].analyze.assert_called_once()
        mock_agents["reviewer"].prioritize_issues.assert_called_once()
        mock_agents["fixer"].apply_fixes.assert_called_once()
        mock_agents["integrator"].create_pr.assert_called_once()
        
        # Verify pattern storage
        mock_memory.store_pattern.assert_called()
    
    def test_workflow_execution_quick_fix(self, temp_repo_dir, mock_memory, mock_agents):
        """Test quick fix workflow template."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        result = coordinator.execute_workflow("quick_fix")
        
        # Verify workflow completion
        assert result["status"] == "complete"
        assert result["template"] == "quick_fix"
        assert len(result["steps"]) == 2  # analyze, fix
        
        # Verify correct steps were executed
        step_names = [step["step"] for step in result["steps"]]
        assert "analyze" in step_names
        assert "fix" in step_names
        assert "predict" not in step_names  # Should not be in quick_fix
    
    def test_workflow_execution_monitor(self, temp_repo_dir, mock_memory, mock_agents):
        """Test monitoring workflow template."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        result = coordinator.execute_workflow("monitor")
        
        # Verify workflow completion
        assert result["status"] == "complete"
        assert result["template"] == "monitor"
        assert len(result["steps"]) == 3  # predict, analyze, notify
        
        # Verify correct steps were executed
        step_names = [step["step"] for step in result["steps"]]
        assert "predict" in step_names
        assert "analyze" in step_names
        assert "notify" in step_names
        assert "fix" not in step_names  # Should not be in monitor
    
    def test_workflow_error_handling(self, temp_repo_dir, mock_memory, mock_agents):
        """Test workflow error handling and recovery."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Make one step fail
        mock_agents["reviewer"].analyze.side_effect = Exception("Analysis failed")
        
        result = coordinator.execute_workflow("quick_fix")
        
        # Should handle error gracefully - since analyze step recovers, workflow completes
        # but should have a failed step recorded
        assert any(step.get("status") == "failed" for step in result["steps"])
        
        # Should still store pattern
        mock_memory.store_pattern.assert_called()
    
    def test_workflow_step_recovery(self, temp_repo_dir, mock_memory, mock_agents):
        """Test individual step error recovery."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Make predict step fail (non-critical)
        mock_agents["learner"].predict_issues.side_effect = Exception("Prediction failed")
        
        result = coordinator.execute_workflow("full_review")
        
        # Should recover and continue
        assert result["status"] == "complete"
        
        # Should have recorded the failed step
        predict_step = next((s for s in result["steps"] if s["step"] == "predict"), None)
        assert predict_step is not None
        assert predict_step["status"] == "failed"
        assert predict_step.get("recovered") is True
    
    def test_unknown_workflow_template(self, temp_repo_dir, mock_memory):
        """Test handling of unknown workflow template."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        result = coordinator.execute_workflow("unknown_template")
        
        assert result["status"] == "failed"
        assert "error" in result
        assert "Unknown workflow template" in result["error"]
    
    # Task 20.2: Interactive and Background Workflow Mode Tests
    
    def test_interactive_workflow_all_confirmed(self, temp_repo_dir, mock_memory, mock_agents):
        """Test interactive workflow with all steps confirmed."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Simulate all steps confirmed
        confirmations = {"predict": True, "analyze": True, "fix": True, "integrate": True, "learn": True}
        
        result = coordinator.execute_interactive("full_review", confirmations=confirmations)
        
        # Should complete successfully
        assert result["status"] == "complete"
        assert result["mode"] == "interactive"
        assert len(result["steps"]) == 5
        
        # All steps should be confirmed and completed
        for step in result["steps"]:
            assert step["confirmed"] is True
            assert step["status"] == "complete"
        
        # Should store interactive workflow pattern
        mock_memory.store_pattern.assert_called()
    
    def test_interactive_workflow_partial_confirmation(self, temp_repo_dir, mock_memory, mock_agents):
        """Test interactive workflow with some steps skipped."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Simulate some steps skipped
        confirmations = {"predict": True, "analyze": True, "fix": False, "integrate": False, "learn": True}
        
        result = coordinator.execute_interactive("full_review", confirmations=confirmations)
        
        # Should be partial complete
        assert result["status"] == "partial_complete"
        assert result["mode"] == "interactive"
        
        # Check step statuses
        completed_steps = [s for s in result["steps"] if s["status"] == "complete"]
        skipped_steps = [s for s in result["steps"] if s["status"] == "skipped"]
        
        assert len(completed_steps) == 3  # predict, analyze, learn
        assert len(skipped_steps) == 2   # fix, integrate
    
    def test_background_workflow_scheduling(self, temp_repo_dir, mock_memory, mock_agents):
        """Test background workflow scheduling."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock scheduler
        with patch.object(coordinator, 'scheduler') as mock_scheduler:
            mock_scheduler.running = False
            mock_scheduler.add_job = Mock()
            mock_scheduler.start = Mock()
            
            coordinator.execute_background("monitor", interval_hours=12)
            
            # Should have added job and started scheduler
            mock_scheduler.add_job.assert_called_once()
            mock_scheduler.start.assert_called_once()
            
            # Should store background workflow pattern
            mock_memory.store_pattern.assert_called()
    
    def test_background_workflow_execution(self, temp_repo_dir, mock_memory, mock_agents):
        """Test background workflow execution wrapper."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Test background execution wrapper
        coordinator._background_workflow_wrapper("monitor")
        
        # Should have executed workflow and stored result
        assert mock_memory.store_pattern.call_count >= 2  # workflow_execution + background_execution
    
    def test_stop_background_workflows(self, temp_repo_dir, mock_memory):
        """Test stopping background workflows."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock scheduler
        with patch.object(coordinator, 'scheduler') as mock_scheduler:
            mock_scheduler.running = True
            mock_scheduler.shutdown = Mock()
            
            coordinator.stop_background_workflows()
            
            mock_scheduler.shutdown.assert_called_once()
    
    def test_customize_workflow_template(self, temp_repo_dir, mock_memory):
        """Test workflow template customization."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        custom_steps = ["analyze", "notify"]
        coordinator.customize_workflow("custom_template", custom_steps)
        
        # Should have added custom template
        assert "custom_template" in coordinator.templates
        assert coordinator.templates["custom_template"] == custom_steps
        
        # Should store customization pattern
        mock_memory.store_pattern.assert_called()
    
    def test_customize_workflow_invalid_steps(self, temp_repo_dir, mock_memory):
        """Test workflow customization with invalid steps."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        invalid_steps = ["analyze", "invalid_step", "notify"]
        
        with pytest.raises(ValueError, match="Invalid steps"):
            coordinator.customize_workflow("invalid_template", invalid_steps)
    
    # Task 20.3: Workflow Analytics and Optimization Tests
    
    def test_workflow_analytics_no_data(self, temp_repo_dir, mock_memory):
        """Test workflow analytics with no execution data."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock empty patterns
        mock_memory.get_team_patterns.return_value = []
        
        analytics = coordinator.analyze_workflows()
        
        assert analytics["total_executions"] == 0
        assert analytics["success_rate"] == 0.0
        assert analytics["average_progress"] == 0.0
        assert len(analytics["recommendations"]) > 0
    
    def test_workflow_analytics_with_data(self, temp_repo_dir, mock_memory):
        """Test workflow analytics with execution data."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock execution patterns
        mock_executions = [
            {
                "pattern_data": {
                    "status": "complete",
                    "progress": 100,
                    "template": "full_review",
                    "steps": [
                        {"step": "predict", "status": "complete"},
                        {"step": "analyze", "status": "complete"},
                        {"step": "fix", "status": "complete"}
                    ]
                }
            },
            {
                "pattern_data": {
                    "status": "failed",
                    "progress": 50,
                    "template": "quick_fix",
                    "steps": [
                        {"step": "analyze", "status": "complete"},
                        {"step": "fix", "status": "failed"}
                    ]
                }
            }
        ]
        
        # Mock different pattern types separately
        def mock_get_patterns(repo_path, pattern_type):
            if pattern_type == "workflow_execution":
                return mock_executions
            return []
        
        mock_memory.get_team_patterns.side_effect = mock_get_patterns
        
        analytics = coordinator.analyze_workflows()
        
        assert analytics["total_executions"] == 2
        assert analytics["success_rate"] == 0.5  # 1 success out of 2
        assert analytics["average_progress"] == 75.0  # (100 + 50) / 2
        assert "full_review" in analytics["template_performance"]
        assert "quick_fix" in analytics["template_performance"]
        assert len(analytics["step_success_rates"]) > 0
    
    def test_template_optimization(self, temp_repo_dir, mock_memory):
        """Test workflow template optimization."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock successful executions with common pattern
        successful_executions = [
            {
                "status": "complete",
                "steps": [
                    {"step": "analyze", "status": "complete"},
                    {"step": "fix", "status": "complete"}
                ]
            },
            {
                "status": "complete", 
                "steps": [
                    {"step": "analyze", "status": "complete"},
                    {"step": "fix", "status": "complete"}
                ]
            }
        ]
        
        coordinator._optimize_templates(successful_executions)
        
        # Should have created optimized template
        assert "optimized" in coordinator.templates
        assert coordinator.templates["optimized"] == ["analyze", "fix"]
        
        # Should store optimization pattern
        mock_memory.store_pattern.assert_called()
    
    def test_ab_test_workflows(self, temp_repo_dir, mock_memory, mock_agents):
        """Test A/B testing of workflow templates."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock successful executions for both templates
        with patch.object(coordinator, 'execute_workflow') as mock_execute:
            mock_execute.side_effect = [
                {"status": "complete", "progress": 100},  # quick_fix run 1
                {"status": "complete", "progress": 100},  # quick_fix run 2
                {"status": "failed", "progress": 50},     # monitor run 1
                {"status": "complete", "progress": 100},  # monitor run 2
            ]
            
            result = coordinator.ab_test_workflows("quick_fix", "monitor", runs=2)
            
            assert result["template_a"] == "quick_fix"
            assert result["template_b"] == "monitor"
            assert result["runs"] == 2
            assert result["success_rate_a"] == 1.0  # 2/2 success
            assert result["success_rate_b"] == 0.5  # 1/2 success
            assert result["winner"] == "quick_fix"
            
            # Should have called execute_workflow 4 times (2 runs each)
            assert mock_execute.call_count == 4
            
            # Should store A/B test results
            mock_memory.store_pattern.assert_called()
    
    def test_ab_test_invalid_templates(self, temp_repo_dir, mock_memory):
        """Test A/B testing with invalid templates."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        result = coordinator.ab_test_workflows("invalid_template", "quick_fix", runs=2)
        
        assert "error" in result
        assert "not found" in result["error"]
    
    # Utility Method Tests
    
    def test_get_workflow_status(self, temp_repo_dir, mock_memory):
        """Test getting current workflow status."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        status = coordinator.get_workflow_status()
        
        assert "status" in status
        assert "progress" in status
        assert status["status"] == "idle"  # Initial state
    
    def test_get_available_templates(self, temp_repo_dir, mock_memory):
        """Test getting available workflow templates."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        templates = coordinator.get_available_templates()
        
        assert isinstance(templates, list)
        assert "full_review" in templates
        assert "quick_fix" in templates
        assert "monitor" in templates
    
    def test_get_template_steps(self, temp_repo_dir, mock_memory):
        """Test getting steps for a specific template."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        steps = coordinator.get_template_steps("full_review")
        
        assert isinstance(steps, list)
        assert "predict" in steps
        assert "analyze" in steps
        assert "fix" in steps
        assert "integrate" in steps
        assert "learn" in steps
    
    def test_get_execution_history(self, temp_repo_dir, mock_memory):
        """Test getting workflow execution history."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock execution history
        mock_history = [
            {
                "pattern_data": {
                    "start_time": "2025-08-15T10:00:00",
                    "template": "full_review",
                    "status": "complete"
                }
            }
        ]
        mock_memory.get_team_patterns.return_value = mock_history
        
        history = coordinator.get_execution_history(limit=5)
        
        assert isinstance(history, list)
        assert len(history) <= 5
    
    def test_cleanup_old_executions(self, temp_repo_dir, mock_memory):
        """Test cleanup of old workflow executions."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Should not raise exception
        coordinator.cleanup_old_executions(days_to_keep=30)
    
    def test_coordinator_destruction(self, temp_repo_dir, mock_memory):
        """Test coordinator cleanup on destruction."""
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=mock_memory, verbose=True)
        
        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.shutdown = Mock()
        coordinator.scheduler = mock_scheduler
        
        # Trigger destruction
        coordinator.__del__()
        
        # Should have shut down scheduler
        mock_scheduler.shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])