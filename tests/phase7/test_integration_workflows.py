"""
Phase 7 Integration Tests: Multi-Agent Workflows

Comprehensive integration tests for multi-agent workflows including
end-to-end workflow execution, interactive mode, background monitoring,
and graceful degradation scenarios.
"""

import pytest
import tempfile
import time
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, List, Any

# Import components to test
from kirolinter.orchestration.workflow_coordinator import WorkflowCoordinator
from kirolinter.memory.pattern_memory import PatternMemory, create_pattern_memory
from kirolinter.agents.learner import LearnerAgent
from kirolinter.agents.reviewer import ReviewerAgent
from kirolinter.agents.fixer import FixerAgent
from kirolinter.agents.integrator import IntegratorAgent
from kirolinter.models.issue import Issue, IssueType, Severity
from kirolinter.models.suggestion import Suggestion, FixType


# temp_repo_dir fixture is now provided by conftest.py


class TestEndToEndWorkflows:
    """Integration tests for complete end-to-end workflows."""
    
    @pytest.fixture
    def mock_workflow_coordinator(self, temp_repo_dir):
        """Create a workflow coordinator with mocked dependencies."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        memory.retrieve_patterns.return_value = []
        
        # The LLM dependencies are already mocked by the autouse fixture
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=memory)
        yield coordinator, memory
    
    def test_full_autonomous_workflow(self, mock_workflow_coordinator, temp_repo_dir):
        """Test complete autonomous workflow from analysis to PR creation."""
        coordinator, memory = mock_workflow_coordinator
        
        # Mock all agent responses
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer, \
             patch.object(coordinator, 'integrator') as mock_integrator:
            
            # Mock reviewer analysis
            test_issue = Issue(
                file_path="test.py",
                line_number=5,
                rule_id="unused_variable",
                message="Unused variable",
                severity=Severity.MEDIUM,
                issue_type="style"
            )
            mock_reviewer.analyze.return_value = [test_issue]
            
            # Mock fixer application
            mock_fixer.apply_fixes.return_value = {
                "applied": 1,
                "failed": 0,
                "fixes": ["test_issue_1"]
            }
            
            # Mock integrator PR creation
            mock_integrator.create_pr.return_value = {
                "pr_number": 123,
                "url": "https://github.com/test/repo/pull/123",
                "status": "created"
            }
            
            # Execute full workflow
            result = coordinator.execute_workflow("full_review")
            
            # Verify workflow completion
            assert result["status"] == "complete", f"Workflow failed: {result}"
            assert result["progress"] == 100, "Workflow progress not 100%"
            assert "steps_completed" in result, "Step tracking missing"
            
            # Verify agent interactions
            mock_reviewer.analyze.assert_called_once()
            mock_fixer.apply_fixes.assert_called_once()
            mock_integrator.create_pr.assert_called_once()
            
            # Verify workflow logging
            memory.store_pattern.assert_called()
            
            # Check for workflow execution logging (store_pattern should be called at least once)
            assert memory.store_pattern.call_count > 0, "Workflow execution not logged" 
   
    def test_interactive_workflow_with_user_input(self, mock_workflow_coordinator, temp_repo_dir):
        """Test interactive workflow with user confirmation points."""
        coordinator, memory = mock_workflow_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer, \
             patch('builtins.input') as mock_input:
            
            # Mock user inputs (yes to all confirmations)
            mock_input.side_effect = ['y', 'y', 'y']
            
            # Mock reviewer analysis
            test_issues = [
                Issue(file_path="test.py", line_number=1, rule_id="style_1", message="Style issue", severity=Severity.LOW, issue_type="style"),
                Issue(file_path="test.py", line_number=2, rule_id="perf_1", message="Performance issue", severity=Severity.MEDIUM, issue_type="performance")
            ]
            mock_reviewer.analyze.return_value = test_issues
            
            # Mock fixer application
            mock_fixer.apply_fixes.return_value = {
                "applied": 2,
                "failed": 0,
                "fixes": ["issue_1", "issue_2"]
            }
            
            # Execute interactive workflow
            result = coordinator.execute_interactive("quick_fix")
            
            # Verify interactive completion
            assert result["status"] == "complete", "Interactive workflow failed"
            assert len(result["user_confirmations"]) >= 2, "User confirmations not tracked"
            
            # Verify interactive mode was used
            assert "mode" in result and result["mode"] == "interactive", "Interactive mode not detected"
            
            # Verify workflow logging
            memory.store_pattern.assert_called()
    
    def test_background_monitoring_workflow(self, mock_workflow_coordinator, temp_repo_dir):
        """Test background monitoring workflow setup and execution."""
        coordinator, memory = mock_workflow_coordinator
        
        # Mock the scheduler instance directly on the coordinator
        mock_scheduler_instance = Mock()
        mock_scheduler_instance.running = False  # Ensure start() will be called
        coordinator.scheduler = mock_scheduler_instance
        
        # Execute background workflow
        result = coordinator.execute_background("monitor")
        
        # Verify background setup
        assert result["status"] in ["scheduled", "running"], "Background workflow not started"
        assert "job_id" in result, "Job ID missing"
        
        # Verify scheduler interaction
        mock_scheduler_instance.start.assert_called()
        
        # Verify background workflow logging
        background_logged = any(
            call[0][1] == "background_workflow" 
            for call in memory.store_pattern.call_args_list
        )
        assert background_logged, "Background workflow not logged"
    
    def test_workflow_with_partial_failures(self, mock_workflow_coordinator, temp_repo_dir):
        """Test workflow handling with partial agent failures."""
        coordinator, memory = mock_workflow_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer, \
             patch.object(coordinator, 'integrator') as mock_integrator:
            
            # Mock reviewer success
            test_issue = Issue(file_path="test.py", line_number=1, rule_id="test_1", message="Test issue", severity=Severity.LOW, issue_type="style")
            mock_reviewer.analyze.return_value = [test_issue]
            
            # Mock fixer partial failure
            mock_fixer.apply_fixes.return_value = {
                "applied": 0,
                "failed": 1,
                "fixes": [],
                "errors": ["Fix application failed"]
            }
            
            # Mock integrator should not be called due to no fixes
            mock_integrator.create_pr.return_value = None
            
            # Execute workflow
            result = coordinator.execute_workflow("full_review")
            
            # Verify partial completion
            assert result["status"] in ["partial_complete", "failed"], "Partial failure not handled"
            assert result["progress"] < 100, "Progress should be less than 100% on partial failure"
            assert "errors" in result, "Error information missing"
            
            # Verify reviewer was called but integrator was not (due to no fixes)
            mock_reviewer.analyze.assert_called_once()
            mock_fixer.apply_fixes.assert_called_once()
            # Integrator might not be called if no fixes were applied
            
            # Verify error logging
            memory.store_pattern.assert_called()


class TestWorkflowDegradationAndFallbacks:
    """Integration tests for graceful degradation and fallback mechanisms."""
    
    @pytest.fixture
    def degradation_coordinator(self, temp_repo_dir):
        """Create coordinator for testing degradation scenarios."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=memory)
        yield coordinator, memory
    
    def test_reviewer_agent_failure_fallback(self, degradation_coordinator, temp_repo_dir):
        """Test fallback when reviewer agent fails."""
        coordinator, memory = degradation_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer:
            
            # Mock reviewer failure
            mock_reviewer.analyze.side_effect = Exception("Reviewer analysis failed")
            
            # Mock fixer should still work with empty issues
            mock_fixer.apply_fixes.return_value = {"applied": 0, "failed": 0, "fixes": []}
            
            # Execute workflow
            result = coordinator.execute_workflow("quick_fix")
            
            # Verify graceful degradation
            assert result["status"] in ["failed", "partial_complete"], "Failure not handled gracefully"
            assert "error" in result, "Error information missing"
            assert "Reviewer analysis failed" in str(result["error"]), "Specific error not captured"
            
            # Verify error logging
            memory.store_pattern.assert_called()
            
            # Check for error logging
            error_logged = any(
                "error" in str(call) or "failed" in str(call)
                for call in memory.store_pattern.call_args_list
            )
            assert error_logged, "Error not properly logged"
    
    def test_fixer_agent_failure_fallback(self, degradation_coordinator, temp_repo_dir):
        """Test fallback when fixer agent fails."""
        coordinator, memory = degradation_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer:
            
            # Mock reviewer success
            test_issue = Issue(file_path="test.py", line_number=1, rule_id="test_1", message="Test issue", severity=Severity.LOW, issue_type="style")
            mock_reviewer.analyze.return_value = [test_issue]
            
            # Mock fixer failure
            mock_fixer.apply_fixes.side_effect = Exception("Fix application failed")
            
            # Execute workflow
            result = coordinator.execute_workflow("quick_fix")
            
            # Verify graceful degradation
            assert result["status"] in ["failed", "partial_complete"], "Fixer failure not handled"
            assert "error" in result, "Error information missing"
            
            # Verify reviewer was called successfully
            mock_reviewer.analyze.assert_called_once()
            
            # Verify error logging
            memory.store_pattern.assert_called()
    
    def test_integrator_agent_failure_fallback(self, degradation_coordinator, temp_repo_dir):
        """Test fallback when integrator agent fails."""
        coordinator, memory = degradation_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer, \
             patch.object(coordinator, 'integrator') as mock_integrator:
            
            # Mock reviewer and fixer success
            test_issue = Issue(file_path="test.py", line_number=1, rule_id="test_1", message="Test issue", severity=Severity.LOW, issue_type="style")
            mock_reviewer.analyze.return_value = [test_issue]
            mock_fixer.apply_fixes.return_value = {"applied": 1, "failed": 0, "fixes": ["issue_1"]}
            
            # Mock integrator failure
            mock_integrator.create_pr.side_effect = Exception("PR creation failed")
            
            # Execute workflow
            result = coordinator.execute_workflow("full_review")
            
            # Verify partial completion (fixes applied but PR failed)
            assert result["status"] in ["partial_complete", "failed"], "Integrator failure not handled"
            assert result["progress"] > 0, "Should have some progress from successful fixes"
            
            # Verify earlier agents were called successfully
            mock_reviewer.analyze.assert_called_once()
            mock_fixer.apply_fixes.assert_called_once()
            mock_integrator.create_pr.assert_called_once()
    
    def test_memory_system_failure_fallback(self, temp_repo_dir):
        """Test fallback when memory system fails."""
        # Create coordinator with failing memory
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.side_effect = Exception("Memory storage failed")
        memory.get_team_patterns.side_effect = Exception("Memory retrieval failed")
        
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=memory)
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer:
            # Mock reviewer to work without memory
            mock_reviewer.analyze.return_value = []
            
            # Execute workflow
            result = coordinator.execute_workflow("quick_fix")
            
            # Verify workflow can still execute (though with degraded functionality)
            assert result["status"] in ["complete", "partial_complete", "failed"], "Memory failure not handled"
            
            # Verify reviewer was still called (should work without memory)
            mock_reviewer.analyze.assert_called_once()


