"""
Unit tests for the code scanner module.
"""

import ast
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from kirolinter.core.scanner import CodeSmellScanner, SecurityScanner, CodeScanner
from kirolinter.models.issue import IssueType, Severity


class TestCodeSmellScanner:
    """Test cases for code smell detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {'max_complexity': 10}
        self.scanner = CodeSmellScanner(self.config)
    
    def test_unused_variable_detection(self):
        """Test detection of unused variables."""
        code = '''
def test_function():
    used_var = "I am used"
    unused_var = "I am not used"
    another_unused = 42
    print(used_var)
    return True
'''
        
        # Create temporary file
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find 2 unused variables
            unused_issues = [issue for issue in result.issues if issue.rule_id == 'unused_variable']
            assert len(unused_issues) == 2
            
            # Check issue details
            unused_names = [issue.message for issue in unused_issues]
            assert any('unused_var' in msg for msg in unused_names)
            assert any('another_unused' in msg for msg in unused_names)
            
            # Check severity
            for issue in unused_issues:
                assert issue.severity == Severity.LOW
                assert issue.type == IssueType.CODE_SMELL
    
    def test_unused_import_detection(self):
        """Test detection of unused imports."""
        code = '''
import os
import sys
import json
from pathlib import Path
from typing import List

def main():
    # Only use os and Path
    current_dir = os.getcwd()
    p = Path(current_dir)
    return str(p)
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find unused imports (sys, json, List)
            unused_imports = [issue for issue in result.issues if issue.rule_id == 'unused_import']
            assert len(unused_imports) >= 2  # At least sys and json
            
            unused_names = [issue.message for issue in unused_imports]
            assert any('sys' in msg for msg in unused_names)
            assert any('json' in msg for msg in unused_names)
    
    def test_dead_code_detection(self):
        """Test detection of unreachable code."""
        code = '''
def function_with_dead_code():
    x = 10
    if x > 5:
        return "early return"
        print("This is dead code")  # Unreachable
        y = 20  # Also unreachable
    return "normal return"
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find dead code
            dead_code_issues = [issue for issue in result.issues if issue.rule_id == 'dead_code']
            assert len(dead_code_issues) >= 1
            
            for issue in dead_code_issues:
                assert issue.severity == Severity.MEDIUM
                assert 'unreachable' in issue.message.lower()
    
    def test_complex_function_detection(self):
        """Test detection of overly complex functions."""
        # Create a function with high cyclomatic complexity
        code = '''
def complex_function(x, y, z):
    result = 0
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    if i % 2 == 0:
                        try:
                            result += i
                        except ValueError:
                            result -= 1
                        except TypeError:
                            result = 0
                    else:
                        while result < 100:
                            result += 1
                            if result > 50:
                                break
    return result
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find complex function
            complex_issues = [issue for issue in result.issues if issue.rule_id == 'complex_function']
            assert len(complex_issues) >= 1
            
            for issue in complex_issues:
                assert issue.severity in [Severity.MEDIUM, Severity.HIGH]
                assert 'complexity' in issue.message.lower()


class TestSecurityScanner:
    """Test cases for security vulnerability detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {}
        self.scanner = SecurityScanner(self.config)
    
    def test_hardcoded_secret_detection(self):
        """Test detection of hardcoded secrets."""
        code = '''
# Configuration with hardcoded secrets
API_KEY = "sk-1234567890abcdef1234567890abcdef"
password = "super_secret_password123"
database_token = "db_token_abcdef123456"
safe_placeholder = "your_api_key_here"  # Should not trigger

def connect_to_api():
    secret_key = "another_hardcoded_secret"
    return secret_key
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find hardcoded secrets
            secret_issues = [issue for issue in result.issues if 'secret' in issue.rule_id]
            assert len(secret_issues) >= 2  # At least API_KEY and password
            
            for issue in secret_issues:
                assert issue.severity == Severity.HIGH
                assert issue.type == IssueType.SECURITY
                assert 'secret' in issue.message.lower()
    
    def test_sql_injection_detection(self):
        """Test detection of SQL injection vulnerabilities."""
        code = '''
import sqlite3

