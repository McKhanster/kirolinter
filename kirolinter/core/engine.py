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
from kirolinter.core.suggester import SuggestionEngine
from kirolinter.models.config import Config
from kirolinter.utils.performance_tracker import PerformanceTracker
from kirolinter.integrations.repository_handler import RepositoryHandler
from kirolinter.integrations.github_client import GitHubClient
from kirolinter.integrations.cve_database import CVEDatabase
from kirolinter.reporting.json_reporter import JSONReporter
from kirolinter.reporting.web_reporter import WebReporter


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
        self.suggester = SuggestionEngine(config.to_dict())
        self.repo_handler = RepositoryHandler()
        self.performance_tracker = PerformanceTracker()
        
        # Initialize CVE database if enabled
        self.cve_database = None
        if config.to_dict().get('enable_cve_integration', False):
            self.cve_database = CVEDatabase(
                api_key=config.to_dict().get('nvd_api_key', None)
            )
    
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
            all_issues = []
            
            for i, file_path in enumerate(python_files):
                try:
                    if self.verbose:
                        print(f"Analyzing {file_path}...")
                    
                    result = self.process_file(file_path)
                    scan_results.append(result)
                    all_issues.extend(result.issues)
                    
                    # Update progress
                    if progress_callback:
                        progress = int((i + 1) / len(python_files) * 100)
                        progress_callback(progress)
                        
                except Exception as e:
                    error_msg = f"Error analyzing {file_path}: {str(e)}"
                    errors.append(error_msg)
                    if self.verbose:
                        print(f"⚠️  {error_msg}")
            
            # Enhance security issues with CVE database
            if self.cve_database and all_issues:
                if self.verbose:
                    print("Enhancing security issues with CVE database...")
                
                enhanced_issues = self.cve_database.enhance_security_issues(all_issues)
                
                # Update scan results with enhanced issues
                issue_map = {issue.id: issue for issue in enhanced_issues}
                for scan_result in scan_results:
                    for i, issue in enumerate(scan_result.issues):
                        if issue.id in issue_map:
                            scan_result.issues[i] = issue_map[issue.id]
                
                all_issues = enhanced_issues
            
            # Generate suggestions for all issues
            if all_issues and self.verbose:
                print("Generating suggestions...")
            
            suggestions = self.suggester.generate_suggestions(all_issues, analysis_path)
            
            # Add suggestions to scan results
            for scan_result in scan_results:
                for issue in scan_result.issues:
                    if issue.id in suggestions:
                        # Store suggestion in issue for later use
                        issue.suggestion = suggestions[issue.id]
            
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
        elif format == 'html':
            return self._generate_html_report(results)
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
            # Local directory or file
            if target == '.':
                target = os.getcwd()
            
            path = Path(target)
            if not path.exists():
                raise ValueError(f"Path does not exist: {target}")
            
            # Handle both directories and individual Python files
            if path.is_dir():
                return str(path.resolve())
            elif path.is_file() and path.suffix == '.py':
                return str(path.resolve())
            else:
                raise ValueError(f"Target must be a directory or Python file: {target}")
            
            return str(path.resolve())
    
    def _get_python_files(self, target_path: str, changed_only: bool = False) -> List[Path]:
        """
        Get list of Python files to analyze.
        
        Args:
            target_path: Directory or file path to analyze
            changed_only: Only include files changed in the last commit
        
        Returns:
            List of Python file paths
        """
        path = Path(target_path)
        
        # Handle individual file
        if path.is_file() and path.suffix == '.py':
            if not self._should_exclude_file(path):
                return [path]
            else:
                return []
        
        # Handle directory
        if changed_only:
            return self._get_changed_python_files(target_path)
        
        python_files = []
        
        # Recursively find Python files
        for file_path in path.rglob('*.py'):
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
        """Generate JSON format report using JSONReporter."""
        json_reporter = JSONReporter(include_diffs=True)
        return json_reporter.generate_report(
            target=results.target,
            scan_results=results.scan_results,
            total_files=results.total_files,
            analysis_time=results.analysis_time,
            errors=results.errors
        )
    
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
    
    def _generate_html_report(self, results: AnalysisResults) -> str:
        """Generate HTML format report using WebReporter."""
        web_reporter = WebReporter(include_source_code=True, theme='light')
        return web_reporter.generate_report(
            target=results.target,
            scan_results=results.scan_results,
            total_files=results.total_files,
            analysis_time=results.analysis_time,
            errors=results.errors
        )
    
    def post_to_github_pr(self, pr_number: int, results: AnalysisResults,
                         github_token: str, github_repo: str) -> bool:
        """
        Post analysis results to a GitHub pull request.
        
        Args:
            pr_number: Pull request number
            results: Analysis results to post
            github_token: GitHub API token
            github_repo: Repository in format 'owner/repo'
        
        Returns:
            True if successful, False otherwise
        """
        if not github_token or not github_repo:
            print("GitHub token and repository are required for PR integration")
            return False
        
        try:
            client = GitHubClient(github_token, github_repo)
            
            # Generate summary for PR
            summary = {
                'total_files_analyzed': results.total_files,
                'total_issues_found': results.total_issues,
                'analysis_time_seconds': results.analysis_time,
                'issues_by_severity': results.get_issues_by_severity()
            }
            
            # Post summary comment
            summary_success = client.post_summary_comment(pr_number, summary)
            
            # Post line-specific comments
            comments_success = client.post_line_comments(pr_number, results.scan_results)
            
            return summary_success and comments_success
            
        except Exception as e:
            print(f"Error posting to GitHub PR: {e}")
            return False