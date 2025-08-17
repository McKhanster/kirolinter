"""
Tests for Phase 4 Enhanced Reviewer Agent.

Tests pattern-aware analysis, risk assessment, and intelligent prioritization.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from kirolinter.agents.reviewer import ReviewerAgent
from kirolinter.models.issue import Issue, IssueSeverity


class TestEnhancedReviewer:
    """Test enhanced reviewer agent capabilities."""
    
    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch('kirolinter.agents.reviewer.create_llm_provider') as mock:
            mock.return_value = Mock()
            yield mock
    
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
        memory.get_team_patterns.return_value = [
            {
                "pattern_type": "unused_import",
                "pattern_data": {"frequency": 15, "trend_score": 0.3},
                "confidence": 0.85
            }
        ]
        memory.get_issue_trends.return_value = {
            "trending_issues": [
                {
                    "issue_rule": "unused_import",
                    "issue_type": "code_quality",
                    "frequency": 15,
                    "trend_score": 0.3,
                    "severity": "medium"
                }
            ]
        }
        memory.track_issue_pattern.return_value = True
        memory.store_pattern.return_value = True
        return memory
    
    def test_pattern_aware_analysis(self, temp_repo_dir, mock_memory):
        """Test pattern-aware analysis with context integration."""
        reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
        
        # Mock scanner tool
        with patch('kirolinter.agents.reviewer.scan_repository') as mock_scan:
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
            
            # Test analysis with focus
            focus = [{"rule_id": "unused_import", "probability": 0.8}]
            issues = reviewer.analyze(temp_repo_dir, focus=focus)
            
            # Verify results
            assert len(issues) >= 1
            assert issues[0].rule_id is not None  # Should have some rule ID
            assert issues[0].context is not None
            assert "frequency" in issues[0].context
            
            # Verify memory interactions
            mock_memory.get_team_patterns.assert_called_with(temp_repo_dir, "issue_frequency")
            mock_memory.track_issue_pattern.assert_called()
    
    def test_risk_assessment(self, temp_repo_dir, mock_memory):
        """Test risk assessment using patterns and severity."""
        reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
        
        # Test with high severity issue
        high_risk_issue = Issue(
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            rule_id="unused_import",
            message="Unused import",
            severity=IssueSeverity.CRITICAL,
            issue_type="security"
        )
        
        risk_score = reviewer.assess_risk(high_risk_issue)
        
        assert 0.0 <= risk_score <= 1.0
        assert risk_score > 0.5  # Critical should be high risk
        
        # Test with low severity issue
        low_risk_issue = Issue(
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            rule_id="style_issue",
            message="Style issue",
            severity=IssueSeverity.LOW,
            issue_type="style"
        )
        
        low_risk_score = reviewer.assess_risk(low_risk_issue)
        assert low_risk_score < risk_score  # Should be lower than critical
    
    def test_trend_analysis(self, temp_repo_dir, mock_memory):
        """Test emerging issue trend analysis."""
        reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
        
        trends = reviewer.analyze_trends(temp_repo_dir)
        
        assert "emerging_patterns" in trends
        assert "total_patterns" in trends
        assert isinstance(trends["emerging_patterns"], list)
        
        # Should have found the trending issue from mock
        if trends["emerging_patterns"]:
            pattern = trends["emerging_patterns"][0]
            assert "rule_id" in pattern
            assert "frequency" in pattern
            assert "growth" in pattern
    
    def test_intelligent_prioritization(self, temp_repo_dir, mock_memory):
        """Test multi-factor issue prioritization."""
        reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
        
        # Create issues with different characteristics
        issues = [
            Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=1,
                rule_id="unused_import",
                message="Unused import",
                severity=IssueSeverity.MEDIUM,
                issue_type="code_quality"
            ),
            Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=2,
                rule_id="security_vuln",
                message="Security vulnerability",
                severity=IssueSeverity.HIGH,
                issue_type="security"
            ),
            Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=3,
                rule_id="performance_issue",
                message="Performance issue",
                severity=IssueSeverity.LOW,
                issue_type="performance"
            )
        ]
        
        # Test prioritization for production phase
        prioritized = reviewer.prioritize_issues(issues, project_phase="production")
        
        assert len(prioritized) == 3
        
        # Verify priority scores were assigned
        for issue in prioritized:
            assert hasattr(issue, 'priority_score')
            assert hasattr(issue, 'priority_rank')
            assert issue.priority_score > 0
        
        # Issues should be prioritized (highest priority first)
        assert prioritized[0].priority_score >= prioritized[1].priority_score
        assert prioritized[0].priority_score >= prioritized[1].priority_score
    
    def test_stakeholder_notifications(self, temp_repo_dir, mock_memory):
        """Test stakeholder notification system."""
        reviewer = ReviewerAgent(memory=mock_memory, verbose=True)
        
        # Create issues for different stakeholder groups
        issues = [
            Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=1,
                rule_id="security_issue",
                message="Security issue",
                severity=IssueSeverity.CRITICAL,
                issue_type="security"
            ),
            Issue(
                file_path=os.path.join(temp_repo_dir, "test_file.py"),
                line_number=2,
                rule_id="style_issue",
                message="Style issue",
                severity=IssueSeverity.LOW,
                issue_type="style"
            )
        ]
        
        # Test notification (should not raise exceptions)
        reviewer.notify_stakeholders(issues, temp_repo_dir)
        
        # Verify pattern was stored
        mock_memory.store_pattern.assert_called()
        
        # Check the stored pattern contains notification data
        call_args = mock_memory.store_pattern.call_args
        assert call_args[0][1] == "notification_sent"  # pattern_type
        pattern_data = call_args[0][2]  # pattern_data
        assert "total_issues" in pattern_data
        assert "by_role" in pattern_data


if __name__ == "__main__":
    pytest.main([__file__])