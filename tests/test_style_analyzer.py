"""
Unit tests for the team style analyzer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from tempfile import TemporaryDirectory
import os

from kirolinter.core.style_analyzer import CommitAnalyzer, TeamStyleAnalyzer


class TestCommitAnalyzer:
    """Test cases for commit analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CommitAnalyzer()
    
    def test_analyze_naming_conventions(self):
        """Test naming convention analysis from diff."""
        diff_text = """
+def calculate_total(items):
+    total_amount = 0
+    MAX_ITEMS = 100
+    for item in items:
+        total_amount += item.price
+    return total_amount
+
+class OrderProcessor:
+    def _validate_order(self, order):
+        return True
"""
        
        patterns = self.analyzer.analyze_commit_diff(diff_text)
        naming = patterns['naming_conventions']
        
        # Should detect snake_case for functions and variables
        assert 'snake_case' in naming['functions']
        assert 'snake_case' in naming['variables']
        assert 'UPPER_SNAKE_CASE' in naming['constants']
        assert 'PascalCase' in naming['classes']
        assert 'snake_case' in naming['private_methods']
    
    def test_analyze_code_structure(self):
        """Test code structure pattern analysis."""
        diff_text = """
+def process_order(order):
+    if not order:
+        return None
+    
+    items = [item for item in order.items if item.valid]
+    
+    try:
+        result = calculate_total(items)
+    except ValueError as e:
+        return None
+    
+    return result
"""
        
        patterns = self.analyzer.analyze_commit_diff(diff_text)
        structure = patterns['code_structure']
        
        # Should detect early returns and list comprehensions
        assert structure['return_style']['early_return'] > 0
        assert structure['comprehension_usage']['list_comprehension'] > 0
        assert structure['error_handling']['specific_except'] > 0
    
    def test_analyze_import_style(self):
        """Test import style analysis."""
        diff_text = """
+import os
+import sys
+from pathlib import Path
+from .utils import helper_function
+from typing import List, Dict
"""
        
        patterns = self.analyzer.analyze_commit_diff(diff_text)
        import_style = patterns['import_style']
        
        # Should detect both import types
        assert import_style['import_types']['direct_import'] > 0
        assert import_style['import_types']['from_import'] > 0
        assert import_style['from_imports']['relative'] > 0
        assert import_style['from_imports']['absolute'] > 0
    
    def test_classify_naming_style(self):
        """Test naming style classification."""
        assert self.analyzer._classify_naming_style('snake_case_name') == 'snake_case'
        assert self.analyzer._classify_naming_style('PascalCaseName') == 'PascalCase'
        assert self.analyzer._classify_naming_style('camelCaseName') == 'camelCase'
        assert self.analyzer._classify_naming_style('UPPER_SNAKE_CASE') == 'UPPER_SNAKE_CASE'
        assert self.analyzer._classify_naming_style('lowercase') == 'lowercase'
        assert self.analyzer._classify_naming_style('MixedCase123') == 'mixed'
    
    def test_analyze_with_syntax_errors(self):
        """Test analysis with malformed code."""
        diff_text = """
+def incomplete_function(
+    invalid syntax here
+    another line
"""
        
        # Should not crash on syntax errors
        patterns = self.analyzer.analyze_commit_diff(diff_text)
        assert isinstance(patterns, dict)
        assert 'naming_conventions' in patterns


class TestTeamStyleAnalyzer:
    """Test cases for team style analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.repo_path = self.temp_dir.name
        self.config = {
            'analyze_last_n_commits': 10,
            'min_pattern_frequency': 0.6,
            'exclude_merge_commits': True,
            'exclude_authors': ['bot']
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    @patch('kirolinter.core.style_analyzer.GIT_AVAILABLE', False)
    def test_analyze_without_git(self):
        """Test analysis when Git is not available."""
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        patterns = analyzer.analyze_repository()
        
        # Should return default patterns
        assert patterns['naming_conventions']['variables'] == 'snake_case'
        assert patterns['naming_conventions']['classes'] == 'PascalCase'
        assert patterns['confidence_scores']['default_patterns'] is True
    
    @patch('kirolinter.core.style_analyzer.GIT_AVAILABLE', True)
    @patch('kirolinter.core.style_analyzer.Repo')
    def test_analyze_with_mock_repo(self, mock_repo_class):
        """Test analysis with mocked Git repository."""
        # Mock repository and commits
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Create mock commits
        mock_commit1 = Mock()
        mock_commit1.parents = [Mock()]  # Not a merge commit
        mock_commit1.author.name = 'developer'
        mock_commit1.stats.files = {'file1.py': Mock(), 'file2.py': Mock()}
        mock_commit1.hexsha = 'abc123'
        
        mock_commit2 = Mock()
        mock_commit2.parents = [Mock()]
        mock_commit2.author.name = 'developer'
        mock_commit2.stats.files = {'file3.py': Mock()}
        mock_commit2.hexsha = 'def456'
        
        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]
        
        # Mock git diff output
        mock_repo.git.diff.return_value = """
+def snake_case_function():
+    variable_name = "test"
+    CONSTANT_VALUE = 42
+    return variable_name

