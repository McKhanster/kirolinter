"""
End-to-end integration tests for KiroLinter.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, Mock

from kirolinter.core.engine import AnalysisEngine
from kirolinter.models.config import Config
from kirolinter.cli import main


class TestEndToEndAnalysis:
    """End-to-end tests for complete analysis pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo_path = Path(self.temp_dir)
        
        # Create a sample Python project structure
        self._create_sample_project()
        
        # Create test config
        self.config = Config()
        self.config.rules = {
            'unused_variable': {'enabled': True, 'severity': 'low'},
            'sql_injection': {'enabled': True, 'severity': 'critical'},
            'unsafe_eval': {'enabled': True, 'severity': 'critical'},
            'inefficient_loop': {'enabled': True, 'severity': 'medium'}
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_sample_project(self):
        """Create a sample Python project with various issues."""
        
        # Main application file with security issues
        app_py = self.test_repo_path / "app.py"
        app_py.write_text('''
import sqlite3
import os

def get_user_data(user_id):
    """Get user data from database - has SQL injection vulnerability."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

def process_user_input(user_input):
    """Process user input - has eval vulnerability."""
    # Dangerous eval usage
    result = eval(user_input)
    return result

def calculate_totals(items):
    """Calculate totals - has performance issue."""
    total = 0
    # Inefficient loop pattern
    for i in range(len(items)):
        total += items[i]['price']
    return total

def unused_function():
    """Function with unused variables."""
    used_var = "I am used"
    unused_var = "I am not used"
    another_unused = 42
    
    print(used_var)
    return True
''')
        
        # Utility module with code smells
        utils_py = self.test_repo_path / "utils.py"
        utils_py.write_text('''
import json
import pickle

def load_config(config_data):
    """Load configuration - has pickle vulnerability."""
    # Unsafe pickle usage
    config = pickle.loads(config_data)
    return config

def complex_function(a, b, c, d, e):
    """Overly complex function for testing."""
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return a + b + c + d + e
                    else:
                        return a + b + c + d
                else:
                    return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        return 0

def process_data(data_list):
    """Process data with performance issues."""
    result = []
    # Inefficient list concatenation
    for item in data_list:
        result = result + [item * 2]
    return result

class DataProcessor:
    """Class with various issues."""
    
    def __init__(self):
        self.data = []
        self.unused_attr = "not used"
    
    def add_item(self, item):
        """Add item with redundant operations."""
        # Redundant len() calls
        if len(self.data) > 0 and len(self.data) < 100:
            self.data.append(item)
    
    def get_item_count(self):
        """Get count with dead code."""
        count = len(self.data)
        return count
        # Dead code after return
        print("This will never execute")
        unused_var = "dead code variable"
''')
        
        # Test file (should be excluded from analysis)
        test_py = self.test_repo_path / "test_app.py"
        test_py.write_text('''
import unittest
from app import get_user_data

class TestApp(unittest.TestCase):
    def test_get_user_data(self):
        result = get_user_data(1)
        self.assertIsNotNone(result)
''')
        
        # Requirements file
        requirements_txt = self.test_repo_path / "requirements.txt"
        requirements_txt.write_text('''
flask==1.0.0
requests==2.20.0
sqlite3
''')
        
        # Create subdirectory with more files
        subdir = self.test_repo_path / "modules"
        subdir.mkdir()
        
        module_py = subdir / "auth.py"
        module_py.write_text('''
import hashlib
import secrets

def hash_password(password):
    """Hash password - potential timing attack."""
    # Weak hashing (for testing)
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(stored_hash, password):
    """Verify password with timing vulnerability."""
    computed_hash = hash_password(password)
    # Timing attack vulnerability
    return stored_hash == computed_hash

def generate_token():
    """Generate secure token."""
    return secrets.token_hex(32)
''')
    
    def test_complete_analysis_pipeline(self):
        """Test the complete analysis pipeline from start to finish."""
        engine = AnalysisEngine(self.config, verbose=True)
        
        # Run analysis on the test project
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Verify analysis completed successfully
        assert results.total_files > 0
        assert results.total_issues > 0
        assert results.analysis_time > 0
        assert len(results.errors) == 0
        
        # Verify we found expected issue types
        all_issues = []
        for scan_result in results.scan_results:
            all_issues.extend(scan_result.issues)
        
        # Should find security issues
        security_issues = [i for i in all_issues if i.type.value == 'security']
        assert len(security_issues) > 0
        
        # Should find performance issues
        performance_issues = [i for i in all_issues if i.type.value == 'performance']
        assert len(performance_issues) > 0
        
        # Should find code smell issues
        code_smell_issues = [i for i in all_issues if i.type.value == 'code_smell']
        assert len(code_smell_issues) > 0
        
        # Verify specific vulnerabilities were detected
        rule_ids = [issue.rule_id for issue in all_issues]
        assert 'sql_injection' in rule_ids
        assert 'unsafe_eval' in rule_ids
        assert 'unused_variable' in rule_ids
    
    def test_json_report_generation(self):
        """Test JSON report generation."""
        engine = AnalysisEngine(self.config)
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Generate JSON report
        json_report = engine.generate_report(results, format='json')
        
        # Verify JSON is valid
        report_data = json.loads(json_report)
        
        # Verify report structure
        assert 'target' in report_data
        assert 'summary' in report_data
        assert 'files' in report_data
        assert 'analysis_metadata' in report_data
        
        # Verify summary data
        summary = report_data['summary']
        assert 'total_files' in summary
        assert 'total_issues' in summary
        assert 'issues_by_severity' in summary
        assert 'issues_by_type' in summary
        
        # Verify file data
        files = report_data['files']
        assert len(files) > 0
        
        for file_data in files:
            assert 'file_path' in file_data
            assert 'issues' in file_data
            
            for issue in file_data['issues']:
                assert 'id' in issue
                assert 'type' in issue
                assert 'severity' in issue
                assert 'message' in issue
                assert 'line_number' in issue
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        engine = AnalysisEngine(self.config)
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Generate HTML report
        html_report = engine.generate_report(results, format='html')
        
        # Verify HTML contains expected elements
        assert '<!DOCTYPE html>' in html_report
        assert 'KiroLinter Analysis Report' in html_report
        assert 'Files Analyzed' in html_report
        assert 'Issues Found' in html_report
        
        # Verify interactive elements
        assert 'toggleFile' in html_report  # JavaScript function
        assert 'severity-filter' in html_report  # Filter controls
        assert 'search-filter' in html_report
        
        # Verify CSS styling
        assert '.file-card' in html_report
        assert '.issue-item' in html_report
        assert '.severity-critical' in html_report
    
    def test_summary_report_generation(self):
        """Test summary report generation."""
        engine = AnalysisEngine(self.config)
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Generate summary report
        summary_report = engine.generate_report(results, format='summary')
        
        # Verify summary contains expected information
        assert 'KiroLinter Analysis Summary' in summary_report
        assert 'Files analyzed:' in summary_report
        assert 'Issues found:' in summary_report
        
        # Should contain severity sections if issues exist
        if results.total_issues > 0:
            severity_counts = results.get_issues_by_severity()
            if severity_counts['critical'] > 0:
                assert 'CRITICAL SEVERITY' in summary_report
            if severity_counts['high'] > 0:
                assert 'HIGH SEVERITY' in summary_report
    
    @patch('subprocess.run')
    def test_git_repository_analysis(self, mock_subprocess):
        """Test analysis of a Git repository."""
        # Mock git clone success
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        engine = AnalysisEngine(self.config)
        
        # This would normally clone a repo, but we'll mock it
        with patch.object(engine, '_prepare_codebase', return_value=str(self.test_repo_path)):
            results = engine.analyze_codebase('https://github.com/test/repo.git')
            
            assert results.target == 'https://github.com/test/repo.git'
            assert results.total_files > 0
    
    def test_changed_files_only_analysis(self):
        """Test analysis of only changed files."""
        # Create a git repository
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.test_repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], 
                      cwd=self.test_repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], 
                      cwd=self.test_repo_path, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=self.test_repo_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], 
                      cwd=self.test_repo_path, capture_output=True)
        
        # Modify a file
        app_py = self.test_repo_path / "app.py"
        app_py.write_text(app_py.read_text() + '\n# Modified file\n')
        
        subprocess.run(['git', 'add', 'app.py'], cwd=self.test_repo_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Modified app.py'], 
                      cwd=self.test_repo_path, capture_output=True)
        
        engine = AnalysisEngine(self.config)
        
        # Analyze only changed files
        results = engine.analyze_codebase(str(self.test_repo_path), changed_only=True)
        
        # Should analyze at least the changed file
        assert results.total_files >= 1
        
        # Should find issues in the changed file
        changed_file_results = [r for r in results.scan_results if 'app.py' in r.file_path]
        assert len(changed_file_results) > 0
    
    def test_performance_constraint(self):
        """Test that analysis completes within performance constraints."""
        import time
        
        engine = AnalysisEngine(self.config)
        
        start_time = time.time()
        results = engine.analyze_codebase(str(self.test_repo_path))
        end_time = time.time()
        
        analysis_time = end_time - start_time
        
        # Should complete within reasonable time for small project
        assert analysis_time < 30  # 30 seconds for small test project
        assert results.analysis_time > 0
    
    def test_error_handling(self):
        """Test error handling for various failure scenarios."""
        engine = AnalysisEngine(self.config)
        
        # Test with non-existent path
        results = engine.analyze_codebase('/non/existent/path')
        assert len(results.errors) > 0
        assert results.total_files == 0
        
        # Test with invalid Git URL
        results = engine.analyze_codebase('https://invalid-git-url.com/repo.git')
        assert len(results.errors) > 0
        assert results.total_files == 0
    
    def test_file_exclusion_patterns(self):
        """Test that files are properly excluded based on patterns."""
        # Add exclusion patterns to config
        self.config.exclude_patterns = ['test_*.py', '*/tests/*']
        
        engine = AnalysisEngine(self.config)
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Verify test files were excluded
        analyzed_files = [r.file_path for r in results.scan_results]
        test_files = [f for f in analyzed_files if 'test_' in f]
        assert len(test_files) == 0
    
    @patch('kirolinter.integrations.cve_database.CVEDatabase')
    def test_cve_integration(self, mock_cve_db):
        """Test CVE database integration in end-to-end analysis."""
        # Mock CVE database
        mock_cve_instance = Mock()
        mock_cve_instance.enhance_security_issues.return_value = []
        mock_cve_db.return_value = mock_cve_instance
        
        # Enable CVE integration in config
        config_dict = self.config.to_dict()
        config_dict['enable_cve_integration'] = True
        
        engine = AnalysisEngine(self.config)
        engine.cve_database = mock_cve_instance
        
        results = engine.analyze_codebase(str(self.test_repo_path))
        
        # Verify CVE enhancement was called
        mock_cve_instance.enhance_security_issues.assert_called_once()
        
        # Verify analysis still completed successfully
        assert results.total_files > 0


