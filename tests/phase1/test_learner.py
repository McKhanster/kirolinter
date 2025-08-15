"""
Unit tests for LearnerAgent system.

Tests commit analysis, pattern extraction, and team style adaptation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from collections import Counter

from kirolinter.agents.learner import LearnerAgent
from kirolinter.models.config import Config


class TestLearnerAgent:
    """Test LearnerAgent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.learner = LearnerAgent(verbose=True)
        
        # Mock Git repository for testing
        self.mock_repo_path = "/test/repo"
        self.mock_config = Config()
        
        # Ensure config has team_style structure
        if not hasattr(self.mock_config, 'team_style'):
            self.mock_config.team_style = {
                'naming_conventions': {'variables': 'unknown', 'functions': 'unknown'},
                'import_organization': {'preferred_style': 'unknown'},
                'formatting': {'indentation': 'unknown'}
            }
    
    def test_initialization_with_llm(self):
        """Test LearnerAgent initialization with LLM."""
        learner = LearnerAgent(model="test-model", provider="test", verbose=True)
        assert learner.verbose is True
        assert learner.pattern_memory is not None
        assert learner.min_pattern_frequency == 3
        assert learner.min_confidence_threshold == 0.6
    
    def test_initialization_without_git(self):
        """Test LearnerAgent initialization when Git is not available."""
        with patch('kirolinter.agents.learner.GIT_AVAILABLE', False):
            learner = LearnerAgent()
            result = learner.learn_from_commits("/test/repo", Config())
            assert result["error"] == "GitPython not available"
            assert result["patterns_learned"] == 0
    
    @patch('kirolinter.agents.learner.Repo')
    def test_learn_from_commits_success(self, mock_repo_class):
        """Test successful commit analysis and pattern learning."""
        # Mock Git repository and commits
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Create mock commits with Python file changes
        mock_commits = []
        for i in range(5):
            mock_commit = MagicMock()
            mock_commit.hexsha = f"abc123{i}"
            mock_commit.parents = []  # Not a merge commit
            mock_commit.stats.files = {"test_file.py": {"insertions": 10, "deletions": 2}}
            mock_commits.append(mock_commit)
        
        mock_repo.iter_commits.return_value = mock_commits
        
        # Mock file content retrieval
        with patch.object(self.learner, '_get_file_content_from_commit') as mock_get_content:
            mock_get_content.return_value = """
def test_function():
    variable_name = "test"
    another_var = 42
    return variable_name + str(another_var)

import os
from pathlib import Path
"""
            
            # Mock pattern memory storage
            with patch.object(self.learner.pattern_memory, 'store_pattern') as mock_store:
                mock_store.return_value = True
                
                # Run learning
                result = self.learner.learn_from_commits(self.mock_repo_path, self.mock_config)
                
                # Verify results
                assert result["commits_analyzed"] == 5
                assert result["patterns_found"] > 0
                assert result["patterns_stored"] >= 0
                assert "patterns" in result
    
    @patch('kirolinter.agents.learner.Repo')
    def test_learn_from_commits_invalid_repo(self, mock_repo_class):
        """Test handling of invalid Git repository."""
        from git import InvalidGitRepositoryError
        mock_repo_class.side_effect = InvalidGitRepositoryError("Invalid repo")
        
        result = self.learner.learn_from_commits("/invalid/repo", self.mock_config)
        
        assert result["error"] == "Invalid Git repository"
        assert result["patterns_learned"] == 0
    
    def test_classify_naming_style(self):
        """Test naming style classification."""
        # Test snake_case
        assert self.learner._classify_naming_style("variable_name") == "snake_case"
        assert self.learner._classify_naming_style("test_function") == "snake_case"
        
        # Test camelCase
        assert self.learner._classify_naming_style("variableName") == "camelCase"
        assert self.learner._classify_naming_style("testFunction") == "camelCase"
        
        # Test PascalCase
        assert self.learner._classify_naming_style("ClassName") == "PascalCase"
        assert self.learner._classify_naming_style("TestClass") == "PascalCase"
        
        # Test UPPER_CASE
        assert self.learner._classify_naming_style("CONSTANT_VALUE") == "UPPER_CASE"
        assert self.learner._classify_naming_style("MAX_SIZE") == "UPPER_CASE"
        
        # Test other
        assert self.learner._classify_naming_style("mixedUP_style") == "other"
    
    def test_classify_import_style(self):
        """Test import style classification."""
        # Test from import
        assert self.learner._classify_import_style("from os import path") == "from_import"
        assert self.learner._classify_import_style("from pathlib import Path") == "from_import"
        
        # Test multiple import
        assert self.learner._classify_import_style("import os, sys, json") == "multiple_import"
        
        # Test single import
        assert self.learner._classify_import_style("import os") == "single_import"
        assert self.learner._classify_import_style("import json") == "single_import"
    
    def test_calculate_pattern_confidence(self):
        """Test pattern confidence calculation."""
        # High consistency, high frequency
        high_confidence_pattern = {
            'frequency': 50,
            'variables': Counter({'snake_case': 45, 'camelCase': 5}),
            'functions': Counter({'snake_case': 40, 'camelCase': 10})
        }
        confidence = self.learner._calculate_pattern_confidence(high_confidence_pattern)
        assert confidence > 0.7
        
        # Low consistency, low frequency
        low_confidence_pattern = {
            'frequency': 2,
            'variables': Counter({'snake_case': 1, 'camelCase': 1}),
            'functions': Counter({'snake_case': 1, 'camelCase': 1})
        }
        confidence = self.learner._calculate_pattern_confidence(low_confidence_pattern)
        assert confidence < 0.3
        
        # Below minimum frequency
        below_min_pattern = {
            'frequency': 1,
            'variables': Counter({'snake_case': 10})
        }
        confidence = self.learner._calculate_pattern_confidence(below_min_pattern)
        assert confidence == 0.0
    
    def test_adapt_team_style(self):
        """Test team style adaptation based on patterns."""
        # Create patterns with clear preferences
        patterns = {
            'naming_conventions': {
                'variables': Counter({'snake_case': 40, 'camelCase': 5}),
                'functions': Counter({'snake_case': 35, 'camelCase': 3}),
                'frequency': 45
            },
            'import_styles': {
                'patterns': Counter({'from_import': 25, 'single_import': 10}),
                'frequency': 35
            },
            'code_structure': {
                'indentation': Counter({'spaces': 50, 'tabs': 5}),
                'line_length': Counter({'normal': 40, 'long': 10}),
                'frequency': 55
            }
        }
        
        # Adapt team style
        result = self.learner.adapt_team_style(self.mock_config, patterns)
        
        # Verify adaptations
        assert result["success"] is True
        assert result["adaptations_made"] > 0
        assert len(result["changes"]) > 0
        
        # Verify config updates
        assert self.mock_config.team_style['naming_conventions']['variables'] == 'snake_case'
        assert self.mock_config.team_style['naming_conventions']['functions'] == 'snake_case'
        assert self.mock_config.team_style['import_organization']['preferred_style'] == 'from_import'
        assert self.mock_config.team_style['formatting']['indentation'] == 'spaces'
    
    def test_adapt_team_style_no_patterns(self):
        """Test team style adaptation with no clear patterns."""
        empty_patterns = {}
        
        result = self.learner.adapt_team_style(self.mock_config, empty_patterns)
        
        assert result["success"] is True
        assert result["adaptations_made"] == 0
        assert len(result["changes"]) == 0
    
    def test_learn_from_analysis(self):
        """Test learning from analysis results."""
        analysis_result = {
            'repository_path': '/test/repo',
            'issues_by_type': {
                'style': 15,
                'security': 3,
                'performance': 1
            },
            'issues_by_severity': {
                'low': 10,
                'medium': 7,
                'high': 2,
                'critical': 0
            }
        }
        
        # Mock pattern memory methods
        with patch.object(self.learner.pattern_memory, 'track_issue_pattern') as mock_track:
            mock_track.return_value = True
            
            with patch.object(self.learner.pattern_memory, 'record_learning_session') as mock_record:
                mock_record.return_value = True
                
                result = self.learner.learn_from_analysis(analysis_result)
                
                # Verify learning results
                assert result["success"] is True
                assert result["patterns_learned"] == 3  # Three issue types
                assert len(result["insights"]) >= 0
                
                # Verify pattern tracking was called
                assert mock_track.call_count == 3
    
    def test_extract_team_patterns(self):
        """Test team pattern extraction from history results."""
        history_result = {
            'patterns': {
                'naming_conventions': {
                    'frequency': 50,
                    'variables': Counter({'snake_case': 45, 'camelCase': 5})
                },
                'import_styles': {
                    'frequency': 2,  # Below minimum frequency
                    'patterns': Counter({'from_import': 1, 'single_import': 1})
                }
            }
        }
        
        # Mock confidence calculation
        with patch.object(self.learner, '_calculate_pattern_confidence') as mock_calc:
            mock_calc.side_effect = [0.8, 0.3]  # High confidence, low confidence
            
            result = self.learner.extract_team_patterns(history_result)
            
            # Should only extract high-confidence patterns above threshold
            assert result["total_patterns"] == 1
            assert "naming_conventions" in result["patterns"]
            assert "import_styles" not in result["patterns"]  # Below confidence threshold
    
    def test_update_analysis_rules(self):
        """Test analysis rule updates based on patterns."""
        patterns_result = {
            'patterns': {
                'naming_conventions': {
                    'data': {
                        'variables': Counter({'snake_case': 40, 'camelCase': 5}),
                        'functions': Counter({'snake_case': 35, 'camelCase': 3})
                    },
                    'confidence': 0.8
                },
                'import_styles': {
                    'data': {
                        'patterns': Counter({'from_import': 25, 'single_import': 10})
                    },
                    'confidence': 0.7
                }
            }
        }
        
        result = self.learner.update_analysis_rules(patterns_result)
        
        assert result["success"] is True
        assert result["rules_updated"] == 2
        assert len(result["changes"]) == 2
        assert any("snake_case" in change for change in result["changes"])
        assert any("from" in change for change in result["changes"])
    
    def test_validate_rule_improvements(self):
        """Test rule improvement validation."""
        rules_result = {
            "success": True,
            "rules_updated": 3,
            "changes": [
                "Adjusted naming rules to prefer snake_case",
                "Adjusted import rules to prefer 'from' imports",
                "Updated indentation preference to spaces"
            ]
        }
        
        result = self.learner.validate_rule_improvements("/test/repo", rules_result)
        
        assert result["validation_passed"] is True
        assert result["rules_validated"] == 3
        assert len(result["improvements"]) == 3
    
    def test_validate_rule_improvements_failure(self):
        """Test rule improvement validation with failures."""
        rules_result = {
            "success": False,
            "rules_updated": 0,
            "changes": []
        }
        
        result = self.learner.validate_rule_improvements("/test/repo", rules_result)
        
        assert result["validation_passed"] is False
        assert result["rules_validated"] == 0
        assert len(result["improvements"]) == 0
    
    @patch('kirolinter.agents.learner.SCHEDULER_AVAILABLE', True)
    def test_start_periodic_learning(self):
        """Test starting periodic learning."""
        # Mock scheduler
        mock_scheduler = MagicMock()
        self.learner.scheduler = mock_scheduler
        
        success = self.learner.start_periodic_learning("/test/repo", 24)
        
        assert success is True
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
    
    @patch('kirolinter.agents.learner.SCHEDULER_AVAILABLE', False)
    def test_start_periodic_learning_no_scheduler(self):
        """Test starting periodic learning without scheduler."""
        success = self.learner.start_periodic_learning("/test/repo", 24)
        
        assert success is False
    
    def test_get_learning_status(self):
        """Test getting learning status for a repository."""
        repo_path = "/test/repo"
        
        # Mock pattern memory responses
        mock_patterns = [
            {"pattern_type": "naming", "updated_at": "2023-08-12T10:00:00"},
            {"pattern_type": "imports", "updated_at": "2023-08-12T11:00:00"}
        ]
        
        mock_analytics = {
            "total_sessions": 5,
            "total_patterns_learned": 10,
            "total_insights_generated": 3
        }
        
        with patch.object(self.learner.pattern_memory, 'get_team_patterns') as mock_get_patterns:
            mock_get_patterns.return_value = mock_patterns
            
            with patch.object(self.learner.pattern_memory, 'get_learning_analytics') as mock_get_analytics:
                mock_get_analytics.return_value = mock_analytics
                
                status = self.learner.get_learning_status(repo_path)
                
                assert status["repo_path"] == repo_path
                assert status["patterns_stored"] == 2
                assert status["learning_sessions"] == 5
                assert status["patterns_learned"] == 10
                assert status["insights_generated"] == 3
                assert status["periodic_learning_active"] is False
                assert status["last_learning_session"] == "2023-08-12T10:00:00"