def unsafe_query(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    
    return cursor.fetchall()

def safe_query(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Safe parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    
    return cursor.fetchall()
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find SQL injection vulnerability
            sql_issues = [issue for issue in result.issues if issue.rule_id == 'sql_injection']
            assert len(sql_issues) >= 1
            
            for issue in sql_issues:
                assert issue.severity == Severity.HIGH
                assert 'injection' in issue.message.lower()
    
    def test_unsafe_eval_detection(self):
        """Test detection of unsafe eval() usage."""
        code = '''
def unsafe_function(user_input):
    # Dangerous use of eval
    result = eval(user_input)
    return result

def another_unsafe_function(code_string):
    # Dangerous use of exec
    exec(code_string)
    
def safe_function(data):
    # Safe alternative
    import json
    return json.loads(data)
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find unsafe eval and exec usage
            unsafe_issues = [issue for issue in result.issues if 'unsafe_' in issue.rule_id]
            assert len(unsafe_issues) >= 2  # eval and exec
            
            for issue in unsafe_issues:
                assert issue.severity == Severity.CRITICAL
                assert issue.type == IssueType.SECURITY


class TestCodeScanner:
    """Test cases for the main code scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {'max_complexity': 10}
        self.scanner = CodeScanner(self.config)
    
    def test_comprehensive_analysis(self):
        """Test comprehensive code analysis with multiple issue types."""
        code = '''
import os
import sys  # Unused import
import json  # Unused import

API_KEY = "hardcoded_secret_key_123456"  # Security issue

def complex_function_with_issues(user_input):
    unused_variable = "not used"  # Code smell
    
    # Security vulnerability
    result = eval(user_input)
    
    # Complex logic (high cyclomatic complexity)
    if result > 0:
        if result < 100:
            for i in range(result):
                if i % 2 == 0:
                    try:
                        if i > 10:
                            return i
                            print("Dead code")  # Unreachable
                    except ValueError:
                        pass
                    except TypeError:
                        pass
    
    return os.getcwd()  # Only os is actually used
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find multiple types of issues
            assert len(result.issues) >= 4
            
            # Check for different issue types
            issue_types = {issue.type for issue in result.issues}
            assert IssueType.CODE_SMELL in issue_types
            assert IssueType.SECURITY in issue_types
            
            # Check for different severities
            severities = {issue.severity for issue in result.issues}
            assert len(severities) >= 2  # Should have multiple severity levels
            
            # Verify critical issues are detected
            assert result.has_critical_issues()
    
    def test_clean_code_analysis(self):
        """Test analysis of clean code with no issues."""
        code = '''
from pathlib import Path

def calculate_sum(numbers):
    """Calculate the sum of a list of numbers."""
    total = 0
    for number in numbers:
        total += number
    return total

def main():
    data = [1, 2, 3, 4, 5]
    result = calculate_sum(data)
    output_path = Path("result.txt")
    
    with open(output_path, "w") as f:
        f.write(str(result))
    
    return result

if __name__ == "__main__":
    main()
'''
        
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            result = self.scanner.scan_file(Path(f.name))
            
            # Should find minimal or no issues
            assert len(result.issues) == 0 or all(
                issue.severity == Severity.LOW for issue in result.issues
            )
            
            # Should not have critical issues
            assert not result.has_critical_issues()
            
            # Should have basic metrics
            assert result.metrics['lines_of_code'] > 0
            assert result.metrics['functions'] >= 2
            assert result.metrics['imports'] >= 1


# Inline AI Coding Prompts for Test Generation:

"""
Recommended prompts for generating additional test cases using Kiro's inline AI coding:

1. "Generate a test for unused variable detection with edge cases like underscore variables and loop variables"

2. "Create test cases for hardcoded secret detection that cover different patterns like API keys, passwords, and tokens in various formats"

3. "Generate test code that triggers SQL injection detection with different database libraries (sqlite3, psycopg2, mysql-connector)"

4. "Create a test for complex function detection with a function that has exactly 10 cyclomatic complexity (boundary case)"

5. "Generate test cases for dead code detection after different types of return statements (early returns, returns in loops, returns in try/except)"

6. "Create test code with performance issues like inefficient loops and redundant operations for the PerformanceScanner"

7. "Generate edge case tests for import detection including relative imports, aliased imports, and star imports"

8. "Create test cases for the scanner with malformed Python code to test error handling"
"""