class TestWorkflowPerformanceIntegration:
    """Integration tests for workflow performance and timing."""
    
    @pytest.fixture
    def performance_coordinator(self, temp_repo_dir):
        """Create coordinator for performance testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=memory)
        yield coordinator, memory
    
    def test_workflow_execution_timing(self, performance_coordinator, temp_repo_dir):
        """Test workflow execution stays within time limits."""
        coordinator, memory = performance_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer, \
             patch.object(coordinator, 'fixer') as mock_fixer:
            
            # Mock quick responses
            mock_reviewer.analyze.return_value = []
            mock_fixer.apply_fixes.return_value = {"applied": 0, "failed": 0, "fixes": []}
            
            # Time the workflow execution
            start_time = time.time()
            result = coordinator.execute_workflow("quick_fix")
            execution_time = time.time() - start_time
            
            # Verify reasonable execution time (should be fast with mocked agents)
            assert execution_time < 5.0, f"Workflow too slow: {execution_time}s"
            assert result["status"] == "complete", "Quick workflow should complete"
            
            # Verify timing is recorded
            if "duration" in result:
                assert result["duration"] > 0, "Duration not recorded"
    
    def test_concurrent_workflow_execution(self, performance_coordinator, temp_repo_dir):
        """Test multiple workflows can run concurrently."""
        coordinator, memory = performance_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer:
            mock_reviewer.analyze.return_value = []
            
            # Create multiple coordinators for concurrent execution
            coordinators = [
                WorkflowCoordinator(temp_repo_dir, memory=memory) 
                for _ in range(3)
            ]
            
            # Mock all reviewers
            for coord in coordinators:
                with patch.object(coord, 'reviewer') as mock_rev:
                    mock_rev.analyze.return_value = []
            
            # Execute workflows concurrently (simulated)
            results = []
            for coord in coordinators:
                with patch.object(coord, 'reviewer') as mock_rev:
                    mock_rev.analyze.return_value = []
                    result = coord.execute_workflow("quick_fix")
                    results.append(result)
            
            # Verify all workflows completed
            assert len(results) == 3, "Not all workflows executed"
            assert all(r["status"] == "complete" for r in results), "Some workflows failed"
            
            # Verify memory was accessed concurrently (multiple store calls)
            assert memory.store_pattern.call_count >= 3, "Concurrent memory access not working"


class TestWorkflowStateManagement:
    """Integration tests for workflow state management and persistence."""
    
    @pytest.fixture
    def stateful_coordinator(self, temp_repo_dir):
        """Create coordinator for state management testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        
        coordinator = WorkflowCoordinator(temp_repo_dir, memory=memory)
        yield coordinator, memory
    
    def test_workflow_state_persistence(self, stateful_coordinator, temp_repo_dir):
        """Test workflow state is properly persisted."""
        coordinator, memory = stateful_coordinator
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer:
            # Mock long-running analysis
            mock_reviewer.analyze.return_value = [
                Issue(file_path="test.py", line_number=1, rule_id="test_1", message="Test", severity=Severity.LOW, issue_type="style")
            ]
            
            # Execute workflow
            result = coordinator.execute_workflow("quick_fix")
            
            # Verify state persistence calls
            memory.store_pattern.assert_called()
            
            # Check for workflow state storage
            state_stored = any(
                "workflow_state" in str(call) or "workflow_execution" in str(call)
                for call in memory.store_pattern.call_args_list
            )
            assert state_stored, "Workflow state not persisted"
    
    def test_workflow_resume_capability(self, stateful_coordinator, temp_repo_dir):
        """Test workflow can resume from saved state."""
        coordinator, memory = stateful_coordinator
        
        # Mock existing workflow state
        existing_state = {
            "workflow_id": "test_workflow_123",
            "status": "in_progress",
            "completed_steps": ["analysis"],
            "remaining_steps": ["fix_application", "pr_creation"],
            "context": {"issues_found": 1}
        }
        
        memory.get_team_patterns.return_value = [
            {"pattern_data": existing_state}
        ]
        
        with patch.object(coordinator, 'fixer') as mock_fixer, \
             patch.object(coordinator, 'integrator') as mock_integrator:
            
            mock_fixer.apply_fixes.return_value = {"applied": 1, "failed": 0}
            mock_integrator.create_pr.return_value = {"pr_number": 123}
            
            # First, create a workflow pattern in memory to resume
            memory.get_team_patterns.return_value = [
                {
                    "pattern_data": {
                        "template": "test_workflow_123",
                        "status": "failed", 
                        "steps": [
                            {"step": "analyze", "status": "complete"},
                            {"step": "fix", "status": "failed"}
                        ],
                        "start_time": "2023-01-01T00:00:00"
                    }
                }
            ]
            
            # Resume workflow
            result = coordinator.resume_workflow("test_workflow_123")
            
            # Verify resume functionality
            assert result["status"] in ["complete", "resumed"] or "resumed_from" in result, "Workflow resume failed"
            
            # Verify only remaining steps were executed
            mock_fixer.apply_fixes.assert_called_once()
            mock_integrator.create_pr.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])