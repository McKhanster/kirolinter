"""
Tests for Phase 4 Workflow Orchestration.

Tests the enhanced agent capabilities and multi-agent workflow coordination
with Redis-based PatternMemory integration.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from kirolinter.agents.coordinator import CoordinatorAgent
from kirolinter.agents.reviewer import ReviewerAgent
from kirolinter.agents.fixer import FixerAgent
from kirolinter.agents.integrator import IntegratorAgent
from kirolinter.models.issue import Issue, IssueSeverity
from kirolinter.models.suggestion import Suggestion


class TestWorkflowOrchestration:
    """Test workflow orchestration and agent coordination."""
    
    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch('kirolinter.agents.coordinator.create_llm_provider') as mock_reviewer_llm:
            with patch('kirolinter.agents.fixer.get_chat_model') as mock_fixer_llm:
                with patch('kirolinter.agents.integrator.get_chat_model') as mock_integrator_llm:
                    mock_reviewer_llm.return_value = Mock()
                    mock_fixer_llm.return_value = Mock()
                    mock_integrator_llm.return_value = Mock()
                    yield
    
    @pytest.fixture
    def temp_repo_dir(self):
        """Create temporary repository directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some Python files for testing
            test_file = os.path.join(temp_dir, "test_file.py")
            with open(test_file, 'w') as f:
                f.write("import os\nimport sys\n\ndef test_function():\n    pass\n")
            yield temp_dir
    
    @pytest.fixture
    def mock_memory(self):
        """Create mock PatternMemory."""
        memory = Mock()
        memory.get_team_patterns.return_value = [
            {
                "pattern_type": "unused_import",
                "pattern_data": {"frequency": 10, "trend_score": 0.2},
                "confidence": 0.8
            }
        ]
        memory.get_issue_trends.return_value = {
            "trending_issues": [
                {
                    "issue_rule": "unused_import",
                    "issue_type": "code_quality",
                    "frequency": 10,
                    "trend_score": 0.2,
                    "severity": "medium"
                }
            ]
        }
        memory.store_pattern.return_value = True
        memory.track_issue_pattern.return_value = True
        return memory
    
    def test_full_workflow(self, temp_repo_dir, mock_memory):
        """Test complete workflow orchestration."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            coordinator = CoordinatorAgent(verbose=True)
            
            # Mock agent methods
            with patch.object(coordinator.reviewer, 'analyze') as mock_analyze:
                with patch.object(coordinator.reviewer, 'prioritize_issues') as mock_prioritize:
                    with patch.object(coordinator.reviewer, 'notify_stakeholders') as mock_notify:
                        
                        # Setup mocks
                        test_issue = Issue(
                            file_path=os.path.join(temp_repo_dir, "test_file.py"),
                            line_number=1,
                            rule_id="unused_import",
                            message="Unused import 'os'",
                            severity=IssueSeverity.MEDIUM,
                            issue_type="code_quality"
                        )
                        
                        mock_analyze.return_value = [test_issue]
                        mock_prioritize.return_value = [test_issue]
                        mock_notify.return_value = None
                        
                        # Execute workflow
                        result = coordinator.run_workflow(temp_repo_dir, "full_review")
                        
                        # Verify workflow execution
                        assert result.get("success", True) is True
                        assert result["workflow"] == "full_review"
                        assert "steps" in result
                        assert "analyze" in result["steps"]
                        
                        # Verify agent interactions
                        mock_analyze.assert_called_once()
                        mock_prioritize.assert_called_once()
                        mock_notify.assert_called_once()
    
    def test_pattern_aware_analysis(self, temp_repo_dir, mock_memory):
        """Test pattern-aware analysis with context integration."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
            
            # Mock scanner results
            with patch('kirolinter.agents.tools.scanner_tool.scan_repository') as mock_scan:
                mock_scan.invoke.return_value = {
                    "files": [
                        {
                            "file_path": os.path.join(temp_repo_dir, "test_file.py"),
                            "issues": [
                                {
                                    "rule_id": "unused_import",
                                    "message": "Unused import 'os'",
                                    "severity": "medium",
                                    "type": "code_quality",
                                    "line_number": 1
                                }
                            ]
                        }
                    ]
                }
                
                # Test pattern-aware analysis
                focus = [{"rule_id": "unused_import", "probability": 0.8}]
                issues = reviewer.analyze(temp_repo_dir, focus=focus)
                
                assert len(issues) > 0
                assert issues[0].rule_id is not None  # Should have some rule ID
                assert hasattr(issues[0], 'context')
                
                # Verify pattern memory interactions
                mock_memory.get_team_patterns.assert_called()
                mock_memory.track_issue_pattern.assert_called()
    
    def test_risk_assessment(self, temp_repo_dir, mock_memory):
        """Test risk assessment functionality."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
            
            # Create test issue
            issue = Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=1,
                rule_id="unused_import",
                message="Unused import 'os'",
                severity=IssueSeverity.HIGH,
                issue_type="code_quality"
            )
            
            # Test risk assessment
            risk_score = reviewer.assess_risk(issue)
            
            assert 0.0 <= risk_score <= 1.0
            assert isinstance(risk_score, float)
            
            # High severity should result in higher risk
            assert risk_score > 0.3  # Should be reasonably high for HIGH severity
    
    def test_intelligent_prioritization(self, temp_repo_dir, mock_memory):
        """Test multi-factor issue prioritization."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
            
            # Create test issues with different severities
            issues = [
                Issue(
                    file_path=os.path.join(temp_repo_dir, "test_file.py"),
                    line_number=1,
                    rule_id="unused_import",
                    message="Unused import",
                    severity=IssueSeverity.LOW,
                    issue_type="code_quality"
                ),
                Issue(
                    file_path=os.path.join(temp_repo_dir, "test_file.py"),
                    line_number=2,
                    rule_id="security_issue",
                    message="Security vulnerability",
                    severity=IssueSeverity.CRITICAL,
                    issue_type="security"
                )
            ]
            
            # Test prioritization
            prioritized = reviewer.prioritize_issues(issues, project_phase="production")
            
            assert len(prioritized) == 2
            # Issues should be prioritized by priority score
            assert prioritized[0].priority_score >= prioritized[1].priority_score
            assert prioritized[0].priority_score > prioritized[1].priority_score
    
    def test_safety_first_fix_application(self, temp_repo_dir, mock_memory):
        """Test safety-first fix application with validation."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            fixer = FixerAgent(memory=mock_memory, verbose=True)
            
            # Create test suggestion
            suggestion = Suggestion(
                issue_id="unused_import",
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=1,
                fix_type="delete",
                suggested_code="",
                confidence=0.95
            )
            
            # Test fix validation
            is_valid = fixer._validate_fix(suggestion)
            assert isinstance(is_valid, bool)
            
            # Test safety check
            with patch.object(fixer, '_should_auto_apply') as mock_should_apply:
                mock_should_apply.return_value = True
                
                with patch.object(fixer, '_apply_single_fix') as mock_apply:
                    mock_apply.return_value = True
                    
                    # Test fix application
                    applied = fixer.apply_fixes([suggestion], auto_apply=True)
                    
                    assert len(applied) == 1
                    assert applied[0] == "unused_import"
                    
                    # Verify safety checks were called
                    mock_should_apply.assert_called_once()
                    mock_apply.assert_called_once()
    
    def test_outcome_learning(self, temp_repo_dir, mock_memory):
        """Test fix outcome learning and adaptive strategies."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            fixer = FixerAgent(memory=mock_memory, verbose=True)
            fixer.repo_path = temp_repo_dir
            
            # Test learning from successful fix
            fixer.learn_from_fixes("test_issue", success=True, feedback="Good fix")
            
            # Verify pattern storage
            mock_memory.store_pattern.assert_called_with(
                temp_repo_dir,
                "fix_outcome",
                {
                    "issue_id": "test_issue",
                    "success": True,
                    "feedback": "Good fix",
                    "timestamp": pytest.approx(datetime.now().isoformat(), abs=10)
                },
                1.0
            )
            
            # Test strategy optimization
            mock_memory.get_team_patterns.return_value = [
                {
                    "pattern_data": {"success": True},
                    "confidence": 1.0
                },
                {
                    "pattern_data": {"success": False},
                    "confidence": 0.5
                }
            ]
            
            initial_threshold = fixer.confidence_threshold
            fixer._optimize_fix_strategy()
            
            # Threshold should be adjusted based on success rate
            assert fixer.confidence_threshold != initial_threshold
    
    def test_smart_pr_management(self, temp_repo_dir, mock_memory):
        """Test intelligent PR creation and management."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            integrator = IntegratorAgent(memory=mock_memory, verbose=True)
            
            # Test PR creation
            fixes = ["security_fix_1", "code_quality_fix_2", "style_fix_3"]
            
            # Mock fix categorization
            mock_memory.get_team_patterns.return_value = [
                {
                    "pattern_data": {"issue_id": "security_fix_1", "fix_type": "security"},
                    "confidence": 0.9
                }
            ]
            
            result = integrator.create_pr(temp_repo_dir, fixes)
            
            assert result["pr_created"] is True
            assert "pr_number" in result
            assert "categories" in result
            
            # Verify pattern storage
            mock_memory.store_pattern.assert_called()
            
            # Check that PR was created with proper categorization
            categories = result["categories"]
            assert isinstance(categories, dict)
    
    def test_workflow_recovery(self, temp_repo_dir, mock_memory):
        """Test workflow failure recovery mechanisms."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            coordinator = CoordinatorAgent(verbose=True)
            
            # Mock a failing step
            with patch.object(coordinator, '_convert_issues_to_suggestions') as mock_convert:
                mock_convert.side_effect = Exception("Conversion failed")
                
                with patch.object(coordinator, '_attempt_recovery') as mock_recovery:
                    mock_recovery.return_value = True
                    
                    # Execute workflow with failure
                    result = coordinator.run_workflow(temp_repo_dir, "quick_fix")
                    
                    # Verify recovery was attempted
                    mock_recovery.assert_called()
                    
                    # Check that workflow handled the failure gracefully
                    assert "steps" in result
                    assert "error" in result or "workflow_stopped" in result
    
    def test_comprehensive_workflow_integration(self, temp_repo_dir, mock_memory):
        """Test end-to-end workflow with all agents."""
        with patch('kirolinter.memory.pattern_memory.create_pattern_memory', return_value=mock_memory):
            coordinator = CoordinatorAgent(verbose=True)
            
            # Mock all agent interactions
            with patch('kirolinter.agents.learner.LearnerAgent') as mock_learner_class:
                with patch('kirolinter.agents.reviewer.ReviewerAgent') as mock_reviewer_class:
                    with patch('kirolinter.agents.fixer.FixerAgent') as mock_fixer_class:
                        with patch('kirolinter.agents.integrator.IntegratorAgent') as mock_integrator_class:
                            
                            # Setup mock instances
                            mock_learner = Mock()
                            mock_reviewer = Mock()
                            mock_fixer = Mock()
                            mock_integrator = Mock()
                            
                            mock_learner_class.return_value = mock_learner
                            mock_reviewer_class.return_value = mock_reviewer
                            mock_fixer_class.return_value = mock_fixer
                            mock_integrator_class.return_value = mock_integrator
                            
                            # Setup mock returns
                            mock_learner.predict_issues.return_value = [{"rule_id": "test", "probability": 0.8}]
                            mock_reviewer.analyze.return_value = [Mock()]
                            mock_reviewer.prioritize_issues.return_value = [Mock()]
                            mock_reviewer.notify_stakeholders.return_value = None
                            mock_fixer.apply_fixes.return_value = ["fix_1"]
                            mock_fixer.learn_from_fixes.return_value = None
                            mock_integrator.create_pr.return_value = {"pr_created": True, "pr_number": 123}
                            
                            # Execute autonomous workflow
                            result = coordinator.run_workflow(temp_repo_dir, "autonomous")
                            
                            # Verify all steps were executed
                            assert result["success"] is True
                            assert len(result["steps"]) == 5  # predict, analyze, fix, integrate, learn
                            
                            # Verify agent method calls
                            mock_learner.predict_issues.assert_called_once()
                            mock_reviewer.analyze.assert_called_once()
                            mock_reviewer.prioritize_issues.assert_called_once()
                            mock_fixer.apply_fixes.assert_called_once()
                            mock_integrator.create_pr.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])