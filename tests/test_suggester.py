"""
Unit tests for the suggestion engine.
"""

import pytest
from tempfile import NamedTemporaryFile
from pathlib import Path

from kirolinter.core.suggester import RuleBasedSuggester, SuggestionEngine
from kirolinter.models.issue import Issue, IssueType, Severity
from kirolinter.models.suggestion import FixType


class TestRuleBasedSuggester:
    """Test cases for rule-based suggestion generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.suggester = RuleBasedSuggester()
    
    def test_unused_variable_suggestion(self):
        """Test suggestion generation for unused variables."""
        # Create a test file with unused variable
        code = '''
def test_function():
    used_var = "I am used"
    unused_var = "I am not used"
    print(used_var)
    return True
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="unused_var_test_1",
                type=IssueType.CODE_SMELL,
                severity=Severity.LOW,
                file_path=f.name,
                line_number=3,
                column=4,
                message="Unused variable 'unused_var'",
                rule_id="unused_variable"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.DELETE
            assert suggestion.confidence >= 0.8
            assert "Remove" in suggestion.explanation
            assert suggestion.issue_id == issue.id
    
    def test_unused_import_suggestion(self):
        """Test suggestion generation for unused imports."""
        code = '''
import os
import sys
import json

def main():
    return os.getcwd()
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="unused_import_sys_2",
                type=IssueType.CODE_SMELL,
                severity=Severity.LOW,
                file_path=f.name,
                line_number=2,
                column=0,
                message="Unused import 'sys'",
                rule_id="unused_import"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.DELETE
            assert suggestion.confidence >= 0.9
            assert "import" in suggestion.explanation.lower()
            assert suggestion.suggested_code == ""  # Should be empty for deletion
    
    def test_hardcoded_secret_suggestion(self):
        """Test suggestion generation for hardcoded secrets."""
        code = '''
API_KEY = "sk-1234567890abcdef1234567890abcdef"
password = "super_secret_password123"

def connect():
    return API_KEY
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="hardcoded_secret_api_key_1",
                type=IssueType.SECURITY,
                severity=Severity.HIGH,
                file_path=f.name,
                line_number=1,
                column=0,
                message="Potential hardcoded secret in variable 'API_KEY'",
                rule_id="hardcoded_secret"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.REPLACE
            assert suggestion.confidence >= 0.8  # Updated confidence
            assert "environment" in suggestion.explanation.lower()
            assert "os.environ.get" in suggestion.suggested_code
            assert "API_KEY" in suggestion.suggested_code  # Should use proper env var name
    
    def test_hardcoded_api_key_specific_suggestion(self):
        """Test specific suggestion for API key hardcoding."""
        code = '''
api_key = "sk-1234567890abcdef1234567890abcdef"
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="hardcoded_api_key_1",
                type=IssueType.SECURITY,
                severity=Severity.HIGH,
                file_path=f.name,
                line_number=1,
                column=0,
                message="Potential hardcoded API key detected",
                rule_id="hardcoded_api_key"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.REPLACE
            assert suggestion.confidence >= 0.9
            assert "API_KEY" in suggestion.suggested_code
    
    def test_sql_injection_suggestion(self):
        """Test suggestion generation for SQL injection vulnerabilities."""
        code = '''
import sqlite3

def unsafe_query(user_id):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    return cursor.fetchall()
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="sql_injection_7",
                type=IssueType.SECURITY,
                severity=Severity.HIGH,
                file_path=f.name,
                line_number=6,
                column=12,
                message="Potential SQL injection: use parameterized queries",
                rule_id="sql_injection"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.REPLACE
            assert suggestion.confidence >= 0.7
            assert "parameterized" in suggestion.explanation.lower()
            assert "?" in suggestion.suggested_code  # Parameterized query placeholder
    
    def test_unsafe_eval_suggestion(self):
        """Test suggestion generation for unsafe eval usage."""
        code = '''
def unsafe_function(user_input):
    result = eval(user_input)
    return result
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="unsafe_eval_2",
                type=IssueType.SECURITY,
                severity=Severity.CRITICAL,
                file_path=f.name,
                line_number=2,
                column=13,
                message="Unsafe use of eval() function",
                rule_id="unsafe_eval"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.REPLACE
            assert suggestion.confidence >= 0.8
            assert "safer" in suggestion.explanation.lower()
            assert any(alt in suggestion.suggested_code for alt in ["json.loads", "ast.literal_eval"])
    
    def test_complex_function_suggestion(self):
        """Test suggestion generation for complex functions."""
        code = '''
def complex_function(x, y, z):
    # This function has high cyclomatic complexity
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
    return 0
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issue = Issue(
                id="complex_function_1",
                type=IssueType.CODE_SMELL,
                severity=Severity.MEDIUM,
                file_path=f.name,
                line_number=1,
                column=0,
                message="Function 'complex_function' has high cyclomatic complexity (15)",
                rule_id="complex_function"
            )
            
            suggestion = self.suggester.generate_suggestion(issue)
            
            assert suggestion is not None
            assert suggestion.fix_type == FixType.REFACTOR
            assert suggestion.confidence >= 0.5
            assert "smaller" in suggestion.explanation.lower()
    
    def test_no_suggestion_for_unknown_rule(self):
        """Test that no suggestion is generated for unknown rules."""
        issue = Issue(
            id="unknown_rule_1",
            type=IssueType.CODE_SMELL,
            severity=Severity.LOW,
            file_path="/tmp/test.py",
            line_number=1,
            column=0,
            message="Unknown issue",
            rule_id="unknown_rule"
        )
        
        suggestion = self.suggester.generate_suggestion(issue)
        assert suggestion is None


class TestSuggestionEngine:
    """Test cases for the main suggestion engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'use_ai_suggestions': False,  # Disable AI for testing
            'fallback_to_rules': True,
            'openai_api_key': ''
        }
        self.engine = SuggestionEngine(self.config)
    
    def test_generate_suggestions_for_multiple_issues(self):
        """Test generating suggestions for multiple issues."""
        code = '''
import os
import sys  # Unused
import json  # Unused

API_KEY = "hardcoded_secret_123"

def test():
    unused_var = "not used"
    return os.getcwd()
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issues = [
                Issue(
                    id="unused_import_sys",
                    type=IssueType.CODE_SMELL,
                    severity=Severity.LOW,
                    file_path=f.name,
                    line_number=2,
                    column=0,
                    message="Unused import 'sys'",
                    rule_id="unused_import"
                ),
                Issue(
                    id="hardcoded_secret_api",
                    type=IssueType.SECURITY,
                    severity=Severity.HIGH,
                    file_path=f.name,
                    line_number=5,
                    column=0,
                    message="Hardcoded secret detected",
                    rule_id="hardcoded_secret"
                ),
                Issue(
                    id="unused_var_test",
                    type=IssueType.CODE_SMELL,
                    severity=Severity.LOW,
                    file_path=f.name,
                    line_number=8,
                    column=4,
                    message="Unused variable 'unused_var'",
                    rule_id="unused_variable"
                )
            ]
            
            suggestions = self.engine.generate_suggestions(issues)
            
            # Should generate suggestions for all known rule types
            assert len(suggestions) == 3
            assert "unused_import_sys" in suggestions
            assert "hardcoded_secret_api" in suggestions
            assert "unused_var_test" in suggestions
            
            # Check suggestion types
            assert suggestions["unused_import_sys"].fix_type == FixType.DELETE
            assert suggestions["hardcoded_secret_api"].fix_type == FixType.REPLACE
            assert suggestions["unused_var_test"].fix_type == FixType.DELETE
    
    def test_suggestion_engine_with_ai_disabled(self):
        """Test suggestion engine with AI suggestions disabled."""
        config = {
            'use_ai_suggestions': False,
            'fallback_to_rules': True,
            'openai_api_key': 'fake_key'
        }
        engine = SuggestionEngine(config)
        
        issue = Issue(
            id="test_issue",
            type=IssueType.CODE_SMELL,
            severity=Severity.LOW,
            file_path="/tmp/test.py",
            line_number=1,
            column=0,
            message="Unused variable 'test'",
            rule_id="unused_variable"
        )
        
        suggestions = engine.generate_suggestions([issue])
        
        # Should still generate rule-based suggestion
        assert len(suggestions) == 1
        assert suggestions["test_issue"].fix_type == FixType.DELETE
    
    def test_suggestion_engine_with_fallback_disabled(self):
        """Test suggestion engine with rule-based fallback disabled."""
        config = {
            'use_ai_suggestions': True,
            'fallback_to_rules': False,
            'openai_api_key': ''  # No API key, so AI won't work
        }
        engine = SuggestionEngine(config)
        
        issue = Issue(
            id="test_issue",
            type=IssueType.CODE_SMELL,
            severity=Severity.LOW,
            file_path="/tmp/test.py",
            line_number=1,
            column=0,
            message="Unused variable 'test'",
            rule_id="unused_variable"
        )
        
        suggestions = engine.generate_suggestions([issue])
        
        # Should not generate any suggestions since AI is unavailable and fallback is disabled
        assert len(suggestions) == 0
    
    def test_team_style_prioritization(self):
        """Test that team style analyzer prioritizes suggestions correctly."""
        code = '''