class TestLearnerAgentIntegration:
    """Integration tests for LearnerAgent with realistic scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.learner = LearnerAgent(verbose=False)  # Reduce noise in tests
    
    @patch('kirolinter.agents.learner.Repo')
    def test_realistic_commit_analysis_workflow(self, mock_repo_class):
        """Test a realistic commit analysis workflow with mixed code styles."""
        # Mock repository with realistic commit history
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Create commits with different coding styles
        commits_data = [
            {
                "files": {"main.py": {}},
                "content": """
def calculate_total(item_list):
    total_amount = 0
    for item in item_list:
        total_amount += item.price
    return total_amount

import os
from pathlib import Path
"""
            },
            {
                "files": {"utils.py": {}},
                "content": """
def processData(dataList):
    resultValue = []
    for dataItem in dataList:
        resultValue.append(dataItem.value)
    return resultValue

import sys, json
"""
            },
            {
                "files": {"models.py": {}},
                "content": """
class UserModel:
    def __init__(self, user_name):
        self.user_name = user_name
        self.created_at = datetime.now()
    
    def get_display_name(self):
        return self.user_name.title()

from datetime import datetime
import logging
"""
            }
        ]
        
        # Mock commits
        mock_commits = []
        for i, commit_data in enumerate(commits_data):
            mock_commit = MagicMock()
            mock_commit.hexsha = f"commit{i}"
            mock_commit.parents = []
            mock_commit.stats.files = commit_data["files"]
            mock_commits.append(mock_commit)
        
        mock_repo.iter_commits.return_value = mock_commits
        
        # Mock file content retrieval
        def mock_get_content(commit, file_path):
            commit_index = int(commit.hexsha.replace("commit", ""))
            return commits_data[commit_index]["content"]
        
        with patch.object(self.learner, '_get_file_content_from_commit', side_effect=mock_get_content):
            # Mock pattern storage
            with patch.object(self.learner.pattern_memory, 'store_pattern') as mock_store:
                mock_store.return_value = True
                
                # Run learning
                config = Config()
                result = self.learner.learn_from_commits("/test/mixed-styles", config)
                
                # Verify mixed patterns were detected
                assert result["commits_analyzed"] == 3
                assert result["patterns_found"] > 0
                
                # Check that patterns contain both snake_case and camelCase
                patterns = result.get("patterns", {})
                if "naming_conventions" in patterns:
                    naming_data = patterns["naming_conventions"]
                    variables = naming_data.get("variables", Counter())
                    
                    # Should detect both styles
                    assert variables.get("snake_case", 0) > 0
                    assert variables.get("camelCase", 0) > 0
    
    def test_pattern_confidence_evolution(self):
        """Test how pattern confidence evolves with more data."""
        # Start with low confidence pattern
        low_confidence_pattern = {
            'frequency': 5,
            'variables': Counter({'snake_case': 3, 'camelCase': 2}),
            'functions': Counter({'snake_case': 3, 'camelCase': 2})
        }
        
        confidence_low = self.learner._calculate_pattern_confidence(low_confidence_pattern)
        
        # Add more consistent data
        high_confidence_pattern = {
            'frequency': 50,
            'variables': Counter({'snake_case': 45, 'camelCase': 5}),
            'functions': Counter({'snake_case': 40, 'camelCase': 10})
        }
        
        confidence_high = self.learner._calculate_pattern_confidence(high_confidence_pattern)
        
        # Confidence should increase with more consistent data
        assert confidence_high > confidence_low
        assert confidence_high > 0.7  # Should be high confidence
        assert confidence_low < 0.5   # Should be low confidence
    
    def test_team_style_adaptation_realistic_scenario(self):
        """Test team style adaptation with realistic mixed patterns."""
        config = Config()
        
        # Ensure config structure exists
        config.team_style = {
            'naming_conventions': {'variables': 'mixed', 'functions': 'mixed'},
            'import_organization': {'preferred_style': 'mixed'},
            'formatting': {'indentation': 'mixed'}
        }
        
        # Realistic patterns from a team transitioning to snake_case
        realistic_patterns = {
            'naming_conventions': {
                'variables': Counter({
                    'snake_case': 120,  # New preferred style
                    'camelCase': 30,    # Legacy style
                    'other': 5
                }),
                'functions': Counter({
                    'snake_case': 80,
                    'camelCase': 20,
                    'other': 2
                }),
                'frequency': 155
            },
            'import_styles': {
                'patterns': Counter({
                    'from_import': 60,
                    'single_import': 25,
                    'multiple_import': 10
                }),
                'frequency': 95
            },
            'code_structure': {
                'indentation': Counter({
                    'spaces': 140,
                    'tabs': 15
                }),
                'line_length': Counter({
                    'normal': 120,
                    'long': 35
                }),
                'frequency': 155
            }
        }
        
        # Adapt team style
        result = self.learner.adapt_team_style(config, realistic_patterns)
        
        # Verify successful adaptation
        assert result["success"] is True
        assert result["adaptations_made"] >= 3
        
        # Verify the dominant patterns were adopted
        assert config.team_style['naming_conventions']['variables'] == 'snake_case'
        assert config.team_style['naming_conventions']['functions'] == 'snake_case'
        assert config.team_style['import_organization']['preferred_style'] == 'from_import'
        assert config.team_style['formatting']['indentation'] == 'spaces'
        
        # Verify changes were logged
        changes = result["changes"]
        assert any('snake_case' in change for change in changes)
        assert any('from_import' in change for change in changes)
        assert any('spaces' in change for change in changes)