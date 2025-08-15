"""
Tests for Adaptive Learner Agent (Phase 2).

Tests the enhanced Learner Agent with commit history analysis,
team style evolution tracking, and rule optimization capabilities.
"""

import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from kirolinter.agents.learner import LearnerAgent
from kirolinter.models.config import Config


class TestAdaptiveLearner:
    """Test enhanced Learner Agent functionality."""
    
    @pytest.fixture
    def temp_repo_dir(self):
        """Create temporary repository directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def learner_agent(self):
        """Create Learner Agent instance for testing."""
        return LearnerAgent(verbose=False)
    
    @pytest.fixture
    def mock_git_repo(self):
        """Create mock Git repository for testing."""
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.parents = []  # Not a merge commit
        mock_commit.stats.files = {"test.py": {"insertions": 5, "deletions": 2}}
        
        # Mock tree access for file content
        mock_blob = Mock()
        mock_blob.data_stream.read.return_value = b"""
def calculate_total(items):
    total_sum = 0
    for item in items:
        total_sum += item.price
    return total_sum

import os
from pathlib import Path
"""
        mock_commit.tree = {"test.py": mock_blob}
        
        mock_repo.iter_commits.return_value = [mock_commit]
        return mock_repo
    
    def test_commit_history_analysis(self, learner_agent, mock_git_repo):
        """Test commit history analysis and pattern extraction."""
        repo_path = "/test/repo"
        config = Config()
        
        with patch('kirolinter.agents.learner.Repo', return_value=mock_git_repo):
            result = learner_agent.learn_from_commits(repo_path, config)
        
        assert "commits_analyzed" in result
        assert "patterns_found" in result
        assert "patterns_stored" in result
        assert result["commits_analyzed"] > 0
        
        # Should have extracted patterns
        patterns = result.get("patterns", {})
        assert "naming_conventions" in patterns
        assert "import_styles" in patterns
        assert "code_structure" in patterns
    
    def test_pattern_extraction_from_code(self, learner_agent):
        """Test pattern extraction from code content."""
        # Test code with various patterns
        test_code = """
def calculate_user_total(user_items):
    total_amount = 0
    for item in user_items:
        total_amount += item.price
    return total_amount

class UserManager:
    def __init__(self):
        self.user_count = 0
    
    def addUser(self, user):  # Mixed naming style
        self.user_count += 1

