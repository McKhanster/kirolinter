"""
Unit tests for PatternMemory system.

Tests storage, retrieval, anonymization, and security features.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from kirolinter.memory.pattern_memory import PatternMemory, DataAnonymizer


class TestDataAnonymizer:
    """Test data anonymization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.anonymizer = DataAnonymizer()
    
    def test_anonymize_code_snippet_with_secrets(self):
        """Test anonymization of code snippets containing secrets."""
        code_with_secrets = """
        API_KEY = "sk-1234567890abcdef"
        password = "secret123"
        token = "xai-abcdef123456"
        email = "user@example.com"
        """
        
        anonymized = self.anonymizer.anonymize_code_snippet(code_with_secrets)
        
        # Verify secrets are masked
        assert "sk-1234567890abcdef" not in anonymized
        assert "secret123" not in anonymized
        assert "xai-abcdef123456" not in anonymized
        assert "user@example.com" not in anonymized
        assert "<REDACTED>" in anonymized
    
    def test_anonymize_code_snippet_without_secrets(self):
        """Test anonymization of clean code snippets."""
        clean_code = """
        def calculate_sum(a, b):
            return a + b
        
        result = calculate_sum(1, 2)
        """
        
        anonymized = self.anonymizer.anonymize_code_snippet(clean_code)
        
        # Verify code is unchanged
        assert anonymized == clean_code
    
    def test_anonymize_pattern_data(self):
        """Test anonymization of pattern data structures."""
        pattern_data = {
            "examples": [
                "password = 'secret123'",
                "def clean_function(): pass"
            ],
            "code_samples": {
                "bad": "API_KEY = 'sk-1234567890'",
                "good": "def good_function(): pass"
            },
            "description": "This pattern contains API_KEY = 'sensitive'"
        }
        
        anonymized = self.anonymizer.anonymize_pattern_data(pattern_data)
        
        # Verify secrets in examples are masked
        assert "secret123" not in str(anonymized["examples"])
        assert "sk-1234567890" not in str(anonymized["code_samples"])
        assert "sensitive" not in anonymized["description"]
        assert "<REDACTED>" in str(anonymized)
    
    def test_validate_anonymization_success(self):
        """Test successful anonymization validation."""
        clean_data = {
            "examples": ["def clean_function(): pass"],
            "pattern": "snake_case"
        }
        
        assert self.anonymizer.validate_anonymization(clean_data) is True
    
    def test_validate_anonymization_failure(self):
        """Test failed anonymization validation."""
        dirty_data = {
            "examples": ["password = 'secret123'"],
            "pattern": "snake_case"
        }
        
        assert self.anonymizer.validate_anonymization(dirty_data) is False
    
    def test_is_sensitive_file(self):
        """Test sensitive file detection."""
        # Test sensitive files
        assert self.anonymizer.is_sensitive_file(".env") is True
        assert self.anonymizer.is_sensitive_file("secrets.yaml") is True
        assert self.anonymizer.is_sensitive_file("config.json") is True
        assert self.anonymizer.is_sensitive_file("private.key") is True
        
        # Test normal files
        assert self.anonymizer.is_sensitive_file("main.py") is False
        assert self.anonymizer.is_sensitive_file("test_file.py") is False
        assert self.anonymizer.is_sensitive_file("README.md") is False