+class PascalCaseClass:
+    def method_name(self):
+        return True
"""
        
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        patterns = analyzer.analyze_repository()
        
        # Should extract patterns from mock commits
        assert 'naming_conventions' in patterns
        assert 'code_structure' in patterns
        assert 'confidence_scores' in patterns
    
    def test_get_default_patterns(self):
        """Test default pattern generation."""
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        patterns = analyzer._get_default_patterns()
        
        assert patterns['naming_conventions']['variables'] == 'snake_case'
        assert patterns['naming_conventions']['functions'] == 'snake_case'
        assert patterns['naming_conventions']['classes'] == 'PascalCase'
        assert patterns['naming_conventions']['constants'] == 'UPPER_SNAKE_CASE'
        assert patterns['code_structure']['uses_comprehensions'] is True
        assert patterns['import_style']['prefers_from_imports'] is True
    
    def test_get_style_recommendations(self):
        """Test style recommendation generation."""
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        
        # Mock the analyze_repository method
        with patch.object(analyzer, 'analyze_repository') as mock_analyze:
            mock_analyze.return_value = {
                'naming_conventions': {
                    'variables': 'snake_case',
                    'functions': 'camelCase'  # Different from current
                },
                'code_structure': {
                    'preferred_function_length': 25,
                    'uses_comprehensions': True
                },
                'confidence_scores': {
                    'naming_functions': 0.8,
                    'naming_variables': 0.9
                }
            }
            
            current_patterns = {
                'naming_conventions': {
                    'variables': 'snake_case',
                    'functions': 'snake_case'  # Different from team preference
                }
            }
            
            recommendations = analyzer.get_style_recommendations(current_patterns)
            
            # Should recommend camelCase for functions
            assert len(recommendations) >= 1
            assert any('camelCase' in rec and 'functions' in rec for rec in recommendations)
    
    def test_accumulate_patterns(self):
        """Test pattern accumulation from multiple commits."""
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        
        # Simulate patterns from multiple commits
        patterns1 = {
            'naming_conventions': {
                'functions': {'snake_case': 3, 'camelCase': 1}
            },
            'code_structure': {
                'return_style': {'early_return': 2}
            },
            'import_style': {
                'import_types': {'from_import': 5}
            }
        }
        
        patterns2 = {
            'naming_conventions': {
                'functions': {'snake_case': 2, 'camelCase': 1}
            },
            'code_structure': {
                'return_style': {'early_return': 1, 'conditional_return': 1}
            },
            'import_style': {
                'import_types': {'from_import': 3, 'direct_import': 2}
            }
        }
        
        analyzer._accumulate_patterns(patterns1)
        analyzer._accumulate_patterns(patterns2)
        
        # Check accumulated patterns
        assert analyzer.team_patterns['naming_conventions']['functions']['snake_case'] == 5
        assert analyzer.team_patterns['naming_conventions']['functions']['camelCase'] == 2
        assert analyzer.team_patterns['code_structure']['return_style']['early_return'] == 3
        assert analyzer.team_patterns['import_style']['import_types']['from_import'] == 8
    
    def test_extract_team_preferences(self):
        """Test extraction of team preferences from accumulated patterns."""
        analyzer = TeamStyleAnalyzer(self.repo_path, self.config)
        
        # Set up accumulated patterns
        analyzer.team_patterns = {
            'naming_conventions': {
                'functions': {'snake_case': 8, 'camelCase': 2},  # 80% snake_case
                'variables': {'snake_case': 9, 'camelCase': 1}   # 90% snake_case
            },
            'code_structure': {
                'function_length': [15, 20, 18, 22, 16],
                'return_style': {'early_return': 7, 'conditional_return': 3},
                'comprehension_usage': {'list_comprehension': 12}
            },
            'import_style': {
                'import_types': {'from_import': 15, 'direct_import': 5}
            }
        }
        
        preferences = analyzer._extract_team_preferences()
        
        # Should prefer snake_case (above min_frequency of 0.6)
        assert preferences['naming_conventions']['functions'] == 'snake_case'
        assert preferences['naming_conventions']['variables'] == 'snake_case'
        
        # Should calculate average function length
        assert preferences['code_structure']['preferred_function_length'] == 18  # Average of [15,20,18,22,16]
        
        # Should prefer early returns
        assert preferences['code_structure']['preferred_return_style'] == 'early_return'
        
        # Should prefer from imports
        assert preferences['import_style']['prefers_from_imports'] is True
        
        # Should have confidence scores
        assert preferences['confidence_scores']['naming_functions'] == 0.8
        assert preferences['confidence_scores']['naming_variables'] == 0.9


# Inline AI Coding Prompts for Style Analyzer Enhancement:

"""
Recommended prompts for generating additional style analysis features using Kiro's inline AI coding:

1. "Generate code to extract naming conventions from commit diffs, detecting patterns like snake_case vs camelCase usage frequency across different code elements"

2. "Create analysis logic to detect team preferences for error handling patterns (try/except vs if/else, specific vs bare except clauses)"

3. "Generate code to analyze import organization patterns from commit history, detecting preferences for import grouping, sorting, and relative vs absolute imports"

4. "Create pattern detection for function signature styles, including parameter naming, type hints usage, and default parameter patterns"

5. "Generate analysis for code documentation patterns, detecting docstring styles, comment frequency, and inline documentation preferences"

6. "Create detection logic for team preferences in data structure usage (lists vs tuples, dicts vs classes, comprehensions vs loops)"

7. "Generate code to analyze testing patterns from commit history, detecting test naming conventions, assertion styles, and test organization"

8. "Create analysis for team preferences in class design patterns, including inheritance usage, method organization, and property vs attribute usage"

9. "Generate pattern detection for team preferences in string handling (f-strings vs format vs %, single vs double quotes)"

10. "Create analysis logic for team preferences in async/await usage patterns and concurrent programming styles"

Usage Example:
```python
# Use these prompts with Kiro's inline AI to enhance the style analyzer
# Select relevant code section and use Ctrl+K or Cmd+K to invoke AI assistance
# Paste the prompt and let Kiro generate the enhanced analysis logic
```
"""