class TestCLIIntegration:
    """Test CLI integration end-to-end."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.py"
        self.test_file.write_text('''
def test_function():
    unused_var = "not used"
    eval("dangerous")
    return True
''')
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('sys.argv')
    def test_cli_analyze_command(self, mock_argv):
        """Test CLI analyze command."""
        mock_argv.__getitem__.side_effect = lambda i: [
            'kirolinter', 'analyze', str(self.test_file), '--format', 'json'
        ][i]
        mock_argv.__len__.return_value = 5
        
        # This would test the actual CLI, but requires more complex mocking
        # For now, we'll test the components individually
        pass
    
    def test_config_file_loading(self):
        """Test configuration file loading."""
        config_file = Path(self.temp_dir) / ".kirolinter.yaml"
        config_file.write_text('''
rules:
  unused_variable:
    enabled: true
    severity: medium
  sql_injection:
    enabled: true
    severity: critical

exclude_patterns:
  - "test_*.py"
  - "*/tests/*"

max_complexity: 15
''')
        
        config = Config.from_file(str(config_file))
        
        assert config.rules['unused_variable']['enabled'] is True
        assert config.rules['unused_variable']['severity'] == 'medium'
        assert config.exclude_patterns == ["test_*.py", "*/tests/*"]
        assert config.max_complexity == 15


# Performance test fixtures
@pytest.fixture
def large_test_project():
    """Create a larger test project for performance testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create multiple files with various issues
    for i in range(10):
        file_path = Path(temp_dir) / f"module_{i}.py"
        file_path.write_text(f'''
def function_{i}():
    unused_var_{i} = "not used"
    result = eval("test_{i}")
    return result

class Class_{i}:
    def method_{i}(self):
        data = []
        for j in range(100):
            data = data + [j]  # Inefficient
        return data
''')
    
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_large_project_performance(large_test_project):
    """Test performance on larger projects."""
    config = Config()
    engine = AnalysisEngine(config)
    
    import time
    start_time = time.time()
    results = engine.analyze_codebase(large_test_project)
    end_time = time.time()
    
    # Should complete within reasonable time
    assert (end_time - start_time) < 60  # 1 minute for 10 files
    assert results.total_files == 10
    assert results.total_issues > 0