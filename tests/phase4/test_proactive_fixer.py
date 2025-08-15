"""
Tests for Phase 4 Proactive Fixer Agent.

Tests safety-first fix application, validation, and outcome learning.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from kirolinter.agents.fixer import FixerAgent
from kirolinter.models.suggestion import Suggestion


class TestProactiveFixer:
    """Test proactive fixer agent capabilities."""
    
    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch('kirolinter.agents.fixer.get_chat_model') as mock:
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
                "pattern_type": "fix_outcome",
                "pattern_data": {"success": True},
                "confidence": 1.0
            }
        ]
        memory.store_pattern.return_value = True
        return memory
    
    @pytest.fixture
    def safe_suggestion(self, temp_repo_dir):
        """Create a safe suggestion for testing."""
        return Suggestion(
            issue_id="unused_import",
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            fix_type="delete",
            suggested_code="",
            confidence=0.95
        )
    
    @pytest.fixture
    def unsafe_suggestion(self, temp_repo_dir):
        """Create an unsafe suggestion for testing."""
        return Suggestion(
            issue_id="dangerous_fix",
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            fix_type="replace",
            suggested_code="exec('malicious code')",
            confidence=0.95
        )
    
    def test_fix_validation(self, temp_repo_dir, mock_memory, safe_suggestion, unsafe_suggestion):
        """Test comprehensive fix safety validation."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        # Test safe suggestion
        assert fixer._validate_fix(safe_suggestion) is True
        
        # Test unsafe suggestion (contains dangerous pattern)
        assert fixer._validate_fix(unsafe_suggestion) is False
        
        # Test suggestion with invalid fix type
        invalid_suggestion = Suggestion(
            issue_id="test",
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            fix_type="dangerous_operation",
            suggested_code="safe code",
            confidence=0.95
        )
        assert fixer._validate_fix(invalid_suggestion) is False
        
        # Test suggestion with too much code
        large_suggestion = Suggestion(
            issue_id="test",
            file_path=os.path.join(temp_repo_dir, "test_file.py"),
            line_number=1,
            fix_type="replace",
            suggested_code="x" * 2000,  # Too large
            confidence=0.95
        )
        assert fixer._validate_fix(large_suggestion) is False
    
    def test_syntax_checking(self, temp_repo_dir, mock_memory):
        """Test Python syntax validation."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        # Valid Python code
        assert fixer._check_syntax("def test(): pass") is True
        
        # Invalid Python code
        assert fixer._check_syntax("def test( pass") is False
        
        # Empty code
        assert fixer._check_syntax("") is True
    
    def test_backup_creation(self, temp_repo_dir, mock_memory):
        """Test automatic backup creation."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        test_file = os.path.join(temp_repo_dir, "test_file.py")
        
        # Test backup creation
        success = fixer._backup_file(test_file)
        assert success is True
        
        # Verify backup directory was created
        backup_dir = os.path.join(temp_repo_dir, ".kirolinter_backups")
        assert os.path.exists(backup_dir)
        
        # Verify backup file exists
        backups = os.listdir(backup_dir)
        assert len(backups) == 1
        assert backups[0].startswith("test_file.py.")
        assert backups[0].endswith(".backup")
    
    def test_safe_fix_application(self, temp_repo_dir, mock_memory, safe_suggestion):
        """Test safety-first fix application."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        # Mock reviewer for risk assessment
        with patch('kirolinter.agents.reviewer.ReviewerAgent') as mock_reviewer_class:
            mock_reviewer = Mock()
            mock_reviewer.assess_risk.return_value = 0.3  # Low risk
            mock_reviewer_class.return_value = mock_reviewer
            
            # Apply fixes
            applied = fixer.apply_fixes([safe_suggestion], auto_apply=True)
            
            # Should have applied the safe fix
            assert len(applied) == 1
            assert applied[0] == "unused_import"
            
            # Verify pattern was stored
            mock_memory.store_pattern.assert_called()
    
    def test_high_risk_fix_rejection(self, temp_repo_dir, mock_memory, safe_suggestion):
        """Test that high-risk fixes are rejected."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        # Mock reviewer to return high risk
        with patch('kirolinter.agents.reviewer.ReviewerAgent') as mock_reviewer_class:
            mock_reviewer = Mock()
            mock_reviewer.assess_risk.return_value = 0.8  # High risk
            mock_reviewer_class.return_value = mock_reviewer
            
            # Apply fixes
            applied = fixer.apply_fixes([safe_suggestion], auto_apply=True)
            
            # Should not have applied the high-risk fix
            assert len(applied) == 0
    
    def test_rollback_functionality(self, temp_repo_dir, mock_memory):
        """Test intelligent rollback with backup restoration."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        fixer.repo_path = temp_repo_dir
        
        test_file = os.path.join(temp_repo_dir, "test_file.py")
        original_content = "original content"
        
        # Write original content
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Create backup
        fixer._backup_file(test_file)
        
        # Modify file
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # Test rollback
        fixer.rollback_fix("test_issue", test_file)
        
        # Verify file was restored
        with open(test_file, 'r') as f:
            restored_content = f.read()
        
        assert restored_content == original_content
        
        # Verify rollback pattern was stored
        mock_memory.store_pattern.assert_called()
    
    def test_outcome_learning(self, temp_repo_dir, mock_memory):
        """Test fix outcome tracking and learning."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        fixer.repo_path = temp_repo_dir
        
        # Test successful fix learning
        fixer.learn_from_fixes("test_issue", success=True, feedback="Great fix!")
        
        # Verify outcome was stored
        mock_memory.store_pattern.assert_called_with(
            temp_repo_dir,
            "fix_outcome",
            {
                "issue_id": "test_issue",
                "success": True,
                "feedback": "Great fix!",
                "timestamp": pytest.approx(mock_memory.store_pattern.call_args[0][2]["timestamp"], abs=10)
            },
            1.0
        )
    
    def test_adaptive_strategy_optimization(self, temp_repo_dir, mock_memory):
        """Test adaptive fix strategy optimization."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        fixer.repo_path = temp_repo_dir
        
        # Mock successful outcomes
        mock_memory.get_team_patterns.return_value = [
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": False}}
        ]
        
        initial_threshold = fixer.confidence_threshold
        
        # Optimize strategy
        fixer._optimize_fix_strategy()
        
        # Threshold should be adjusted based on success rate (67% success)
        assert fixer.confidence_threshold != initial_threshold
        
        # With 67% success rate, threshold should be slightly lower than default
        assert fixer.confidence_threshold < 0.9
    
    def test_fix_type_application(self, temp_repo_dir, mock_memory):
        """Test different fix type applications."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        
        test_file = os.path.join(temp_repo_dir, "test_file.py")
        
        # Test replace fix
        replace_suggestion = Suggestion(
            issue_id="replace_test",
            file_path=test_file,
            line_number=1,
            fix_type="replace",
            suggested_code="# Fixed import",
            confidence=0.95
        )
        
        # Create backup first
        fixer._backup_file(test_file)
        
        # Apply replace fix
        success = fixer._apply_replace_fix(replace_suggestion)
        assert success is True
        
        # Verify file was modified
        with open(test_file, 'r') as f:
            lines = f.readlines()
        
        assert lines[0].strip() == "# Fixed import"
    
    def test_confidence_threshold_adaptation(self, temp_repo_dir, mock_memory):
        """Test that confidence threshold adapts to success rates."""
        fixer = FixerAgent(memory=mock_memory, verbose=True)
        fixer.repo_path = temp_repo_dir
        
        # Test with high success rate
        mock_memory.get_team_patterns.return_value = [
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": True}}
        ]
        
        fixer._optimize_fix_strategy()
        high_success_threshold = fixer.confidence_threshold
        
        # Test with low success rate
        mock_memory.get_team_patterns.return_value = [
            {"pattern_data": {"success": False}},
            {"pattern_data": {"success": False}},
            {"pattern_data": {"success": True}},
            {"pattern_data": {"success": False}}
        ]
        
        fixer._optimize_fix_strategy()
        low_success_threshold = fixer.confidence_threshold
        
        # High success rate should result in lower threshold (more aggressive)
        # Low success rate should result in higher threshold (more conservative)
        assert high_success_threshold < low_success_threshold


if __name__ == "__main__":
    pytest.main([__file__])