import os
import sys
from pathlib import Path
"""
        
        patterns = {
            'naming_conventions': {'variables': {}, 'functions': {}, 'frequency': 0},
            'import_styles': {'organization': {}, 'patterns': {}, 'frequency': 0},
            'code_structure': {'indentation': {}, 'line_length': {}, 'frequency': 0}
        }
        
        learner_agent._analyze_file_patterns(test_code, patterns)
        
        # Check naming pattern detection
        naming = patterns['naming_conventions']
        assert 'snake_case' in str(naming['variables']) or 'snake_case' in str(naming['functions'])
        
        # Check import pattern detection
        imports = patterns['import_styles']
        assert len(imports['patterns']) > 0
    
    def test_naming_style_classification(self, learner_agent):
        """Test naming style classification."""
        test_cases = [
            ("user_name", "snake_case"),
            ("userName", "camelCase"),
            ("UserName", "PascalCase"),
            ("USER_NAME", "UPPER_CASE"),
            ("user123", "other")
        ]
        
        for name, expected_style in test_cases:
            style = learner_agent._classify_naming_style(name)
            assert style == expected_style, f"Expected {expected_style} for {name}, got {style}"
    
    def test_import_style_classification(self, learner_agent):
        """Test import style classification."""
        test_cases = [
            ("import os", "single_import"),
            ("import os, sys", "multiple_import"),
            ("from pathlib import Path", "from_import")
        ]
        
        for import_line, expected_style in test_cases:
            style = learner_agent._classify_import_style(import_line)
            assert style == expected_style
    
    def test_pattern_confidence_calculation(self, learner_agent):
        """Test pattern confidence score calculation."""
        # High frequency, high consistency pattern
        high_conf_pattern = {
            'frequency': 20,
            'variables': {'snake_case': 18, 'camelCase': 2},
            'functions': {'snake_case': 19, 'camelCase': 1}
        }
        
        confidence = learner_agent._calculate_pattern_confidence(high_conf_pattern)
        assert confidence > 0.3  # Should be reasonable confidence (capped at 0.95 * 0.85)
        
        # Low frequency pattern
        low_freq_pattern = {
            'frequency': 2,
            'variables': {'snake_case': 2}
        }
        
        confidence = learner_agent._calculate_pattern_confidence(low_freq_pattern)
        assert confidence == 0.0  # Below minimum frequency threshold
        
        # Inconsistent pattern
        inconsistent_pattern = {
            'frequency': 10,
            'variables': {'snake_case': 5, 'camelCase': 5}
        }
        
        confidence = learner_agent._calculate_pattern_confidence(inconsistent_pattern)
        assert confidence < 0.6  # Should be lower due to inconsistency
    
    def test_team_style_adaptation(self, learner_agent):
        """Test team style adaptation based on patterns."""
        config = Config()
        config.team_style = {
            'naming_conventions': {'variables': 'unknown', 'functions': 'unknown'},
            'import_organization': {'preferred_style': 'unknown'},
            'formatting': {'indentation': 'unknown'}
        }
        
        patterns = {
            'naming_conventions': {
                'variables': {'snake_case': 15, 'camelCase': 2},
                'functions': {'snake_case': 12, 'camelCase': 1}
            },
            'import_styles': {
                'patterns': {'from_import': 8, 'single_import': 3}
            },
            'code_structure': {
                'indentation': {'spaces': 20, 'tabs': 1}
            }
        }
        
        result = learner_agent.adapt_team_style(config, patterns)
        
        assert result["success"] is True
        assert result["adaptations_made"] > 0
        assert len(result["changes"]) > 0
        
        # Verify adaptations were applied
        assert config.team_style['naming_conventions']['variables'] == 'snake_case'
        assert config.team_style['naming_conventions']['functions'] == 'snake_case'
        assert config.team_style['import_organization']['preferred_style'] == 'from_import'
        assert config.team_style['formatting']['indentation'] == 'spaces'
    
    def test_team_style_evolution_tracking(self, learner_agent):
        """Test team style evolution tracking."""
        repo_path = "/test/repo"
        
        # Mock pattern memory to return evolution data
        mock_evolution = {
            'naming_conventions': {
                'total_changes': 3,
                'changes': [
                    {'reason': 'Pattern updated', 'created_at': '2024-01-01T10:00:00'},
                    {'reason': 'Confidence increased', 'created_at': '2024-01-02T10:00:00'},
                    {'reason': 'New pattern detected', 'created_at': '2024-01-03T10:00:00'}
                ],
                'confidence_trend': [
                    {'date': '2024-01-01T10:00:00', 'confidence_change': 0.1},
                    {'date': '2024-01-02T10:00:00', 'confidence_change': 0.2},
                    {'date': '2024-01-03T10:00:00', 'confidence_change': 0.3}
                ]
            }
        }
        
        with patch.object(learner_agent.pattern_memory, 'get_pattern_evolution', return_value=mock_evolution['naming_conventions']):
            result = learner_agent.track_team_style_evolution(repo_path, 30)
        
        assert result["repo_path"] == repo_path
        assert result["total_changes"] > 0
        assert "pattern_evolution" in result
        assert "trends" in result
        assert len(result["trends"]) >= 0
    
    def test_rule_optimization_based_on_feedback(self, learner_agent):
        """Test rule optimization based on user feedback."""
        repo_path = "/test/repo"
        
        # Mock success rates with some problematic rules
        mock_success_rates = {
            "unused_import": {
                "success_rate": 0.9,
                "total_attempts": 10,
                "avg_feedback": 0.5
            },
            "line_length": {
                "success_rate": 0.3,  # Low success rate
                "total_attempts": 8,
                "avg_feedback": 0.1
            },
            "naming_style": {
                "success_rate": 0.7,
                "total_attempts": 5,
                "avg_feedback": -0.4  # Negative feedback
            }
        }
        
        with patch.object(learner_agent.pattern_memory, 'get_fix_success_rates', return_value=mock_success_rates):
            result = learner_agent.optimize_rules_based_on_feedback(repo_path, {})
        
        assert result["repo_path"] == repo_path
        assert result["rules_analyzed"] == 3
        assert result["optimizations_identified"] >= 1  # Should identify problematic rules
        
        # Should have optimizations for low success rate and negative feedback
        optimizations = result["optimizations"]
        optimization_types = [opt["fix_type"] for opt in optimizations]
        assert "line_length" in optimization_types  # Low success rate
        assert "naming_style" in optimization_types  # Negative feedback
    
    def test_knowledge_synthesis(self, learner_agent):
        """Test knowledge synthesis from multiple sources."""
        repo_path = "/test/repo"
        
        # Mock data from different sources
        mock_patterns = [
            {"pattern_type": "naming", "confidence": 0.8},
            {"pattern_type": "imports", "confidence": 0.9}
        ]
        
        mock_success_rates = {
            "unused_import": {"success_rate": 0.9},
            "line_length": {"success_rate": 0.3}
        }
        
        mock_issue_trends = {
            "total_patterns": 5,
            "trending_issues": [
                {"issue_type": "style", "frequency": 10},
                {"issue_type": "security", "frequency": 5}
            ]
        }
        
        with patch.object(learner_agent.pattern_memory, 'get_team_patterns', return_value=mock_patterns), \
             patch.object(learner_agent.pattern_memory, 'get_fix_success_rates', return_value=mock_success_rates), \
             patch.object(learner_agent.pattern_memory, 'get_issue_trends', return_value=mock_issue_trends):
            
            result = learner_agent.synthesize_knowledge_from_sources(repo_path)
        
        assert result["repo_path"] == repo_path
        assert len(result["sources_analyzed"]) > 0
        assert len(result["insights"]) > 0
        assert len(result["recommendations"]) > 0
        assert 0.0 <= result["confidence_score"] <= 1.0
    
    def test_learning_from_analysis_results(self, learner_agent):
        """Test learning from analysis results."""
        analysis_result = {
            "repository_path": "/test/repo",
            "issues_by_type": {
                "style": 5,
                "security": 2,
                "performance": 1
            },
            "issues_by_severity": {
                "high": 3,
                "medium": 4,
                "low": 1
            }
        }
        
        result = learner_agent.learn_from_analysis(analysis_result)
        
        assert result["success"] is True
        assert result["patterns_learned"] > 0
        assert len(result["insights"]) >= 0
        
        # Should generate insight about high severity ratio
        if result["insights"]:
            insights_text = " ".join(result["insights"])
            # High severity ratio (3/8 = 37.5% > 20%) should trigger insight
            assert "severe" in insights_text.lower() or "high" in insights_text.lower()
    
    def test_enhanced_learning_status(self, learner_agent):
        """Test enhanced learning status reporting."""
        repo_path = "/test/repo"
        
        # Mock comprehensive data
        mock_patterns = [{"pattern_type": "test", "confidence": 0.8, "updated_at": "2024-01-01"}]
        mock_analytics = {"total_sessions": 5, "total_patterns_learned": 10, "total_insights_generated": 3}
        mock_insights = {
            "pattern_confidence_summary": {"naming": {"avg_confidence": 0.8}},
            "recommendations": ["Enable automated fixes", "Review low-confidence patterns"]
        }
        mock_evolution = {"total_changes": 2}
        
        with patch.object(learner_agent.pattern_memory, 'get_team_patterns', return_value=mock_patterns), \
             patch.object(learner_agent.pattern_memory, 'get_learning_analytics', return_value=mock_analytics), \
             patch.object(learner_agent.pattern_memory, 'get_comprehensive_insights', return_value=mock_insights), \
             patch.object(learner_agent, 'track_team_style_evolution', return_value=mock_evolution):
            
            status = learner_agent.get_learning_status(repo_path)
        
        assert status["repo_path"] == repo_path
        assert status["patterns_stored"] == 1
        assert status["learning_sessions"] == 5
        assert status["patterns_learned"] == 10
        assert status["insights_generated"] == 3
        assert "pattern_confidence_summary" in status
        assert "recent_evolution_changes" in status
        assert len(status["recommendations"]) == 2
    
    @patch('kirolinter.agents.learner.SCHEDULER_AVAILABLE', True)
    def test_periodic_learning_scheduling(self, learner_agent):
        """Test periodic learning scheduling."""
        repo_path = "/test/repo"
        
        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.running = False  # Not running initially
        learner_agent.scheduler = mock_scheduler
        
        # Test starting periodic learning
        success = learner_agent.start_periodic_learning(repo_path, interval_hours=12)
        assert success
        
        # Verify scheduler was called
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
        
        # Test stopping periodic learning
        success = learner_agent.stop_periodic_learning(repo_path)
        assert success
        
        # Verify job removal
        mock_scheduler.remove_job.assert_called_once()
    
    def test_git_unavailable_fallback(self, learner_agent):
        """Test fallback behavior when Git is unavailable."""
        repo_path = "/test/repo"
        config = Config()
        
        # Temporarily disable Git
        with patch('kirolinter.agents.learner.GIT_AVAILABLE', False):
            result = learner_agent.learn_from_commits(repo_path, config)
        
        assert "error" in result
        assert "GitPython not available" in result["error"]
        assert result["patterns_learned"] == 0
    
    def test_invalid_repository_handling(self, learner_agent):
        """Test handling of invalid Git repositories."""
        repo_path = "/invalid/repo"
        config = Config()
        
        with patch('kirolinter.agents.learner.Repo', side_effect=Exception("Invalid repository")):
            result = learner_agent.learn_from_commits(repo_path, config)
        
        assert "error" in result
        assert result["patterns_learned"] == 0


if __name__ == "__main__":
    pytest.main([__file__])