import os
import sys  # Unused
API_KEY = "hardcoded_secret_123"
unused_var = "not used"
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            issues = [
                Issue(
                    id="unused_import_sys",
                    type=IssueType.CODE_SMELL,
                    severity=Severity.LOW,
                    file_path=f.name,
                    line_number=2,
                    column=0,
                    message="Unused import 'sys'",
                    rule_id="unused_import"
                ),
                Issue(
                    id="hardcoded_secret_api",
                    type=IssueType.SECURITY,
                    severity=Severity.HIGH,
                    file_path=f.name,
                    line_number=3,
                    column=0,
                    message="Hardcoded secret detected",
                    rule_id="hardcoded_secret"
                )
            ]
            
            # Generate suggestions with team style analysis
            suggestions = self.engine.generate_suggestions(issues, repo_path=f.name)
            
            # Security issues should have higher confidence after team prioritization
            security_suggestion = suggestions["hardcoded_secret_api"]
            code_smell_suggestion = suggestions["unused_import_sys"]
            
            # Security suggestion should have higher or equal confidence
            assert security_suggestion.confidence >= code_smell_suggestion.confidence


# Inline AI Coding Prompts for Suggester Templates:

"""
Recommended prompts for generating additional suggestion templates using Kiro's inline AI coding:

1. "Generate a template for removing unused variables that handles different assignment patterns (tuple unpacking, multiple assignment)"

2. "Create suggestion templates for fixing hardcoded secrets that cover different secret types (API keys, passwords, database URLs, JWT tokens)"

3. "Generate templates for SQL injection fixes that work with different database libraries (sqlite3, psycopg2, mysql-connector-python, SQLAlchemy)"

4. "Create templates for replacing unsafe eval() usage with safer alternatives based on the context (JSON parsing, mathematical expressions, configuration loading)"

5. "Generate templates for refactoring complex functions that suggest specific decomposition strategies (extract method, parameter object, strategy pattern)"

6. "Create templates for fixing performance issues like inefficient loops, suggesting specific optimizations (list comprehensions, generator expressions, caching)"

7. "Generate templates for import organization that follow PEP 8 guidelines (standard library first, third-party, local imports)"

8. "Create templates for fixing dead code that handle different scenarios (unreachable after return, unused functions, commented code)"

9. "Generate templates for security fixes that include explanations of the vulnerability and why the suggested fix is safer"

10. "Create templates for code style fixes that can be customized based on team preferences (line length, naming conventions, docstring style)"
"""