"""
Advanced GitHub Integration Features

Provides advanced GitHub features including branch protection rules,
PR automation, release management, and security integration.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from github import Github
from github.Repository import Repository
from github.Branch import Branch
from github.PullRequest import PullRequest
from github.Release import GitRelease

from .github_actions import GitHubActionsConnector, GitHubActionResult

logger = logging.getLogger(__name__)


@dataclass
class BranchProtectionRule:
    """Branch protection rule configuration"""
    pattern: str
    required_status_checks: List[str] = field(default_factory=list)
    enforce_admins: bool = False
    required_pull_request_reviews: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    required_linear_history: bool = False
    allow_force_pushes: bool = False
    allow_deletions: bool = False
    required_conversation_resolution: bool = True


@dataclass
class PRAnalysisResult:
    """Pull request analysis result"""
    pr_number: int
    quality_score: float
    risk_score: float
    issues_found: int
    critical_issues: int
    recommendations: List[str]
    approval_required: bool
    auto_mergeable: bool
    quality_gate_passed: bool


class GitHubAdvancedIntegration:
    """Advanced GitHub integration features"""
    
    def __init__(self, github_connector: GitHubActionsConnector):
        self.github = github_connector
        self.client = github_connector.github
        self.logger = logging.getLogger(__name__)
    
    async def setup_branch_protection(self, repo_full_name: str, 
                                    rules: List[BranchProtectionRule]) -> GitHubActionResult:
        """Setup branch protection rules with quality gates"""
        try:
            repo = self.github.get_repository(repo_full_name)
            
            results = []
            for rule in rules:
                try:
                    # Get or create the branch protection rule
                    protection_config = self._build_protection_config(rule)
                    
                    # Apply protection rule
                    branch = repo.get_branch(rule.pattern)
                    branch.edit_protection(**protection_config)
                    
                    results.append({
                        "pattern": rule.pattern,
                        "status": "configured",
                        "checks_required": rule.required_status_checks
                    })
                    
                    self.logger.info(f"Configured branch protection for {rule.pattern} in {repo_full_name}")
                    
                except Exception as e:
                    results.append({
                        "pattern": rule.pattern,
                        "status": "failed",
                        "error": str(e)
                    })
                    self.logger.error(f"Failed to configure protection for {rule.pattern}: {e}")
            
            success = all(r["status"] == "configured" for r in results)
            
            return GitHubActionResult(
                success=success,
                data={
                    "rules_configured": len([r for r in results if r["status"] == "configured"]),
                    "rules_failed": len([r for r in results if r["status"] == "failed"]),
                    "results": results
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up branch protection for {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    def _build_protection_config(self, rule: BranchProtectionRule) -> Dict[str, Any]:
        """Build GitHub API protection configuration"""
        config = {
            "required_status_checks": {
                "strict": True,
                "contexts": rule.required_status_checks
            } if rule.required_status_checks else None,
            "enforce_admins": rule.enforce_admins,
            "required_pull_request_reviews": rule.required_pull_request_reviews,
            "restrictions": rule.restrictions,
            "required_linear_history": rule.required_linear_history,
            "allow_force_pushes": rule.allow_force_pushes,
            "allow_deletions": rule.allow_deletions,
            "required_conversation_resolution": rule.required_conversation_resolution
        }
        
        # Remove None values
        return {k: v for k, v in config.items() if v is not None}
    
    async def analyze_pull_request(self, repo_full_name: str, pr_number: int,
                                 quality_threshold: float = 70.0) -> PRAnalysisResult:
        """Comprehensive pull request analysis"""
        try:
            repo = self.github.get_repository(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            # Get PR files and changes
            files = list(pr.get_files())
            changes = {
                "files_modified": len(files),
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": [f.filename for f in files]
            }
            
            # Simulate quality analysis (in real implementation, this would call KiroLinter)
            quality_score = await self._calculate_quality_score(changes, files)
            risk_score = await self._calculate_risk_score(pr, changes)
            
            # Analyze issues
            issues = await self._analyze_pr_issues(files, changes)
            critical_issues = sum(1 for issue in issues if issue.get("severity") == "critical")
            
            # Generate recommendations
            recommendations = await self._generate_pr_recommendations(pr, changes, issues)
            
            # Determine approval requirements
            approval_required = critical_issues > 0 or quality_score < quality_threshold
            auto_mergeable = not approval_required and quality_score >= quality_threshold
            quality_gate_passed = quality_score >= quality_threshold and critical_issues == 0
            
            result = PRAnalysisResult(
                pr_number=pr_number,
                quality_score=quality_score,
                risk_score=risk_score,
                issues_found=len(issues),
                critical_issues=critical_issues,
                recommendations=recommendations,
                approval_required=approval_required,
                auto_mergeable=auto_mergeable,
                quality_gate_passed=quality_gate_passed
            )
            
            self.logger.info(f"Analyzed PR #{pr_number}: Quality {quality_score:.1f}, Risk {risk_score:.1f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing PR #{pr_number} in {repo_full_name}: {e}")
            # Return default result with error
            return PRAnalysisResult(
                pr_number=pr_number,
                quality_score=0.0,
                risk_score=100.0,
                issues_found=0,
                critical_issues=0,
                recommendations=[f"Analysis failed: {str(e)}"],
                approval_required=True,
                auto_mergeable=False,
                quality_gate_passed=False
            )
    
    async def _calculate_quality_score(self, changes: Dict[str, Any], files: List[Any]) -> float:
        """Calculate quality score based on changes"""
        # Simplified quality scoring logic
        base_score = 85.0
        
        # Penalty for large changes
        if changes["files_modified"] > 20:
            base_score -= 10
        elif changes["files_modified"] > 10:
            base_score -= 5
        
        # Penalty for large additions/deletions
        total_changes = changes["additions"] + changes["deletions"]
        if total_changes > 1000:
            base_score -= 15
        elif total_changes > 500:
            base_score -= 10
        elif total_changes > 200:
            base_score -= 5
        
        # Bonus for test files
        test_files = sum(1 for f in changes["changed_files"] if "test" in f.lower())
        if test_files > 0:
            base_score += min(10, test_files * 2)
        
        return max(0, min(100, base_score))
    
    async def _calculate_risk_score(self, pr: PullRequest, changes: Dict[str, Any]) -> float:
        """Calculate deployment risk score"""
        base_risk = 20.0
        
        # Risk factors
        if changes["files_modified"] > 30:
            base_risk += 25
        elif changes["files_modified"] > 15:
            base_risk += 15
        elif changes["files_modified"] > 5:
            base_risk += 10
        
        # High-risk file patterns
        high_risk_patterns = [
            "config", "settings", "database", "migration", 
            "security", "auth", "payment", "production"
        ]
        
        for filename in changes["changed_files"]:
            if any(pattern in filename.lower() for pattern in high_risk_patterns):
                base_risk += 15
                break
        
        # Recent changes increase risk
        if hasattr(pr, 'created_at') and pr.created_at:
            hours_old = (datetime.now() - pr.created_at.replace(tzinfo=None)).total_seconds() / 3600
            if hours_old < 2:  # Very recent PR
                base_risk += 10
        
        return max(0, min(100, base_risk))
    
    async def _analyze_pr_issues(self, files: List[Any], changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze PR for potential issues"""
        issues = []
        
        # Large PR warning
        if changes["files_modified"] > 50:
            issues.append({
                "severity": "critical",
                "message": f"PR modifies {changes['files_modified']} files - consider breaking into smaller PRs",
                "category": "maintainability"
            })
        elif changes["files_modified"] > 25:
            issues.append({
                "severity": "high",
                "message": f"PR modifies {changes['files_modified']} files - review carefully",
                "category": "maintainability"
            })
        
        # Large change warning
        total_changes = changes["additions"] + changes["deletions"]
        if total_changes > 2000:
            issues.append({
                "severity": "high",
                "message": f"PR has {total_changes} line changes - very large change",
                "category": "complexity"
            })
        
        # Missing tests warning
        has_test_files = any("test" in f.lower() for f in changes["changed_files"])
        has_code_files = any(f.endswith(('.py', '.js', '.ts', '.java', '.go')) 
                           for f in changes["changed_files"])
        
        if has_code_files and not has_test_files:
            issues.append({
                "severity": "medium",
                "message": "Code changes without corresponding test changes",
                "category": "testing"
            })
        
        return issues
    
    async def _generate_pr_recommendations(self, pr: PullRequest, changes: Dict[str, Any], 
                                         issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for the PR"""
        recommendations = []
        
        # Based on size
        if changes["files_modified"] > 30:
            recommendations.append("Consider breaking this large PR into smaller, focused changes")
        
        # Based on issues
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        if critical_issues:
            recommendations.append("Address critical issues before merging")
        
        # Based on change patterns
        config_files = [f for f in changes["changed_files"] if "config" in f.lower()]
        if config_files:
            recommendations.append("Carefully review configuration changes for security implications")
        
        # Test recommendations
        has_tests = any("test" in f.lower() for f in changes["changed_files"])
        if not has_tests and changes["files_modified"] > 3:
            recommendations.append("Consider adding tests for the new functionality")
        
        # Documentation recommendations
        has_docs = any(f.endswith(('.md', '.rst', '.txt')) for f in changes["changed_files"])
        if not has_docs and changes["files_modified"] > 10:
            recommendations.append("Consider updating documentation for significant changes")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    async def auto_merge_pr(self, repo_full_name: str, pr_number: int, 
                          merge_method: str = "squash") -> GitHubActionResult:
        """Auto-merge PR if quality gates pass"""
        try:
            # First analyze the PR
            analysis = await self.analyze_pull_request(repo_full_name, pr_number)
            
            if not analysis.auto_mergeable:
                return GitHubActionResult(
                    success=False,
                    error=f"PR not auto-mergeable: Quality {analysis.quality_score:.1f}, Critical issues: {analysis.critical_issues}"
                )
            
            repo = self.github.get_repository(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            # Check if PR is mergeable
            if not pr.mergeable:
                return GitHubActionResult(
                    success=False,
                    error="PR has merge conflicts"
                )
            
            # Perform the merge
            merge_result = pr.merge(
                commit_message=f"Auto-merge: Quality gate passed (Score: {analysis.quality_score:.1f})",
                merge_method=merge_method
            )
            
            if merge_result.merged:
                self.logger.info(f"Successfully auto-merged PR #{pr_number} in {repo_full_name}")
                return GitHubActionResult(
                    success=True,
                    data={
                        "pr_number": pr_number,
                        "merge_commit_sha": merge_result.sha,
                        "quality_score": analysis.quality_score,
                        "merge_method": merge_method
                    }
                )
            else:
                return GitHubActionResult(
                    success=False,
                    error="Merge failed - GitHub API returned merged=False"
                )
                
        except Exception as e:
            self.logger.error(f"Error auto-merging PR #{pr_number} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def create_release_with_quality_check(self, repo_full_name: str, tag_name: str,
                                              target_commitish: str = "main",
                                              name: Optional[str] = None,
                                              body: Optional[str] = None,
                                              draft: bool = False,
                                              prerelease: bool = False) -> GitHubActionResult:
        """Create a release with quality validation"""
        try:
            repo = self.github.get_repository(repo_full_name)
            
            # Run quality check on the target branch
            quality_result = await self._validate_release_quality(repo_full_name, target_commitish)
            
            if not quality_result["passed"]:
                return GitHubActionResult(
                    success=False,
                    error=f"Release quality validation failed: {quality_result['reason']}"
                )
            
            # Generate release notes if not provided
            if not body:
                body = await self._generate_release_notes(repo, tag_name, target_commitish)
            
            # Create the release
            release = repo.create_git_release(
                tag=tag_name,
                name=name or tag_name,
                message=body or f"Release {tag_name}",
                target_commitish=target_commitish,
                draft=draft,
                prerelease=prerelease
            )
            
            self.logger.info(f"Created release {tag_name} in {repo_full_name}")
            
            return GitHubActionResult(
                success=True,
                data={
                    "release_id": release.id,
                    "tag_name": tag_name,
                    "url": release.html_url,
                    "quality_score": quality_result["score"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error creating release {tag_name} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def _validate_release_quality(self, repo_full_name: str, branch: str) -> Dict[str, Any]:
        """Validate quality for release"""
        try:
            # This would integrate with the actual KiroLinter quality gates
            # For now, return a mock validation
            return {
                "passed": True,
                "score": 85.0,
                "reason": "All quality gates passed"
            }
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "reason": f"Quality validation error: {str(e)}"
            }
    
    async def _generate_release_notes(self, repo: Repository, tag_name: str, 
                                    target_commitish: str) -> str:
        """Generate automated release notes"""
        try:
            # Get commits since last release
            releases = list(repo.get_releases())
            last_release = releases[0] if releases else None
            
            if last_release:
                commits = list(repo.get_commits(sha=target_commitish, since=last_release.created_at))
            else:
                commits = list(repo.get_commits(sha=target_commitish))
            
            # Limit to recent commits to avoid huge release notes
            commits = commits[:50]
            
            # Categorize commits
            features = []
            fixes = []
            other = []
            
            for commit in commits:
                message = commit.commit.message.split('\n')[0].strip()
                lower_message = message.lower()
                
                if any(word in lower_message for word in ['feat', 'feature', 'add']):
                    features.append(f"- {message}")
                elif any(word in lower_message for word in ['fix', 'bug', 'patch']):
                    fixes.append(f"- {message}")
                else:
                    other.append(f"- {message}")
            
            # Build release notes
            notes = f"# Release {tag_name}\n\n"
            
            if features:
                notes += "## ✨ New Features\n" + "\n".join(features[:10]) + "\n\n"
            
            if fixes:
                notes += "## 🐛 Bug Fixes\n" + "\n".join(fixes[:10]) + "\n\n"
            
            if other:
                notes += "## 🔧 Other Changes\n" + "\n".join(other[:10]) + "\n\n"
            
            notes += f"**Full Changelog**: {repo.html_url}/commits/{target_commitish}\n"
            
            return notes
            
        except Exception as e:
            return f"# Release {tag_name}\n\nAutomated release created by KiroLinter DevOps.\n\nError generating detailed notes: {str(e)}"
    
    async def setup_security_alerts(self, repo_full_name: str) -> GitHubActionResult:
        """Setup GitHub security alerts and dependency monitoring"""
        try:
            repo = self.github.get_repository(repo_full_name)
            
            # Enable vulnerability alerts (this requires admin permissions)
            success_count = 0
            errors = []
            
            try:
                # Enable dependency alerts
                repo.enable_vulnerability_alert()
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to enable vulnerability alerts: {str(e)}")
            
            try:
                # Enable automated security fixes (Dependabot)
                repo.enable_automated_security_fixes()
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to enable automated security fixes: {str(e)}")
            
            return GitHubActionResult(
                success=success_count > 0,
                data={
                    "features_enabled": success_count,
                    "errors": errors,
                    "vulnerability_alerts": success_count >= 1,
                    "automated_fixes": success_count >= 2
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up security alerts for {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def get_security_advisories(self, repo_full_name: str) -> GitHubActionResult:
        """Get security advisories for the repository"""
        try:
            # This would integrate with GitHub Security Advisory API
            # For now, return mock data
            advisories = [
                {
                    "id": "GHSA-xxxx-xxxx-xxxx",
                    "severity": "high",
                    "summary": "SQL Injection vulnerability in auth module",
                    "published_at": "2024-01-15T10:30:00Z",
                    "cve_id": "CVE-2024-1234"
                }
            ]
            
            return GitHubActionResult(
                success=True,
                data={
                    "advisories": advisories,
                    "total_advisories": len(advisories),
                    "high_severity": sum(1 for a in advisories if a["severity"] == "high"),
                    "critical_severity": sum(1 for a in advisories if a["severity"] == "critical")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting security advisories for {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )