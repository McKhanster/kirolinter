"""
GitHub API client for posting PR comments and reviews.
"""

import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from kirolinter.core.scanner import ScanResult
from kirolinter.models.issue import Issue


@dataclass
class PRComment:
    """Represents a comment to be posted on a PR."""
    file_path: str
    line_number: int
    message: str
    suggestion: Optional[str] = None


class GitHubClient:
    """GitHub API client for KiroLinter integration."""
    
    def __init__(self, token: str, repository: str):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
            repository: Repository in format 'owner/repo'
        """
        self.token = token
        self.repository = repository
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "KiroLinter/0.1.0"
        })
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
    
    def post_pr_review(self, pr_number: int, scan_results: List[ScanResult], 
                      summary: str) -> bool:
        """
        Post a comprehensive review on a pull request.
        
        Args:
            pr_number: Pull request number
            scan_results: List of scan results from analysis
            summary: Summary comment for the review
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get PR information
            pr_info = self._get_pr_info(pr_number)
            if not pr_info:
                return False
            
            # Generate review comments
            comments = self._generate_review_comments(scan_results, pr_info)
            
            # Post review with comments
            return self._post_review(pr_number, comments, summary)
            
        except Exception as e:
            print(f"Error posting PR review: {e}")
            return False
    
    def post_line_comments(self, pr_number: int, scan_results: List[ScanResult]) -> bool:
        """
        Post line-specific comments on a pull request.
        
        Args:
            pr_number: Pull request number
            scan_results: List of scan results from analysis
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get PR information
            pr_info = self._get_pr_info(pr_number)
            if not pr_info:
                return False
            
            # Generate comments
            comments = self._generate_review_comments(scan_results, pr_info)
            
            # Post individual comments
            success_count = 0
            for comment in comments[:50]:  # Limit to 50 comments
                if self._post_single_comment(pr_number, comment):
                    success_count += 1
                time.sleep(0.1)  # Rate limiting
            
            return success_count > 0
            
        except Exception as e:
            print(f"Error posting line comments: {e}")
            return False
    
    def post_summary_comment(self, pr_number: int, analysis_summary: Dict[str, Any]) -> bool:
        """
        Post a summary comment with analysis overview.
        
        Args:
            pr_number: Pull request number
            analysis_summary: Analysis results summary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            summary_text = self._generate_summary_text(analysis_summary)
            
            url = f"{self.base_url}/repos/{self.repository}/issues/{pr_number}/comments"
            data = {"body": summary_text}
            
            response = self.session.post(url, json=data)
            self._update_rate_limit(response)
            
            return response.status_code == 201
            
        except Exception as e:
            print(f"Error posting summary comment: {e}")
            return False
    
    def create_status_check(self, commit_sha: str, state: str, description: str, 
                          target_url: Optional[str] = None) -> bool:
        """
        Create a status check on a commit.
        
        Args:
            commit_sha: Commit SHA to create status for
            state: Status state ('pending', 'success', 'error', 'failure')
            description: Status description
            target_url: Optional URL for more details
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/repos/{self.repository}/statuses/{commit_sha}"
            data = {
                "state": state,
                "description": description,
                "context": "KiroLinter/code-quality"
            }
            
            if target_url:
                data["target_url"] = target_url
            
            response = self.session.post(url, json=data)
            self._update_rate_limit(response)
            
            return response.status_code == 201
            
        except Exception as e:
            print(f"Error creating status check: {e}")
            return False
    
    def _get_pr_info(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get pull request information."""
        try:
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}"
            response = self.session.get(url)
            self._update_rate_limit(response)
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            print(f"Error getting PR info: {e}")
            return None
    
    def _generate_review_comments(self, scan_results: List[ScanResult], 
                                pr_info: Dict[str, Any]) -> List[PRComment]:
        """Generate review comments from scan results."""
        comments = []
        
        for scan_result in scan_results:
            for issue in scan_result.issues:
                # Create comment for each issue
                comment_text = self._format_issue_comment(issue)
                
                comment = PRComment(
                    file_path=scan_result.file_path,
                    line_number=issue.line_number,
                    message=comment_text,
                    suggestion=self._format_suggestion(issue) if hasattr(issue, 'suggestion') else None
                )
                comments.append(comment)
        
        return comments
    
    def _format_issue_comment(self, issue: Issue) -> str:
        """Format an issue as a comment."""
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        emoji = severity_emoji.get(issue.severity.value, '⚪')
        
        comment = f"{emoji} **{issue.severity.value.upper()}**: {issue.message}\n\n"
        comment += f"**Rule**: `{issue.rule_id}`\n"
        comment += f"**Type**: {issue.type.value.replace('_', ' ').title()}\n"
        
        # Add suggestion if available
        if hasattr(issue, 'suggestion') and issue.suggestion:
            suggestion = issue.suggestion
            comment += f"\n**💡 Suggested Fix** (Confidence: {suggestion.confidence:.0%}):\n"
            comment += f"{suggestion.explanation}\n"
            
            if suggestion.suggested_code:
                comment += f"\n```python\n{suggestion.suggested_code}\n```\n"
            
            if suggestion.diff_patch:
                comment += f"\n<details>\n<summary>View diff</summary>\n\n```diff\n{suggestion.diff_patch}\n```\n</details>"
        
        comment += f"\n\n*Powered by [KiroLinter](https://github.com/yourusername/kirolinter) 🔍*"
        
        return comment
    
    def _format_suggestion(self, issue: Issue) -> Optional[str]:
        """Format suggestion for GitHub's suggestion feature."""
        if not hasattr(issue, 'suggestion') or not issue.suggestion:
            return None
        
        suggestion = issue.suggestion
        if suggestion.fix_type.value == 'replace' and suggestion.suggested_code:
            return suggestion.suggested_code
        
        return None
    
    def _post_review(self, pr_number: int, comments: List[PRComment], 
                    summary: str) -> bool:
        """Post a review with multiple comments."""
        try:
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}/reviews"
            
            # Format comments for GitHub API
            review_comments = []
            for comment in comments[:50]:  # Limit comments
                review_comments.append({
                    "path": comment.file_path,
                    "line": comment.line_number,
                    "body": comment.message
                })
            
            data = {
                "body": summary,
                "event": "COMMENT",  # Use COMMENT instead of REQUEST_CHANGES
                "comments": review_comments
            }
            
            response = self.session.post(url, json=data)
            self._update_rate_limit(response)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error posting review: {e}")
            return False
    
    def _post_single_comment(self, pr_number: int, comment: PRComment) -> bool:
        """Post a single line comment."""
        try:
            # Get PR info for commit SHA
            pr_info = self._get_pr_info(pr_number)
            if not pr_info:
                return False
            
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}/comments"
            data = {
                "body": comment.message,
                "commit_id": pr_info["head"]["sha"],
                "path": comment.file_path,
                "line": comment.line_number
            }
            
            response = self.session.post(url, json=data)
            self._update_rate_limit(response)
            
            return response.status_code == 201
            
        except Exception as e:
            print(f"Error posting single comment: {e}")
            return False
    
    def _generate_summary_text(self, analysis_summary: Dict[str, Any]) -> str:
        """Generate summary comment text."""
        total_issues = analysis_summary.get('total_issues_found', 0)
        total_files = analysis_summary.get('total_files_analyzed', 0)
        analysis_time = analysis_summary.get('analysis_time_seconds', 0)
        
        if total_issues == 0:
            return f"""## 🎉 KiroLinter Analysis - No Issues Found!

All analyzed files passed the code quality check.

**Analysis Summary:**
- Files analyzed: {total_files}
- Issues found: 0
- Analysis time: {analysis_time:.2f}s
- Status: ✅ **Passed**

*Great job maintaining high code quality!*

---
*Analysis powered by [KiroLinter](https://github.com/yourusername/kirolinter) 🔍*"""
        
        issues_by_severity = analysis_summary.get('issues_by_severity', {})
        
        summary = f"""## 📊 KiroLinter Analysis Results

**Summary:**
- Files analyzed: {total_files}
- Total issues found: {total_issues}
- Analysis time: {analysis_time:.2f}s

**Issues by Severity:**
- 🔴 Critical: {issues_by_severity.get('critical', 0)}
- 🟠 High: {issues_by_severity.get('high', 0)}
- 🟡 Medium: {issues_by_severity.get('medium', 0)}
- 🟢 Low: {issues_by_severity.get('low', 0)}

**Status:** {self._get_status_from_issues(issues_by_severity)}

{self._get_recommendations(issues_by_severity)}

---
*Analysis powered by [KiroLinter](https://github.com/yourusername/kirolinter) 🔍*"""
        
        return summary
    
    def _get_status_from_issues(self, issues_by_severity: Dict[str, int]) -> str:
        """Get status based on issue severity."""
        if issues_by_severity.get('critical', 0) > 0:
            return "❌ **Failed** - Critical issues found"
        elif issues_by_severity.get('high', 0) > 5:
            return "⚠️ **Warning** - Many high severity issues"
        elif issues_by_severity.get('high', 0) > 0:
            return "⚠️ **Warning** - High severity issues found"
        else:
            return "✅ **Passed** - No critical issues"
    
    def _get_recommendations(self, issues_by_severity: Dict[str, int]) -> str:
        """Get recommendations based on issues found."""
        if issues_by_severity.get('critical', 0) > 0:
            return "⚠️ **Please address critical security issues before merging.**"
        elif issues_by_severity.get('high', 0) > 10:
            return "💡 **Consider addressing high severity issues to improve code quality.**"
        elif sum(issues_by_severity.values()) > 50:
            return "📝 **Many issues found. Consider running KiroLinter locally for faster feedback.**"
        else:
            return "🎯 **Good code quality! Consider addressing remaining issues when convenient.**"
    
    def _update_rate_limit(self, response: requests.Response):
        """Update rate limit information from response headers."""
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in response.headers:
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
    
    def check_rate_limit(self) -> bool:
        """Check if we're approaching rate limits."""
        if self.rate_limit_remaining < 100:
            current_time = time.time()
            if current_time < self.rate_limit_reset:
                sleep_time = self.rate_limit_reset - current_time
                print(f"Rate limit low ({self.rate_limit_remaining}), sleeping for {sleep_time:.0f}s")
                time.sleep(sleep_time)
        
        return self.rate_limit_remaining > 0