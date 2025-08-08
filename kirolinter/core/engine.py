"""
Analysis engine that orchestrates the code analysis pipeline.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import subprocess
import time

from kirolinter.core.scanner import CodeScanner, ScanResult
from kirolinter.models.config import Config
from kirolinter.utils.performance_tracker import PerformanceTracker
from kirolinter.integrations.repository_handler import RepositoryHandler


@dataclass
class AnalysisResults:
    """Results of analyzing a codebase."""
    target: str
    scan_results: List[ScanResult]
    total_files: int
    total_issues: int
    analysis_time: float
    errors: List[str]
    
    def has_critical_issues(self) -> bool:
        """Check if any scan result has critical issues."""
        return any(result.has_critical_issues() for result in self.scan_results)
    
    def get_issues_by_severity(self) -> Dict[str, int]:
        """Get count of issues by severity level."""
        severity_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for result in self.scan_results:
            for issue in result.issues:
                severity_counts[issue.severity.value] += 1
        return severity_counts


class AnalysisEngine:
    """Main analysis engine that orchestrates the code analysis pipeline."""
    
    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.scanner = CodeScanner(config.to_dict())
        self.repo_handler = RepositoryHandler()
        self.performance_tracker = PerformanceTracker()
    
    def analyze_codebase(self, target: str, changed_only: bool = False, 
                        progress_callback: Optional[Callable[[int], None]] = None) -> AnalysisResults:
        """
        Analyze a codebase (Git repository or local directory).
        
        Args:
            target: Git repository URL or local directory path
            changed_only: Only analyze files changed in the last commit
            progress_callback: Optional callback for progress updates (0-100)
        
        Returns:
            AnalysisResults containing all scan results and metadata
        """
        self.performance_tracker.start()
        
        try:
            # Prepare the codebase for analysis
            analysis_path = self._prepare_codebase(target)
            
            # Get list of Python files to analyze
            python_files = self._get_python_files(analysis_path, changed_only)
            
            if not python_files:
                return AnalysisResults(
                    target=target,
                    scan_results=[],
                    total_files=0,
                    total_issues=0,
                    analysis_time=self.performance_tracker.stop(),
                    errors=["No Python files found to analyze"]
                )
            
            # Analyze files with progress tracking
            scan_results = []
            errors = []
            
            for i, file_path in enumerate(python_files):
                try:
                    if self.verbose:
                        print(f"Analyzing {file_path}...")
                    
                    result = self.process_file(file_path)
                    scan_results.append(result)
                    
                    # Update progress
                    if progress_callback:
                        progress = int((i + 1) / len(python_files) * 100)
                        progress_callback(progress)
                        
                except Exception as e:
                    error_msg = f"Error analyzing {file_path}: {str(e)}"
                    errors.append(error_msg)
                    if self.verbose:
                        print(f"⚠️  {error_msg}")
            
            # Calculate totals
            total_issues = sum(len(result.issues) for result in scan_results)
            analysis_time = self.performance_tracker.stop()
            
            # Clean up temporary directory if we cloned a repo
            if target.startswith(('http://', 'https://', 'git@')) and analysis_path != target:
                shutil.rmtree(analysis_path, ignore_errors=True)
            
            return AnalysisResults(
                target=target,
                scan_results=scan_results,
                total_files=len(python_files),
                total_issues=total_issues,
                analysis_time=analysis_time,
                errors=errors
            )
            
        except Exception as e:
            return AnalysisResults(
                target=target,
                scan_results=[],
                total_files=0,
                total_issues=0,
                analysis_time=self.performance_tracker.stop(),
                errors=[f"Analysis failed: {str(e)}"]
            )
    
    def process_file(self, file_path: Path) -> ScanResult:
        """
        Process a single Python file.
        
        Args:
            file_path: Path to the Python file to analyze
        
        Returns:
            ScanResult containing issues found in the file
        """
        return self.scanner.scan_file(file_path)
    
    def generate_report(self, results: AnalysisResults, format: str = 'json') -> str:
        """
        Generate a report from analysis results.
        
        Args:
            results: Analysis results to format
            format: Output format ('json', 'summary', 'detailed')
        
        Returns:
            Formatted report as string
        """
        if format == 'json':
            return self._generate_json_report(results)
        elif format == 'summary':
            return self._generate_summary_report(results)
        elif format == 'detailed':
            return self._generate_detailed_report(results)
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def _prepare_codebase(self, target: str) -> str:
        """
        Prepare the codebase for analysis (clone if URL, validate if local path).
        
        Args:
            target: Git repository URL or local directory path
        
        Returns:
            Path to the prepared codebase directory
        """
        if target.startswith(('http://', 'https://', 'git@')):
            # Clone Git repository to temporary directory
            temp_dir = tempfile.mkdtemp(prefix='kirolinter_')
            try:
                if self.verbose:
                    print(f"Cloning repository {target}...")
                
                result = subprocess.run([
                    'git', 'clone', '--depth', '1', target, temp_dir
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to clone repository: {result.stderr}")
                
                return temp_dir
                
            except subprocess.TimeoutExpired:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError("Repository clone timed out after 5 minutes")
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(f"Failed to clone repository: {str(e)}")
        
        else:
            # Local directory
            if target == '.':
                target = os.getcwd()
            
            path = Path(target)
            if not path.exists():
                raise ValueError(f"Path does not exist: {target}")
            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {target}")
            
            return str(path.resolve())
    
    def _get_python_files(self, directory: str, changed_only: bool = False) -> List[Path]:
        """
        Get list of Python files to analyze.
        
        Args:
            directory: Directory to scan for Python files
            changed_only: Only include files changed in the last commit
        
        Returns:
            List of Python file paths
        """
        if changed_only:
            return self._get_changed_python_files(directory)
        
        python_files = []
        dir_path = Path(directory)
        
        # Recursively find Python files
        for file_path in dir_path.rglob('*.py'):
            # Skip files matching exclude patterns
            if self._should_exclude_file(file_path):
                continue
            
            python_files.append(file_path)
        
        return python_files
    
    def _get_changed_python_files(self, directory: str) -> List[Path]:
        """Get Python files changed in the last commit."""
        try:
            # Get files changed in the last commit
            result = subprocess.run([
                'git', 'diff', '--name-only', 'HEAD~1', 'HEAD'
            ], cwd=directory, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Fallback to all files if git command fails
                return self._get_python_files(directory, changed_only=False)
            
            changed_files = []
            for file_name in result.stdout.strip().split('\n'):
                if file_name.endswith('.py'):
                    file_path = Path(directory) / file_name
                    if file_path.exists() and not self._should_exclude_file(file_path):
                        changed_files.append(file_path)
            
            return changed_files
            
        except Exception:
            # Fallback to all files if git operations fail
            return self._get_python_files(directory, changed_only=False)
    
    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from analysis."""
        file_str = str(file_path)
        
        # Check exclude patterns from config
        for pattern in self.config.exclude_patterns:
            if pattern in file_str:
                return True
        
        # Default exclusions
        default_exclusions = [
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            'env',
            '.tox',
            'build',
            'dist',
            '.pytest_cache'
        ]
        
        for exclusion in default_exclusions:
            if exclusion in file_str:
                return True
        
        return False
    
    def _generate_json_report(self, results: AnalysisResults) -> str:
        """Generate JSON format report."""
        import json
        
        report_data = {
            'target': results.target,
            'summary': {
                'total_files': results.total_files,
                'total_issues': results.total_issues,
                'analysis_time': results.analysis_time,
                'issues_by_severity': results.get_issues_by_severity()
            },
            'files': []
        }
        
        for scan_result in results.scan_results:
            file_data = {
                'file_path': scan_result.file_path,
                'issues': [issue.to_dict() for issue in scan_result.issues],
                'metrics': scan_result.metrics,
                'parse_errors': scan_result.parse_errors
            }
            report_data['files'].append(file_data)
        
        if results.errors:
            report_data['errors'] = results.errors
        
        return json.dumps(report_data, indent=2)
    
    def _generate_summary_report(self, results: AnalysisResults) -> str:
        """Generate summary format report."""
        lines = []
        lines.append("📊 KiroLinter Analysis Summary")
        lines.append(f"Files analyzed: {results.total_files}")
        lines.append(f"Issues found: {results.total_issues}")
        lines.append("")
        
        severity_counts = results.get_issues_by_severity()
        
        if severity_counts['critical'] > 0:
            lines.append(f"🔴 CRITICAL SEVERITY ({severity_counts['critical']}):")
            self._add_issues_by_severity(lines, results, 'critical')
        
        if severity_counts['high'] > 0:
            lines.append(f"🟠 HIGH SEVERITY ({severity_counts['high']}):")
            self._add_issues_by_severity(lines, results, 'high')
        
        if severity_counts['medium'] > 0:
            lines.append(f"🟡 MEDIUM SEVERITY ({severity_counts['medium']}):")
            self._add_issues_by_severity(lines, results, 'medium')
        
        if severity_counts['low'] > 0:
            lines.append(f"🟢 LOW SEVERITY ({severity_counts['low']}):")
            self._add_issues_by_severity(lines, results, 'low')
        
        if results.errors:
            lines.append("")
            lines.append("❌ ERRORS:")
            for error in results.errors:
                lines.append(f"  {error}")
        
        return '\n'.join(lines)
    
    def _generate_detailed_report(self, results: AnalysisResults) -> str:
        """Generate detailed format report."""
        lines = []
        lines.append("📋 KiroLinter Detailed Analysis Report")
        lines.append("=" * 50)
        lines.append(f"Target: {results.target}")
        lines.append(f"Files analyzed: {results.total_files}")
        lines.append(f"Total issues: {results.total_issues}")
        lines.append(f"Analysis time: {results.analysis_time:.2f}s")
        lines.append("")
        
        for scan_result in results.scan_results:
            if scan_result.issues or scan_result.parse_errors:
                lines.append(f"📄 {scan_result.file_path}")
                lines.append("-" * len(scan_result.file_path))
                
                if scan_result.parse_errors:
                    lines.append("Parse Errors:")
                    for error in scan_result.parse_errors:
                        lines.append(f"  ❌ {error}")
                    lines.append("")
                
                if scan_result.issues:
                    for issue in scan_result.issues:
                        severity_icon = {
                            'low': '🟢',
                            'medium': '🟡', 
                            'high': '🟠',
                            'critical': '🔴'
                        }.get(issue.severity.value, '⚪')
                        
                        lines.append(f"  {severity_icon} Line {issue.line_number}: {issue.message}")
                        lines.append(f"    Rule: {issue.rule_id}")
                        if issue.cve_id:
                            lines.append(f"    CVE: {issue.cve_id}")
                
                lines.append("")
        
        return '\n'.join(lines)
    
    def _add_issues_by_severity(self, lines: List[str], results: AnalysisResults, severity: str):
        """Add issues of a specific severity to the report lines."""
        count = 0
        for scan_result in results.scan_results:
            for issue in scan_result.issues:
                if issue.severity.value == severity:
                    lines.append(f"  {scan_result.file_path}:{issue.line_number} - {issue.message}")
                    count += 1
                    if count >= 10:  # Limit to first 10 issues per severity
                        lines.append(f"  ... and {sum(1 for sr in results.scan_results for i in sr.issues if i.severity.value == severity) - 10} more")
                        return
        lines.append("")