class TestPatternMemory:
    """Test PatternMemory storage and retrieval functionality."""
    
    def setup_method(self):
        """Set up test fixtures with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.memory = PatternMemory(db_path=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_store_and_retrieve_pattern(self):
        """Test basic pattern storage and retrieval."""
        repo_path = "/test/repo"
        pattern_type = "naming_conventions"
        pattern_data = {
            "variables": {"snake_case": 10, "camelCase": 2},
            "confidence": 0.8
        }
        
        # Store pattern
        success = self.memory.store_pattern(repo_path, pattern_type, pattern_data, 0.8)
        assert success is True
        
        # Retrieve pattern
        patterns = self.memory.retrieve_patterns(repo_path, pattern_type)
        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == pattern_type
        assert patterns[0]["confidence"] == 0.8
    
    def test_store_pattern_with_secrets(self):
        """Test pattern storage with automatic anonymization."""
        repo_path = "/test/repo"
        pattern_type = "security_test"
        pattern_data = {
            "examples": ["API_KEY = 'sk-1234567890'"],
            "description": "Pattern with secret"
        }
        
        # Store pattern (should be anonymized)
        success = self.memory.store_pattern(repo_path, pattern_type, pattern_data, 0.5)
        assert success is True
        
        # Retrieve and verify anonymization
        patterns = self.memory.retrieve_patterns(repo_path, pattern_type)
        assert len(patterns) == 1
        
        stored_data = patterns[0]["pattern_data"]
        assert "sk-1234567890" not in str(stored_data)
        assert "<REDACTED>" in str(stored_data)
    
    def test_update_confidence(self):
        """Test confidence score updates."""
        repo_path = "/test/repo"
        pattern_type = "test_pattern"
        pattern_data = {"test": "data"}
        
        # Store initial pattern
        self.memory.store_pattern(repo_path, pattern_type, pattern_data, 0.5)
        
        # Update confidence
        success = self.memory.update_confidence(repo_path, pattern_type, 0.9)
        assert success is True
        
        # Verify update
        patterns = self.memory.retrieve_patterns(repo_path, pattern_type)
        assert patterns[0]["confidence"] == 0.9
    
    def test_track_issue_pattern(self):
        """Test issue pattern tracking."""
        repo_path = "/test/repo"
        issue_type = "style"
        issue_rule = "E501"
        severity = "low"
        
        # Track issue pattern
        success = self.memory.track_issue_pattern(repo_path, issue_type, issue_rule, severity)
        assert success is True
        
        # Get trends
        trends = self.memory.get_issue_trends(repo_path)
        assert trends["total_patterns"] > 0
        assert len(trends["trending_issues"]) > 0
    
    def test_record_fix_outcome(self):
        """Test fix outcome recording."""
        repo_path = "/test/repo"
        issue_type = "style"
        fix_type = "auto_format"
        
        # Record successful fix
        success = self.memory.record_fix_outcome(
            repo_path, issue_type, fix_type, True, 0.8, {"notes": "test fix"}
        )
        assert success is True
        
        # Get success rates
        rates = self.memory.get_fix_success_rates(repo_path)
        assert fix_type in rates
        assert rates[fix_type]["success_rate"] == 1.0
    
    def test_record_learning_session(self):
        """Test learning session recording."""
        repo_path = "/test/repo"
        session_type = "commit_analysis"
        
        # Record learning session
        success = self.memory.record_learning_session(
            repo_path, session_type, 5, 3, {"commits": 10}
        )
        assert success is True
        
        # Get analytics
        analytics = self.memory.get_learning_analytics(repo_path)
        assert analytics["total_sessions"] == 1
        assert analytics["total_patterns_learned"] == 5
        assert analytics["total_insights_generated"] == 3
    
    def test_invalid_confidence_score(self):
        """Test handling of invalid confidence scores."""
        repo_path = "/test/repo"
        pattern_type = "test"
        pattern_data = {"test": "data"}
        
        # Test invalid confidence scores
        assert self.memory.store_pattern(repo_path, pattern_type, pattern_data, -0.1) is False
        assert self.memory.store_pattern(repo_path, pattern_type, pattern_data, 1.1) is False
        assert self.memory.update_confidence(repo_path, pattern_type, 2.0) is False
    
    def test_empty_input_handling(self):
        """Test handling of empty or invalid inputs."""
        # Test empty inputs
        assert self.memory.store_pattern("", "test", {"data": "test"}, 0.5) is False
        assert self.memory.store_pattern("/repo", "", {"data": "test"}, 0.5) is False
        assert self.memory.store_pattern("/repo", "test", {}, 0.5) is False
    
    def test_export_patterns(self):
        """Test pattern export functionality."""
        repo_path = "/test/repo"
        
        # Store some test patterns
        self.memory.store_pattern(repo_path, "naming", {"test": "data"}, 0.8)
        self.memory.track_issue_pattern(repo_path, "style", "E501", "low")
        
        # Export patterns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
        
        success = self.memory.export_patterns(repo_path, export_path)
        assert success is True
        
        # Verify export content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert exported_data["repo_path"] == repo_path
        assert "team_patterns" in exported_data
        assert "issue_trends" in exported_data
        
        # Clean up
        Path(export_path).unlink(missing_ok=True)


class TestPatternMemoryIntegration:
    """Integration tests for PatternMemory with real-world scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.memory = PatternMemory(db_path=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_realistic_pattern_learning_workflow(self):
        """Test a realistic pattern learning workflow."""
        repo_path = "/project/flask-app"
        
        # Simulate learning naming conventions
        naming_patterns = {
            "variables": {"snake_case": 45, "camelCase": 5},
            "functions": {"snake_case": 30, "camelCase": 2},
            "frequency": 50
        }
        
        success = self.memory.store_pattern(
            repo_path, "naming_conventions", naming_patterns, 0.85
        )
        assert success is True
        
        # Simulate tracking common issues
        common_issues = [
            ("style", "E501", "low"),  # Line too long
            ("style", "W292", "low"),  # No newline at end of file
            ("security", "B101", "high"),  # Use of assert
        ]
        
        for issue_type, rule, severity in common_issues:
            self.memory.track_issue_pattern(repo_path, issue_type, rule, severity)
        
        # Simulate fix outcomes
        fix_outcomes = [
            ("style", "auto_format", True, 0.9),
            ("style", "manual_fix", True, 0.7),
            ("security", "code_review", False, -0.2),
        ]
        
        for issue_type, fix_type, success, feedback in fix_outcomes:
            self.memory.record_fix_outcome(repo_path, issue_type, fix_type, success, feedback)
        
        # Verify comprehensive data retrieval
        patterns = self.memory.get_team_patterns(repo_path)
        assert len(patterns) == 1
        assert patterns[0]["confidence"] == 0.85
        
        trends = self.memory.get_issue_trends(repo_path)
        assert trends["total_patterns"] == 3
        assert "style" in trends["issue_distribution"]
        assert "security" in trends["issue_distribution"]
        
        success_rates = self.memory.get_fix_success_rates(repo_path)
        assert "auto_format" in success_rates
        assert success_rates["auto_format"]["success_rate"] == 1.0
        assert success_rates["code_review"]["success_rate"] == 0.0
    
    def test_pattern_evolution_over_time(self):
        """Test pattern evolution and confidence updates over time."""
        repo_path = "/project/evolving"
        pattern_type = "naming_conventions"
        
        # Initial pattern with low confidence
        initial_pattern = {"variables": {"camelCase": 10, "snake_case": 5}}
        self.memory.store_pattern(repo_path, pattern_type, initial_pattern, 0.4)
        
        # Updated pattern with higher confidence (team switched to snake_case)
        updated_pattern = {"variables": {"snake_case": 25, "camelCase": 10}}
        self.memory.store_pattern(repo_path, pattern_type, updated_pattern, 0.7)
        
        # Final pattern with high confidence
        final_pattern = {"variables": {"snake_case": 50, "camelCase": 10}}
        self.memory.store_pattern(repo_path, pattern_type, final_pattern, 0.9)
        
        # Verify final state
        patterns = self.memory.get_team_patterns(repo_path, min_confidence=0.8)
        assert len(patterns) == 1
        assert patterns[0]["confidence"] == 0.9
        assert patterns[0]["frequency"] == 3  # Updated 3 times
    
    @patch('kirolinter.memory.pattern_memory.logging')
    def test_error_handling_and_logging(self, mock_logging):
        """Test error handling and security logging."""
        # Test with corrupted database path
        bad_memory = PatternMemory(db_path="/invalid/path/db.sqlite")
        
        # Should handle gracefully and log errors
        success = bad_memory.store_pattern("/repo", "test", {"data": "test"}, 0.5)
        assert success is False
        
        # Test anonymization failure logging
        pattern_with_secrets = {
            "examples": ["password = 'secret123'"],
            "code": "API_KEY = 'sk-1234567890'"
        }
        
        # This should succeed but log anonymization events
        success = self.memory.store_pattern("/repo", "test", pattern_with_secrets, 0.5)
        assert success is True