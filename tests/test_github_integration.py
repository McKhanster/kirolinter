"""
Integration tests for GitHub functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from kirolinter.integrations.github_client import GitHubClient
from kirolinter.core.scanner import ScanResult
from kirolinter.models.issue import Issue, IssueType, Severity


class TestGitHubIntegration:
    """Test cases for GitHub integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.github_token = "test_token"
        self.github_repo = "test_owner/test_repo"
        self.client = GitHubClient(self.github_token, self.github_repo)
    
    @patch('requests.post')
    def test_post_summary_comment_success(self, mock_post):
        """Test successful summary comment posting."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 12345}
        mock_post.return_value = mock_response
        
        summary = {
            'total_files_analyzed': 5,
            'total_issues_found': 10,
            'analysis_time_seconds': 2.5,
            'issues_by_severity': {
                'critical': 1,
                'high': 2,
                'medium': 4,
                'low': 3
            }
        }
        
        result = self.client.post_summary_comment(123, summary)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify request details
        call_args = mock_post.call_args
        assert 'https://api.github.com/repos/test_owner/test_repo/issues/123/comments' in call_args[0][0]
        assert 'Authorization' in call_args[1]['headers']
        assert call_args[1]['headers']['Authorization'] == 'token test_token'
    
    @patch('requests.post')
    def test_post_summary_comment_failure(self, mock_post):
        """Test summary comment posting failure."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response
        
        summary = {'total_files_analyzed': 0, 'total_issues_found': 0}
        result = self.client.post_summary_comment(123, summary)
        
        assert result is False
    
    @patch('requests.get')
    @patch('requests.post')
    def test_post_line_comments_success(self, mock_post, mock_get):
        """Test successful line-specific comment posting."""
        # Mock PR files API response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {
                'filename': 'test.py',
                'patch': '@@ -1,3 +1,4 @@\n def test():\n+    eval("test")\n     pass'
            }
        ]
        mock_get.return_value = mock_get_response
        
        # Mock comment posting response
        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post.return_value = mock_post_response
        
        # Create test scan results
        issue = Issue(
            id="test_issue_1",
            type=IssueType.SECURITY,
            severity=Severity.CRITICAL,
            file_path="test.py",
            line_number=2,
            column=4,
            message="Unsafe use of eval()",
            rule_id="unsafe_eval"
        )
        
        scan_result = ScanResult(
            file_path="test.py",
            issues=[issue],
            parse_errors=[],
            analysis_time=0.1
        )
        
        result = self.client.post_line_comments(123, [scan_result])
        
        assert result is True
        # Should call GET for PR files and POST for comment
        mock_get.assert_called_once()
        mock_post.assert_called_once()
    
    @patch('requests.get')
    def test_get_pr_files_success(self, mock_get):
        """Test successful PR files retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'filename': 'file1.py', 'patch': '@@ -1,1 +1,2 @@\n+new line'},
            {'filename': 'file2.py', 'patch': '@@ -5,1 +5,1 @@\n-old line\n+new line'}
        ]
        mock_get.return_value = mock_response
        
        files = self.client._get_pr_files(123)
        
        assert len(files) == 2
        assert files[0]['filename'] == 'file1.py'
        assert files[1]['filename'] == 'file2.py'
    
    def test_extract_changed_lines(self):
        """Test extraction of changed line numbers from patch."""
        patch = '''@@ -10,7 +10,8 @@ def test_function():
     existing_line_1
     existing_line_2
-    old_line
+    new_line_1
+    new_line_2
     existing_line_3
     existing_line_4'''
        
        changed_lines = self.client._extract_changed_lines(patch)
        
        # Should include the new lines (12 and 13 in this case)
        assert 12 in changed_lines  # new_line_1
        assert 13 in changed_lines  # new_line_2
    
    def test_consolidate_comments(self):
        """Test comment consolidation for multiple issues on same line."""
        issues = [
            Issue(
                id="issue_1",
                type=IssueType.SECURITY,
                severity=Severity.HIGH,
                file_path="test.py",
                line_number=5,
                column=0,
                message="Security issue 1",
                rule_id="security_1"
            ),
            Issue(
                id="issue_2",
                type=IssueType.CODE_SMELL,
                severity=Severity.MEDIUM,
                file_path="test.py",
                line_number=5,
                column=10,
                message="Code smell issue",
                rule_id="code_smell_1"
            ),
            Issue(
                id="issue_3",
                type=IssueType.SECURITY,
                severity=Severity.CRITICAL,
                file_path="test.py",
                line_number=10,
                column=0,
                message="Security issue 2",
                rule_id="security_2"
            )
        ]
        
        consolidated = self.client._consolidate_comments(issues)
        
        # Should have 2 consolidated comments (line 5 and line 10)
        assert len(consolidated) == 2
        
        # Line 5 should have 2 issues
        line_5_comment = next(c for c in consolidated if c['line'] == 5)
        assert len(line_5_comment['issues']) == 2
        
        # Line 10 should have 1 issue
        line_10_comment = next(c for c in consolidated if c['line'] == 10)
        assert len(line_10_comment['issues']) == 1
    
    @patch('time.sleep')
    @patch('requests.post')
    def test_rate_limiting_and_retry(self, mock_post, mock_sleep):
        """Test rate limiting and retry logic."""
        # First call returns rate limit error, second succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 403
        rate_limit_response.headers = {'X-RateLimit-Remaining': '0'}
        
        success_response = Mock()
        success_response.status_code = 201
        success_response.json.return_value = {"id": 12345}
        
        mock_post.side_effect = [rate_limit_response, success_response]
        
        summary = {'total_files_analyzed': 1, 'total_issues_found': 1}
        result = self.client.post_summary_comment(123, summary)
        
        assert result is True
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep for rate limiting
    
    def test_format_summary_comment(self):
        """Test summary comment formatting."""
        summary = {
            'total_files_analyzed': 5,
            'total_issues_found': 10,
            'analysis_time_seconds': 2.5,
            'issues_by_severity': {
                'critical': 1,
                'high': 2,
                'medium': 4,
                'low': 3
            }
        }
        
        comment = self.client._format_summary_comment(summary)
        
        assert "🔍 KiroLinter Analysis Summary" in comment
        assert "5 files analyzed" in comment
        assert "10 issues found" in comment
        assert "2.50s" in comment
        assert "🔴 1 Critical" in comment
        assert "🟠 2 High" in comment
        assert "🟡 4 Medium" in comment
        assert "🟢 3 Low" in comment
    
    def test_format_line_comment(self):
        """Test line comment formatting."""
        issues = [
            Issue(
                id="test_issue",
                type=IssueType.SECURITY,
                severity=Severity.CRITICAL,
                file_path="test.py",
                line_number=5,
                column=0,
                message="Unsafe eval() usage",
                rule_id="unsafe_eval",
                cve_id="CVE-2023-1234"
            )
        ]
        
        comment = self.client._format_line_comment(issues)
        
        assert "🔴 **CRITICAL**" in comment
        assert "Unsafe eval() usage" in comment
        assert "CVE-2023-1234" in comment
        assert "Rule: unsafe_eval" in comment


class TestGitHubWebhookIntegration:
    """Test cases for GitHub webhook integration."""
    
    def test_webhook_payload_parsing(self):
        """Test parsing of GitHub webhook payloads."""
        # This would test webhook payload parsing if implemented
        # For now, this is a placeholder for future webhook functionality
        pass
    
    def test_pr_event_handling(self):
        """Test handling of pull request events."""
        # This would test PR event handling if implemented
        # For now, this is a placeholder for future webhook functionality
        pass


# Integration test fixtures
@pytest.fixture
def sample_scan_results():
    """Create sample scan results for testing."""
    issues = [
        Issue(
            id="security_1",
            type=IssueType.SECURITY,
            severity=Severity.CRITICAL,
            file_path="app.py",
            line_number=10,
            column=4,
            message="SQL injection vulnerability",
            rule_id="sql_injection"
        ),
        Issue(
            id="performance_1",
            type=IssueType.PERFORMANCE,
            severity=Severity.MEDIUM,
            file_path="utils.py",
            line_number=25,
            column=8,
            message="Inefficient loop operation",
            rule_id="inefficient_loop"
        )
    ]
    
    return [
        ScanResult(
            file_path="app.py",
            issues=[issues[0]],
            parse_errors=[],
            analysis_time=0.1
        ),
        ScanResult(
            file_path="utils.py",
            issues=[issues[1]],
            parse_errors=[],
            analysis_time=0.05
        )
    ]


@pytest.fixture
def github_pr_files_response():
    """Mock GitHub PR files API response."""
    return [
        {
            'filename': 'app.py',
            'patch': '''@@ -8,6 +8,7 @@ def get_user(user_id):
     def authenticate_user(username, password):
         # Vulnerable SQL query
+        query = f"SELECT * FROM users WHERE username='{username}'"
         cursor.execute(query)
         return cursor.fetchone()'''
        },
        {
            'filename': 'utils.py',
            'patch': '''@@ -22,4 +22,6 @@ def process_items(items):
     def calculate_total(items):
         total = 0
+        for i in range(len(items)):
+            total += items[i].price
         return total'''
        }
    ]