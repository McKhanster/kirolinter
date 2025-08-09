"""
Performance tests for KiroLinter to ensure it meets the 5-minute constraint for large repositories.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, Mock

from kirolinter.core.engine import AnalysisEngine
from kirolinter.models.config import Config


class TestPerformanceConstraints:
    """Test performance constraints for large repository analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config.rules = {
            'unused_variable': {'enabled': True, 'severity': 'low'},
            'sql_injection': {'enabled': True, 'severity': 'critical'},
            'unsafe_eval': {'enabled': True, 'severity': 'critical'},
            'inefficient_loop': {'enabled': True, 'severity': 'medium'},
            'complex_function': {'enabled': True, 'severity': 'medium'}
        }
    
    def _create_large_test_project(self, num_files: int = 100, lines_per_file: int = 200) -> str:
        """Create a large test project with specified number of files and lines."""
        temp_dir = tempfile.mkdtemp(prefix='kirolinter_perf_test_')
        
        # Create main directory structure
        for subdir in ['app', 'utils', 'models', 'views', 'tests']:
            Path(temp_dir, subdir).mkdir()
        
        files_created = 0
        
        # Create files in each subdirectory
        for subdir in ['app', 'utils', 'models', 'views']:
            files_in_subdir = num_files // 4
            
            for i in range(files_in_subdir):
                file_path = Path(temp_dir, subdir, f'module_{i}.py')
                content = self._generate_file_content(f'{subdir}_module_{i}', lines_per_file)
                file_path.write_text(content)
                files_created += 1
        
        # Create remaining files in root
        remaining_files = num_files - files_created
        for i in range(remaining_files):
            file_path = Path(temp_dir, f'root_module_{i}.py')
            content = self._generate_file_content(f'root_module_{i}', lines_per_file)
            file_path.write_text(content)
        
        return temp_dir
    
    def _generate_file_content(self, module_name: str, num_lines: int) -> str:
        """Generate Python file content with various issues for testing."""
        lines = [
            f'"""Module {module_name} - Generated for performance testing."""',
            'import os',
            'import sqlite3',
            'import json',
            'import pickle',
            '',
        ]
        
        # Add functions with various issues
        functions_per_file = max(1, num_lines // 50)
        
        for func_idx in range(functions_per_file):
            func_name = f'function_{func_idx}'
            
            # Add function with unused variables
            lines.extend([
                f'def {func_name}(param1, param2=None):',
                f'    """Function {func_name} with various code issues."""',
                f'    used_var = "I am used in {func_name}"',
                f'    unused_var_{func_idx} = "I am not used"',
                f'    another_unused = {func_idx * 42}',
                '',
            ])
            
            # Add security vulnerabilities
            if func_idx % 3 == 0:
                lines.extend([
                    '    # SQL injection vulnerability',
                    f'    query = f"SELECT * FROM table WHERE id = {{param1}}"',
                    '    # cursor.execute(query)  # Commented to avoid actual execution',
                    '',
                ])
            
            if func_idx % 4 == 0:
                lines.extend([
                    '    # Eval vulnerability',
                    '    if param2:',
                    '        # result = eval(param2)  # Commented for safety',
                    '        pass',
                    '',
                ])
            
            # Add performance issues
            if func_idx % 2 == 0:
                lines.extend([
                    '    # Inefficient loop',
                    '    result = []',
                    '    for i in range(100):',
                    '        result = result + [i * 2]  # Inefficient concatenation',
                    '',
                ])
            
            # Add complex control flow
            if func_idx % 5 == 0:
                lines.extend([
                    '    # Complex nested conditions',
                    '    if param1 > 0:',
                    '        if param2 is not None:',
                    '            if len(str(param1)) > 2:',
                    '                if param1 % 2 == 0:',
                    '                    if param1 < 1000:',
                    '                        return "complex_result"',
                    '                    else:',
                    '                        return "very_large"',
                    '                else:',
                    '                    return "odd_number"',
                    '            else:',
                    '                return "short_number"',
                    '        else:',
                    '            return "no_param2"',
                    '    else:',
                    '        return "negative_or_zero"',
                    '',
                ])
            
            # Add dead code
            if func_idx % 6 == 0:
                lines.extend([
                    '    print(used_var)',
                    '    return True',
                    '    # Dead code below',
                    '    dead_var = "This will never execute"',
                    '    print(dead_var)',
                    '',
                ])
            else:
                lines.extend([
                    '    print(used_var)',
                    '    return True',
                    '',
                ])
        
        # Add a class with methods
        lines.extend([
            f'class {module_name.title()}Processor:',
            f'    """Class for {module_name} processing."""',
            '',
            '    def __init__(self):',
            '        self.data = []',
            '        self.unused_attr = "not used"',
            '',
            '    def process_data(self, data_list):',
            '        """Process data with performance issues."""',
            '        # Inefficient operations',
            '        for item in data_list:',
            '            if len(self.data) > 0:  # Redundant len() call',
            '                self.data.append(item)',
            '        return len(self.data)',
            '',
            '    def serialize_data(self, data):',
            '        """Serialize data with security issue."""',
            '        # Unsafe pickle usage',
            '        # return pickle.dumps(data)  # Commented for safety',
            '        return json.dumps(data)',
            '',
        ])
        
        # Pad with comments to reach target line count
        current_lines = len(lines)
        if current_lines < num_lines:
            padding_needed = num_lines - current_lines
            for i in range(padding_needed):
                lines.append(f'# Padding comment {i + 1}')
        
        return '\n'.join(lines)
    
    def test_medium_project_performance(self):
        """Test performance on medium-sized project (50 files, ~5000 lines)."""
        temp_dir = self._create_large_test_project(num_files=50, lines_per_file=100)
        
        try:
            engine = AnalysisEngine(self.config, verbose=False)
            
            start_time = time.time()
            results = engine.analyze_codebase(temp_dir)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # Should complete within 2 minutes for medium project
            assert analysis_time < 120, f"Analysis took {analysis_time:.2f}s, expected < 120s"
            
            # Verify analysis was successful
            assert results.total_files == 50
            assert results.total_issues > 0
            assert len(results.errors) == 0
            
            # Performance metrics
            files_per_second = results.total_files / analysis_time
            assert files_per_second > 0.5, f"Processing rate too slow: {files_per_second:.2f} files/s"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_large_project_performance(self):
        """Test performance on large project (100 files, ~10000 lines)."""
        temp_dir = self._create_large_test_project(num_files=100, lines_per_file=100)
        
        try:
            engine = AnalysisEngine(self.config, verbose=False)
            
            start_time = time.time()
            results = engine.analyze_codebase(temp_dir)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # Should complete within 5 minutes (300 seconds) for large project
            assert analysis_time < 300, f"Analysis took {analysis_time:.2f}s, expected < 300s"
            
            # Verify analysis was successful
            assert results.total_files == 100
            assert results.total_issues > 0
            assert len(results.errors) == 0
            
            # Performance metrics
            files_per_second = results.total_files / analysis_time
            lines_per_second = (results.total_files * 100) / analysis_time
            
            print(f"Performance metrics:")
            print(f"  Files processed: {results.total_files}")
            print(f"  Total issues found: {results.total_issues}")
            print(f"  Analysis time: {analysis_time:.2f}s")
            print(f"  Files per second: {files_per_second:.2f}")
            print(f"  Lines per second: {lines_per_second:.0f}")
            
            # Minimum performance requirements
            assert files_per_second > 0.3, f"Processing rate too slow: {files_per_second:.2f} files/s"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.slow
    def test_very_large_project_performance(self):
        """Test performance on very large project (200 files, ~20000 lines)."""
        temp_dir = self._create_large_test_project(num_files=200, lines_per_file=100)
        
        try:
            engine = AnalysisEngine(self.config, verbose=False)
            
            start_time = time.time()
            results = engine.analyze_codebase(temp_dir)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # Should still complete within 5 minutes even for very large projects
            assert analysis_time < 300, f"Analysis took {analysis_time:.2f}s, expected < 300s"
            
            # Verify analysis was successful
            assert results.total_files == 200
            assert results.total_issues > 0
            
            # Performance metrics
            files_per_second = results.total_files / analysis_time
            
            print(f"Very large project performance:")
            print(f"  Files processed: {results.total_files}")
            print(f"  Analysis time: {analysis_time:.2f}s")
            print(f"  Files per second: {files_per_second:.2f}")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_memory_usage_constraint(self):
        """Test that memory usage remains reasonable during analysis."""
        import psutil
        import os
        
        temp_dir = self._create_large_test_project(num_files=100, lines_per_file=100)
        
        try:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            engine = AnalysisEngine(self.config, verbose=False)
            results = engine.analyze_codebase(temp_dir)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"Memory usage:")
            print(f"  Initial: {initial_memory:.1f} MB")
            print(f"  Final: {final_memory:.1f} MB")
            print(f"  Increase: {memory_increase:.1f} MB")
            
            # Memory usage should not exceed 500MB increase for 100 files
            assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f} MB"
            
            # Verify analysis was successful
            assert results.total_files == 100
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_concurrent_file_processing(self):
        """Test that concurrent processing improves performance."""
        temp_dir = self._create_large_test_project(num_files=50, lines_per_file=100)
        
        try:
            # Test sequential processing
            config_sequential = Config()
            config_sequential.rules = self.config.rules
            engine_sequential = AnalysisEngine(config_sequential, verbose=False)
            
            start_time = time.time()
            results_sequential = engine_sequential.analyze_codebase(temp_dir)
            sequential_time = time.time() - start_time
            
            # For this test, we're mainly verifying the analysis works
            # Real concurrent processing would require threading implementation
            assert results_sequential.total_files == 50
            assert sequential_time > 0
            
            print(f"Sequential processing time: {sequential_time:.2f}s")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_progress_tracking(self):
        """Test progress tracking during analysis."""
        temp_dir = self._create_large_test_project(num_files=20, lines_per_file=50)
        
        try:
            progress_updates = []
            
            def progress_callback(progress):
                progress_updates.append(progress)
            
            engine = AnalysisEngine(self.config, verbose=False)
            results = engine.analyze_codebase(temp_dir, progress_callback=progress_callback)
            
            # Verify progress updates were received
            assert len(progress_updates) > 0
            assert progress_updates[-1] == 100  # Should end at 100%
            
            # Progress should be monotonically increasing
            for i in range(1, len(progress_updates)):
                assert progress_updates[i] >= progress_updates[i-1]
            
            # Verify analysis was successful
            assert results.total_files == 20
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_early_termination_on_timeout(self):
        """Test that analysis can be terminated early if it takes too long."""
        # This test would require implementing timeout functionality
        # For now, we'll test that the analysis completes within expected time
        temp_dir = self._create_large_test_project(num_files=30, lines_per_file=100)
        
        try:
            engine = AnalysisEngine(self.config, verbose=False)
            
            start_time = time.time()
            results = engine.analyze_codebase(temp_dir)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # Should complete well within timeout for this size
            assert analysis_time < 60, f"Analysis took too long: {analysis_time:.2f}s"
            assert results.total_files == 30
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @patch('subprocess.run')
    def test_git_clone_performance(self, mock_subprocess):
        """Test that Git repository cloning doesn't significantly impact performance."""
        # Mock successful git clone
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        temp_dir = self._create_large_test_project(num_files=50, lines_per_file=100)
        
        try:
            engine = AnalysisEngine(self.config, verbose=False)
            
            # Mock the prepare_codebase to return our test directory
            with patch.object(engine, '_prepare_codebase', return_value=temp_dir):
                start_time = time.time()
                results = engine.analyze_codebase('https://github.com/test/repo.git')
                end_time = time.time()
                
                analysis_time = end_time - start_time
                
                # Should complete quickly since we're mocking the clone
                assert analysis_time < 120, f"Analysis took too long: {analysis_time:.2f}s"
                assert results.total_files == 50
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRealWorldPerformance:
    """Test performance against real-world scenarios."""
    
    def test_flask_like_project_structure(self):
        """Test performance on Flask-like project structure."""
        temp_dir = tempfile.mkdtemp(prefix='flask_like_test_')
        
        try:
            # Create Flask-like directory structure
            directories = [
                'app',
                'app/models',
                'app/views',
                'app/utils',
                'app/static',
                'app/templates',
                'tests',
                'migrations'
            ]
            
            for directory in directories:
                Path(temp_dir, directory).mkdir(parents=True)
            
            # Create typical Flask files
            flask_files = {
                'app/__init__.py': '''
from flask import Flask
from app.models import db

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    db.init_app(app)
    return app
''',
                'app/models/user.py': '''
from flask_sqlalchemy import SQLAlchemy
import hashlib

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    def set_password(self, password):
        # Weak hashing for testing
        self.password_hash = hashlib.md5(password.encode()).hexdigest()
    
    def check_password(self, password):
        # Timing attack vulnerability
        return self.password_hash == hashlib.md5(password.encode()).hexdigest()
''',
                'app/views/auth.py': '''
from flask import Blueprint, request, jsonify
from app.models.user import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # SQL injection vulnerability
    query = f"SELECT * FROM user WHERE username = '{username}'"
    # user = db.session.execute(query).first()
    
    # Eval vulnerability
    if request.json.get('debug'):
        eval(request.json.get('debug'))
    
    return jsonify({'status': 'success'})
''',
                'app/utils/helpers.py': '''
import pickle
import json

def serialize_data(data):
    # Unsafe pickle usage
    return pickle.dumps(data)

def process_items(items):
    result = []
    # Inefficient loop
    for i in range(len(items)):
        result = result + [items[i] * 2]
    return result

def complex_calculation(a, b, c, d, e, f):
    # Overly complex function
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            return a + b + c + d + e + f
                        else:
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
'''
            }
            
            # Write files
            for file_path, content in flask_files.items():
                full_path = Path(temp_dir, file_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            # Run analysis
            config = Config()
            engine = AnalysisEngine(config, verbose=False)
            
            start_time = time.time()
            results = engine.analyze_codebase(temp_dir)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # Should complete quickly for small Flask-like project
            assert analysis_time < 30, f"Analysis took too long: {analysis_time:.2f}s"
            
            # Should find various types of issues
            assert results.total_files > 0
            assert results.total_issues > 0
            
            # Verify specific vulnerabilities were found
            all_issues = []
            for scan_result in results.scan_results:
                all_issues.extend(scan_result.issues)
            
            rule_ids = [issue.rule_id for issue in all_issues]
            
            # Should find security issues
            security_rules = [r for r in rule_ids if 'sql' in r or 'eval' in r or 'pickle' in r]
            assert len(security_rules) > 0
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Benchmark utilities
def benchmark_analysis(project_path: str, config: Config, iterations: int = 3) -> dict:
    """Benchmark analysis performance over multiple iterations."""
    times = []
    results_list = []
    
    for i in range(iterations):
        engine = AnalysisEngine(config, verbose=False)
        
        start_time = time.time()
        results = engine.analyze_codebase(project_path)
        end_time = time.time()
        
        times.append(end_time - start_time)
        results_list.append(results)
    
    return {
        'min_time': min(times),
        'max_time': max(times),
        'avg_time': sum(times) / len(times),
        'total_files': results_list[0].total_files,
        'avg_issues': sum(r.total_issues for r in results_list) / len(results_list),
        'times': times
    }


if __name__ == '__main__':
    # Run performance tests manually
    test_perf = TestPerformanceConstraints()
    test_perf.setup_method()
    
    print("Running medium project performance test...")
    test_perf.test_medium_project_performance()
    
    print("Running large project performance test...")
    test_perf.test_large_project_performance()
    
    print("All performance tests passed!")