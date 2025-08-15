"""
Tests for Enhanced Pattern Memory System (Phase 2).

Tests the enhanced PatternMemory class with comprehensive insights,
pattern evolution tracking, and export/import functionality.
"""

import pytest
import tempfile
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

from kirolinter.memory.pattern_memory import PatternMemory


class TestEnhancedPatternMemory:
    """Test enhanced PatternMemory functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def pattern_memory(self):
        """Create PatternMemory instance with Redis-only mode."""
        from kirolinter.memory.pattern_memory import create_pattern_memory
        return create_pattern_memory(redis_only=True)
    
    def test_pattern_evolution_tracking(self, pattern_memory):
        """Test pattern evolution tracking over time."""
        repo_path = "/test/repo"
        pattern_type = "naming_conventions"
        
        # Store initial pattern
        initial_pattern = {
            "variables": {"snake_case": 10, "camelCase": 2},
            "confidence": 0.8
        }
        pattern_memory.store_pattern(repo_path, pattern_type, initial_pattern, 0.8)
        
        # Update pattern (simulating evolution)
        updated_pattern = {
            "variables": {"snake_case": 15, "camelCase": 1},
            "confidence": 0.9
        }
        pattern_memory.store_pattern(repo_path, pattern_type, updated_pattern, 0.9)
        
        # Get evolution data
        evolution = pattern_memory.get_pattern_evolution(repo_path, pattern_type, 30)
        
        assert evolution["pattern_type"] == pattern_type
        assert evolution["total_changes"] >= 1
        assert len(evolution["confidence_trend"]) >= 1
    
    def test_comprehensive_insights(self, pattern_memory):
        """Test comprehensive insights generation."""
        repo_path = "/test/repo"
        
        # Store various types of data
        pattern_memory.store_pattern(repo_path, "naming", {"style": "snake_case"}, 0.8)
        pattern_memory.track_issue_pattern(repo_path, "style", "E501", "medium")
        pattern_memory.record_fix_outcome(repo_path, "style", "line_length", True, 0.5)
        
        # Get comprehensive insights
        insights = pattern_memory.get_comprehensive_insights(repo_path)
        
        assert "team_patterns" in insights
        assert "issue_trends" in insights
        assert "fix_success_rates" in insights
        assert "learning_analytics" in insights
        assert "pattern_confidence_summary" in insights
        assert "recommendations" in insights
        
        # Check that recommendations are generated
        assert isinstance(insights["recommendations"], list)
    
    def test_pattern_export_import(self, pattern_memory):
        """Test pattern export and import functionality."""
        repo_path = "/test/repo"
        
        # Store test patterns
        pattern_memory.store_pattern(repo_path, "naming", {"style": "snake_case"}, 0.8)
        pattern_memory.store_pattern(repo_path, "imports", {"style": "from_import"}, 0.7)
        
        # Export patterns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        try:
            success = pattern_memory.export_patterns(repo_path, export_file)
            assert success
            assert os.path.exists(export_file)
            
            # Verify export content
            with open(export_file, 'r') as f:
                export_data = json.load(f)
            
            assert "team_patterns" in export_data
            assert len(export_data["team_patterns"]) == 2
            
            # Test import (create new instance)
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                new_db_path = f.name
            
            try:
                from kirolinter.memory.pattern_memory import create_pattern_memory
                new_memory = create_pattern_memory(redis_only=True)
                import_success = new_memory.import_patterns(repo_path, export_file)
                assert import_success
                
                # Verify imported patterns
                imported_patterns = new_memory.get_team_patterns(repo_path)
                assert len(imported_patterns) == 2
                
            finally:
                if os.path.exists(new_db_path):
                    os.unlink(new_db_path)
                    
        finally:
            if os.path.exists(export_file):
                os.unlink(export_file)
    
    def test_data_anonymization_validation(self, pattern_memory):
        """Test that sensitive data is properly anonymized."""
        repo_path = "/test/repo"
        
        # Pattern with sensitive data
        sensitive_pattern = {
            "examples": [
                "password = 'secret123'",
                "api_key = 'sk-1234567890abcdef'",
                "email = 'user@example.com'"
            ],
            "code_samples": {
                "auth": "token = 'bearer abc123def456'"
            }
        }
        
        # Store pattern (should be anonymized)
        success = pattern_memory.store_pattern(repo_path, "security", sensitive_pattern, 0.5)
        assert success
        
        # Retrieve and verify anonymization
        patterns = pattern_memory.get_team_patterns(repo_path, "security")
        assert len(patterns) == 1
        
        pattern_data = patterns[0]["pattern_data"]
        
        # Check that sensitive data was anonymized
        examples_str = str(pattern_data.get("examples", []))
        assert "secret123" not in examples_str
        assert "sk-1234567890abcdef" not in examples_str
        assert "user@example.com" not in examples_str
        assert "<REDACTED>" in examples_str
    
    def test_pattern_confidence_updates(self, pattern_memory):
        """Test pattern confidence score updates."""
        repo_path = "/test/repo"
        pattern_type = "naming"
        
        # Store initial pattern
        pattern_memory.store_pattern(repo_path, pattern_type, {"style": "snake_case"}, 0.5)
        
        # Update confidence
        success = pattern_memory.update_confidence(repo_path, pattern_type, 0.8)
        assert success
        
        # Verify update
        patterns = pattern_memory.get_team_patterns(repo_path, pattern_type)
        assert len(patterns) == 1
        assert patterns[0]["confidence"] == 0.8
    
    def test_cleanup_old_data(self, pattern_memory):
        """Test cleanup of old data."""
        repo_path = "/test/repo"
        
        # Store some test data
        pattern_memory.record_fix_outcome(repo_path, "style", "fix1", True, 0.5)
        pattern_memory.record_learning_session(repo_path, "test", 1, 1)
        
        # Cleanup with very short retention (should remove data)
        success = pattern_memory.cleanup_old_data(days_to_keep=0)
        assert success
        
        # Verify data was cleaned up
        success_rates = pattern_memory.get_fix_success_rates(repo_path)
        analytics = pattern_memory.get_learning_analytics(repo_path)
        
        # Data should be cleaned up
        assert len(success_rates) == 0
        assert analytics["total_sessions"] == 0
    
    def test_learning_change_tracking(self, pattern_memory):
        """Test learning change tracking and audit trail."""
        repo_path = "/test/repo"
        pattern_type = "naming"
        
        # Record a learning change
        before_data = '{"old": "pattern"}'
        after_data = '{"new": "pattern"}'
        reason = "Pattern updated based on new commits"
        
        success = pattern_memory.record_learning_change(
            repo_path, pattern_type, before_data, after_data, reason
        )
        assert success
        
        # Get pattern evolution to verify change was recorded
        evolution = pattern_memory.get_pattern_evolution(repo_path, pattern_type, 30)
        assert evolution["total_changes"] >= 1
    
    def test_anonymization_validation_failure(self, pattern_memory):
        """Test that patterns with failed anonymization are rejected."""
        repo_path = "/test/repo"
        
        # Mock the anonymization validation to fail
        original_validate = pattern_memory.anonymizer.validate_anonymization
        pattern_memory.anonymizer.validate_anonymization = lambda x: False
        
        try:
            # Attempt to store pattern (should fail due to validation)
            success = pattern_memory.store_pattern(
                repo_path, "test", {"data": "test"}, 0.5
            )
            assert not success  # Should fail validation
            
            # Verify no pattern was stored
            patterns = pattern_memory.get_team_patterns(repo_path, "test")
            assert len(patterns) == 0
            
        finally:
            # Restore original validation
            pattern_memory.anonymizer.validate_anonymization = original_validate
    
    def test_pattern_frequency_filtering(self, pattern_memory):
        """Test that low-frequency patterns are handled correctly."""
        repo_path = "/test/repo"
        
        # Store pattern with low frequency
        low_freq_pattern = {"frequency": 1, "data": "test"}
        pattern_memory.store_pattern(repo_path, "low_freq", low_freq_pattern, 0.3)
        
        # Store pattern with high frequency
        high_freq_pattern = {"frequency": 10, "data": "test"}
        pattern_memory.store_pattern(repo_path, "high_freq", high_freq_pattern, 0.8)
        
        # Get patterns with minimum confidence filter
        high_conf_patterns = pattern_memory.get_team_patterns(repo_path, min_confidence=0.6)
        all_patterns = pattern_memory.get_team_patterns(repo_path, min_confidence=0.0)
        
        # Should filter out low confidence pattern
        assert len(high_conf_patterns) == 1
        assert len(all_patterns) == 2
        assert high_conf_patterns[0]["pattern_type"] == "high_freq"


if __name__ == "__main__":
    pytest.main([__file__])