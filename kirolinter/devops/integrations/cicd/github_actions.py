"""
GitHub Actions Integration

Comprehensive GitHub Actions connector providing workflow management, 
triggering, status monitoring, and advanced CI/CD orchestration capabilities.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from github import Github, Auth
from github.Repository import Repository
from github.Workflow import Workflow
from github.WorkflowRun import WorkflowRun
from github.CheckRun import CheckRun
from github.PullRequest import PullRequest

from .base_connector import BaseCICDConnector, PlatformType, WorkflowStatus, UniversalWorkflowInfo, TriggerResult
from ..git_events import GitEvent, GitEventType

logger = logging.getLogger(__name__)


class GitHubWorkflowStatus(Enum):
    """GitHub Actions workflow statuses"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"
    REQUESTED = "requested"
    PENDING = "pending"


class GitHubWorkflowConclusion(Enum):
    """GitHub Actions workflow conclusions"""
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"
    STARTUP_FAILURE = "startup_failure"


@dataclass
class GitHubWorkflowInfo:
    """GitHub workflow information"""
    id: int
    name: str
    path: str
    state: str
    created_at: datetime
    updated_at: datetime
    url: str
    badge_url: str


@dataclass
class GitHubWorkflowRunInfo:
    """GitHub workflow run information"""
    id: int
    workflow_id: int
    workflow_name: str
    head_branch: str
    head_sha: str
    status: GitHubWorkflowStatus
    conclusion: Optional[GitHubWorkflowConclusion]
    url: str
    html_url: str
    created_at: datetime
    updated_at: datetime
    run_number: int
    run_attempt: int
    jobs_url: str
    logs_url: str
    artifacts_url: str


@dataclass
class GitHubActionResult:
    """Result of a GitHub Actions operation"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    workflow_run_id: Optional[int] = None
    workflow_run_url: Optional[str] = None


class GitHubActionsConnector(BaseCICDConnector):
    """GitHub Actions integration connector"""
    
    def __init__(self, github_token: str, webhook_secret: Optional[str] = None):
        """Initialize GitHub Actions connector"""
        super().__init__("github_actions")
        
        self.github_token = github_token
        self.webhook_secret = webhook_secret
        
        # Initialize GitHub client
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        
        # Cache and state management
        self.workflow_cache: Dict[str, Dict[int, GitHubWorkflowInfo]] = {}
        self.run_cache: Dict[str, Dict[int, GitHubWorkflowRunInfo]] = {}
        self.status_callbacks: List[Callable] = []
        self.repositories: Dict[str, Repository] = {}
        
        # Rate limiting and performance
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now()
        self.last_rate_limit_check = datetime.now()
        
        self.logger = logging.getLogger(__name__)
    
    def add_status_callback(self, callback: Callable[[GitHubWorkflowRunInfo], None]):
        """Add a callback for workflow status updates"""
        self.status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable):
        """Remove a status callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    async def _check_rate_limit(self):
        """Check and handle GitHub API rate limits"""
        try:
            # Check every 10 minutes
            if (datetime.now() - self.last_rate_limit_check).total_seconds() < 600:
                return
            
            rate_limit = self.github.get_rate_limit()
            self.rate_limit_remaining = rate_limit.core.remaining
            self.rate_limit_reset = datetime.fromtimestamp(rate_limit.core.reset.timestamp())
            self.last_rate_limit_check = datetime.now()
            
            if self.rate_limit_remaining < 100:
                reset_in = (self.rate_limit_reset - datetime.now()).total_seconds()
                self.logger.warning(f"GitHub API rate limit low: {self.rate_limit_remaining} remaining, resets in {reset_in}s")
            
        except Exception as e:
            self.logger.error(f"Error checking GitHub rate limit: {e}")
    
    def get_repository(self, repo_full_name: str) -> Repository:
        """Get repository object with caching"""
        if repo_full_name not in self.repositories:
            try:
                self.repositories[repo_full_name] = self.github.get_repo(repo_full_name)
            except Exception as e:
                self.logger.error(f"Error getting repository {repo_full_name}: {e}")
                raise
        return self.repositories[repo_full_name]
    
    async def discover_github_workflows(self, repo_full_name: str, force_refresh: bool = False) -> List[GitHubWorkflowInfo]:
        """Discover all workflows in a repository"""
        try:
            await self._check_rate_limit()
            
            if not force_refresh and repo_full_name in self.workflow_cache:
                return list(self.workflow_cache[repo_full_name].values())
            
            repo = self.get_repository(repo_full_name)
            workflows = repo.get_workflows()
            
            workflow_info = []
            for workflow in workflows:
                info = GitHubWorkflowInfo(
                    id=workflow.id,
                    name=workflow.name,
                    path=workflow.path,
                    state=workflow.state,
                    created_at=workflow.created_at,
                    updated_at=workflow.updated_at,
                    url=workflow.url,
                    badge_url=workflow.badge_url
                )
                workflow_info.append(info)
            
            # Cache the results
            self.workflow_cache[repo_full_name] = {info.id: info for info in workflow_info}
            
            self.logger.info(f"Discovered {len(workflow_info)} workflows in {repo_full_name}")
            return workflow_info
            
        except Exception as e:
            self.logger.error(f"Error discovering workflows in {repo_full_name}: {e}")
            return []
    
    async def get_workflow_runs(self, repo_full_name: str, workflow_id: Optional[int] = None, 
                              branch: Optional[str] = None, limit: int = 50) -> List[GitHubWorkflowRunInfo]:
        """Get workflow runs for a repository or specific workflow"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            
            if workflow_id:
                workflow = repo.get_workflow(workflow_id)
                runs = workflow.get_runs()
            else:
                runs = repo.get_workflow_runs(branch=branch)
            
            run_info = []
            count = 0
            for run in runs:
                if count >= limit:
                    break
                
                info = GitHubWorkflowRunInfo(
                    id=run.id,
                    workflow_id=run.workflow_id,
                    workflow_name=run.name,
                    head_branch=run.head_branch,
                    head_sha=run.head_sha,
                    status=GitHubWorkflowStatus(run.status),
                    conclusion=GitHubWorkflowConclusion(run.conclusion) if run.conclusion else None,
                    url=run.url,
                    html_url=run.html_url,
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                    run_number=run.run_number,
                    run_attempt=run.run_attempt,
                    jobs_url=run.jobs_url,
                    logs_url=run.logs_url,
                    artifacts_url=run.artifacts_url
                )
                run_info.append(info)
                count += 1
            
            self.logger.info(f"Retrieved {len(run_info)} workflow runs from {repo_full_name}")
            return run_info
            
        except Exception as e:
            self.logger.error(f"Error getting workflow runs from {repo_full_name}: {e}")
            return []
    
    async def trigger_github_workflow(self, repo_full_name: str, workflow_id: Union[int, str], 
                              ref: str = "main", inputs: Optional[Dict[str, Any]] = None) -> GitHubActionResult:
        """Trigger a GitHub Actions workflow"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            workflow = repo.get_workflow(workflow_id)
            
            # Trigger the workflow
            result = workflow.create_dispatch(ref=ref, inputs=inputs or {})
            
            if result:
                self.logger.info(f"Successfully triggered workflow {workflow_id} in {repo_full_name} on {ref}")
                
                # Try to get the workflow run that was just created
                # Note: There might be a delay before the run appears
                await asyncio.sleep(2)
                recent_runs = await self.get_workflow_runs(repo_full_name, workflow_id, limit=1)
                
                if recent_runs:
                    run = recent_runs[0]
                    return GitHubActionResult(
                        success=True,
                        data={
                            "workflow_id": workflow_id,
                            "ref": ref,
                            "inputs": inputs,
                            "triggered_at": datetime.now().isoformat()
                        },
                        workflow_run_id=run.id,
                        workflow_run_url=run.html_url
                    )
                
                return GitHubActionResult(
                    success=True,
                    data={
                        "workflow_id": workflow_id,
                        "ref": ref,
                        "inputs": inputs,
                        "triggered_at": datetime.now().isoformat()
                    }
                )
            else:
                return GitHubActionResult(
                    success=False,
                    error="Workflow dispatch returned False - check if workflow supports workflow_dispatch"
                )
                
        except Exception as e:
            self.logger.error(f"Error triggering workflow {workflow_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def cancel_workflow_run(self, repo_full_name: str, run_id: int) -> GitHubActionResult:
        """Cancel a running GitHub Actions workflow"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            run = repo.get_workflow_run(run_id)
            
            if run.cancel():
                self.logger.info(f"Successfully cancelled workflow run {run_id} in {repo_full_name}")
                return GitHubActionResult(
                    success=True,
                    data={
                        "run_id": run_id,
                        "cancelled_at": datetime.now().isoformat()
                    },
                    workflow_run_id=run_id,
                    workflow_run_url=run.html_url
                )
            else:
                return GitHubActionResult(
                    success=False,
                    error="Failed to cancel workflow run - it may not be cancellable"
                )
                
        except Exception as e:
            self.logger.error(f"Error cancelling workflow run {run_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def rerun_workflow(self, repo_full_name: str, run_id: int, 
                           rerun_failed_only: bool = False) -> GitHubActionResult:
        """Rerun a GitHub Actions workflow"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            run = repo.get_workflow_run(run_id)
            
            if rerun_failed_only:
                result = run.rerun_failed_jobs()
            else:
                result = run.rerun()
            
            if result:
                self.logger.info(f"Successfully reran workflow run {run_id} in {repo_full_name}")
                return GitHubActionResult(
                    success=True,
                    data={
                        "run_id": run_id,
                        "rerun_failed_only": rerun_failed_only,
                        "reran_at": datetime.now().isoformat()
                    },
                    workflow_run_id=run_id,
                    workflow_run_url=run.html_url
                )
            else:
                return GitHubActionResult(
                    success=False,
                    error="Failed to rerun workflow - it may not be eligible for rerun"
                )
                
        except Exception as e:
            self.logger.error(f"Error rerunning workflow run {run_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def get_workflow_run_logs(self, repo_full_name: str, run_id: int) -> GitHubActionResult:
        """Download workflow run logs"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            run = repo.get_workflow_run(run_id)
            
            # Get download URL for logs
            logs_url = run.logs_url
            
            return GitHubActionResult(
                success=True,
                data={
                    "run_id": run_id,
                    "logs_url": logs_url,
                    "download_url": f"{logs_url}/download"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting workflow run logs for {run_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def get_workflow_artifacts(self, repo_full_name: str, run_id: int) -> GitHubActionResult:
        """Get workflow run artifacts"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            run = repo.get_workflow_run(run_id)
            artifacts = run.get_artifacts()
            
            artifact_info = []
            for artifact in artifacts:
                artifact_info.append({
                    "id": artifact.id,
                    "name": artifact.name,
                    "size_in_bytes": artifact.size_in_bytes,
                    "url": artifact.url,
                    "archive_download_url": artifact.archive_download_url,
                    "expired": artifact.expired,
                    "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
                    "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None
                })
            
            return GitHubActionResult(
                success=True,
                data={
                    "run_id": run_id,
                    "artifacts": artifact_info,
                    "artifact_count": len(artifact_info)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting workflow artifacts for {run_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def create_check_run(self, repo_full_name: str, commit_sha: str, 
                             check_name: str, status: str = "in_progress",
                             conclusion: Optional[str] = None, 
                             details_url: Optional[str] = None) -> GitHubActionResult:
        """Create a GitHub check run for quality gate integration"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            
            check_data = {
                "name": check_name,
                "head_sha": commit_sha,
                "status": status
            }
            
            if conclusion:
                check_data["conclusion"] = conclusion
            
            if details_url:
                check_data["details_url"] = details_url
            
            check_run = repo.create_check_run(**check_data)
            
            self.logger.info(f"Created check run {check_name} for {commit_sha} in {repo_full_name}")
            return GitHubActionResult(
                success=True,
                data={
                    "check_run_id": check_run.id,
                    "name": check_name,
                    "status": status,
                    "conclusion": conclusion,
                    "url": check_run.html_url
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error creating check run {check_name} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def update_check_run(self, repo_full_name: str, check_run_id: int,
                             status: Optional[str] = None, conclusion: Optional[str] = None,
                             output_title: Optional[str] = None, output_summary: Optional[str] = None) -> GitHubActionResult:
        """Update an existing GitHub check run"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            check_run = repo.get_check_run(check_run_id)
            
            update_data = {}
            if status:
                update_data["status"] = status
            if conclusion:
                update_data["conclusion"] = conclusion
            if output_title or output_summary:
                update_data["output"] = {
                    "title": output_title or "",
                    "summary": output_summary or ""
                }
            
            check_run.edit(**update_data)
            
            self.logger.info(f"Updated check run {check_run_id} in {repo_full_name}")
            return GitHubActionResult(
                success=True,
                data={
                    "check_run_id": check_run_id,
                    "status": status,
                    "conclusion": conclusion,
                    "updated_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error updating check run {check_run_id} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def add_pr_comment(self, repo_full_name: str, pr_number: int, comment: str) -> GitHubActionResult:
        """Add a comment to a pull request"""
        try:
            await self._check_rate_limit()
            
            repo = self.get_repository(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            comment_obj = pr.create_issue_comment(comment)
            
            self.logger.info(f"Added comment to PR #{pr_number} in {repo_full_name}")
            return GitHubActionResult(
                success=True,
                data={
                    "comment_id": comment_obj.id,
                    "pr_number": pr_number,
                    "comment_url": comment_obj.html_url,
                    "created_at": comment_obj.created_at.isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error adding comment to PR #{pr_number} in {repo_full_name}: {e}")
            return GitHubActionResult(
                success=False,
                error=str(e)
            )
    
    async def monitor_workflow_runs(self, repo_full_name: str, 
                                  callback: Optional[Callable[[GitHubWorkflowRunInfo], None]] = None,
                                  poll_interval: int = 30) -> None:
        """Monitor workflow runs and call callbacks on status changes"""
        last_check = {}
        
        while True:
            try:
                runs = await self.get_workflow_runs(repo_full_name, limit=20)
                
                for run in runs:
                    # Check if this is a new run or status change
                    key = f"{repo_full_name}:{run.id}"
                    
                    if key not in last_check or last_check[key].status != run.status:
                        last_check[key] = run
                        
                        # Call the specific callback if provided
                        if callback:
                            try:
                                callback(run)
                            except Exception as e:
                                self.logger.error(f"Error in workflow monitoring callback: {e}")
                        
                        # Call registered status callbacks
                        for status_callback in self.status_callbacks:
                            try:
                                status_callback(run)
                            except Exception as e:
                                self.logger.error(f"Error in status callback: {e}")
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring workflow runs for {repo_full_name}: {e}")
                await asyncio.sleep(poll_interval)
    
    # Universal interface methods (implementing BaseCICDConnector)
    
    async def discover_workflows(self, repository: str, **kwargs) -> List[UniversalWorkflowInfo]:
        """Discover workflows in a repository (universal interface)"""
        try:
            github_workflows = await self.discover_github_workflows(repository, **kwargs)
            
            universal_workflows = []
            for workflow in github_workflows:
                # Get recent runs to determine status
                runs = await self.get_workflow_runs(repository, workflow.id, limit=1)
                
                status = WorkflowStatus.UNKNOWN
                commit_sha = ""
                branch = ""
                
                if runs:
                    latest_run = runs[0]
                    commit_sha = latest_run.head_sha
                    branch = latest_run.head_branch
                    
                    # Map GitHub status to universal status
                    if latest_run.status == GitHubWorkflowStatus.COMPLETED:
                        if latest_run.conclusion == GitHubWorkflowConclusion.SUCCESS:
                            status = WorkflowStatus.SUCCESS
                        elif latest_run.conclusion == GitHubWorkflowConclusion.FAILURE:
                            status = WorkflowStatus.FAILED
                        elif latest_run.conclusion == GitHubWorkflowConclusion.CANCELLED:
                            status = WorkflowStatus.CANCELLED
                        elif latest_run.conclusion == GitHubWorkflowConclusion.SKIPPED:
                            status = WorkflowStatus.SKIPPED
                        elif latest_run.conclusion == GitHubWorkflowConclusion.TIMED_OUT:
                            status = WorkflowStatus.TIMEOUT
                    elif latest_run.status == GitHubWorkflowStatus.IN_PROGRESS:
                        status = WorkflowStatus.RUNNING
                    elif latest_run.status == GitHubWorkflowStatus.QUEUED:
                        status = WorkflowStatus.QUEUED
                
                universal_workflow = UniversalWorkflowInfo(
                    id=workflow.id,
                    name=workflow.name,
                    platform=PlatformType.GITHUB_ACTIONS,
                    status=status,
                    repository=repository,
                    branch=branch,
                    commit_sha=commit_sha,
                    url=workflow.url,
                    created_at=workflow.created_at.isoformat(),
                    updated_at=workflow.updated_at.isoformat(),
                    metadata={
                        "path": workflow.path,
                        "state": workflow.state,
                        "badge_url": workflow.badge_url
                    }
                )
                universal_workflows.append(universal_workflow)
            
            return universal_workflows
            
        except Exception as e:
            self.logger.error(f"Error in universal discover_workflows: {e}")
            return []
    
    async def trigger_workflow(self, repository: str, workflow_id: Union[int, str], 
                              branch: str = "main", inputs: Optional[Dict[str, Any]] = None) -> TriggerResult:
        """Trigger a workflow (universal interface)"""
        result = await self.trigger_github_workflow(repository, workflow_id, branch, inputs)
        
        return TriggerResult(
            success=result.success,
            workflow_id=workflow_id,
            run_id=result.workflow_run_id,
            url=result.workflow_run_url,
            error=result.error,
            metadata=result.data or {}
        )
    
    async def get_workflow_status(self, repository: str, workflow_id: Union[int, str], 
                                run_id: Optional[Union[int, str]] = None) -> UniversalWorkflowInfo:
        """Get workflow status (universal interface)"""
        try:
            if run_id:
                # Get specific run status
                runs = await self.get_workflow_runs(repository, workflow_id, limit=50)
                run = next((r for r in runs if r.id == int(run_id)), None)
                
                if not run:
                    raise ValueError(f"Workflow run {run_id} not found")
                
                # Map GitHub status to universal status
                status = WorkflowStatus.UNKNOWN
                if run.status == GitHubWorkflowStatus.COMPLETED:
                    if run.conclusion == GitHubWorkflowConclusion.SUCCESS:
                        status = WorkflowStatus.SUCCESS
                    elif run.conclusion == GitHubWorkflowConclusion.FAILURE:
                        status = WorkflowStatus.FAILED
                    elif run.conclusion == GitHubWorkflowConclusion.CANCELLED:
                        status = WorkflowStatus.CANCELLED
                    elif run.conclusion == GitHubWorkflowConclusion.SKIPPED:
                        status = WorkflowStatus.SKIPPED
                    elif run.conclusion == GitHubWorkflowConclusion.TIMED_OUT:
                        status = WorkflowStatus.TIMEOUT
                elif run.status == GitHubWorkflowStatus.IN_PROGRESS:
                    status = WorkflowStatus.RUNNING
                elif run.status == GitHubWorkflowStatus.QUEUED:
                    status = WorkflowStatus.QUEUED
                
                return UniversalWorkflowInfo(
                    id=run.workflow_id,
                    name=run.workflow_name,
                    platform=PlatformType.GITHUB_ACTIONS,
                    status=status,
                    repository=repository,
                    branch=run.head_branch,
                    commit_sha=run.head_sha,
                    url=run.html_url,
                    created_at=run.created_at.isoformat(),
                    updated_at=run.updated_at.isoformat(),
                    metadata={
                        "run_id": run.id,
                        "run_number": run.run_number,
                        "run_attempt": run.run_attempt
                    }
                )
            else:
                # Get workflow info with latest run status
                workflows = await self.discover_workflows(repository)
                workflow = next((w for w in workflows if w.id == workflow_id), None)
                
                if not workflow:
                    raise ValueError(f"Workflow {workflow_id} not found")
                
                return workflow
                
        except Exception as e:
            self.logger.error(f"Error getting workflow status: {e}")
            # Return a default workflow info with error status
            return UniversalWorkflowInfo(
                id=workflow_id,
                name="Unknown",
                platform=PlatformType.GITHUB_ACTIONS,
                status=WorkflowStatus.UNKNOWN,
                repository=repository,
                branch="",
                commit_sha="",
                url="",
                created_at="",
                updated_at="",
                metadata={"error": str(e)}
            )
    
    async def cancel_workflow(self, repository: str, run_id: Union[int, str]) -> bool:
        """Cancel a running workflow (universal interface)"""
        result = await self.cancel_workflow_run(repository, int(run_id))
        return result.success
    
    async def get_connector_status(self) -> Dict[str, Any]:
        """Get the status of the GitHub Actions connector"""
        try:
            await self._check_rate_limit()
            
            user = self.github.get_user()
            
            return {
                "connected": True,
                "platform": "github_actions",
                "authenticated_user": user.login,
                "rate_limit_remaining": self.rate_limit_remaining,
                "rate_limit_reset": self.rate_limit_reset.isoformat(),
                "repositories_cached": len(self.repositories),
                "workflows_cached": sum(len(workflows) for workflows in self.workflow_cache.values()),
                "status_callbacks": len(self.status_callbacks),
                "last_rate_limit_check": self.last_rate_limit_check.isoformat()
            }
            
        except Exception as e:
            return {
                "connected": False,
                "platform": "github_actions",
                "error": str(e),
                "rate_limit_remaining": self.rate_limit_remaining,
                "repositories_cached": len(self.repositories),
                "workflows_cached": sum(len(workflows) for workflows in self.workflow_cache.values())
            }


class GitHubActionsQualityGateIntegration:
    """Integration between KiroLinter quality gates and GitHub Actions"""
    
    def __init__(self, github_connector: GitHubActionsConnector):
        self.github = github_connector
        self.logger = logging.getLogger(__name__)
    
    async def create_quality_gate_check(self, repo_full_name: str, commit_sha: str, 
                                      gate_type: str, status: str = "in_progress") -> GitHubActionResult:
        """Create a quality gate check run"""
        check_name = f"KiroLinter Quality Gate - {gate_type.replace('_', ' ').title()}"
        
        return await self.github.create_check_run(
            repo_full_name=repo_full_name,
            commit_sha=commit_sha,
            check_name=check_name,
            status=status,
            details_url=f"https://kirolinter.dev/quality-gates/{gate_type}"
        )
    
    async def update_quality_gate_result(self, repo_full_name: str, check_run_id: int,
                                       passed: bool, summary: str, details: str = "") -> GitHubActionResult:
        """Update quality gate check run with results"""
        conclusion = "success" if passed else "failure"
        title = f"Quality Gate {'Passed' if passed else 'Failed'}"
        
        return await self.github.update_check_run(
            repo_full_name=repo_full_name,
            check_run_id=check_run_id,
            status="completed",
            conclusion=conclusion,
            output_title=title,
            output_summary=f"{summary}\n\n{details}"
        )
    
    async def add_quality_report_comment(self, repo_full_name: str, pr_number: int,
                                       quality_results: Dict[str, Any]) -> GitHubActionResult:
        """Add a comprehensive quality report comment to a PR"""
        
        # Generate markdown comment
        comment = self._generate_quality_comment(quality_results)
        
        return await self.github.add_pr_comment(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            comment=comment
        )
    
    def _generate_quality_comment(self, results: Dict[str, Any]) -> str:
        """Generate a markdown comment for quality results"""
        
        status_emoji = "✅" if results.get("overall_passed", False) else "❌"
        overall_score = results.get("overall_score", 0)
        
        comment = f"""## {status_emoji} KiroLinter Quality Report

**Overall Score**: {overall_score:.1f}/100

### Quality Gate Results
"""
        
        for gate_type, gate_result in results.get("gates", {}).items():
            gate_emoji = "✅" if gate_result.get("passed", False) else "❌"
            gate_score = gate_result.get("score", 0)
            
            comment += f"\n{gate_emoji} **{gate_type.replace('_', ' ').title()}**: {gate_score:.1f}/100"
            
            if gate_result.get("issues"):
                comment += f" ({len(gate_result['issues'])} issues)"
        
        # Add issue summary
        if results.get("issues"):
            comment += "\n\n### Issues Found\n"
            
            issues_by_severity = {}
            for issue in results["issues"]:
                severity = issue.get("severity", "unknown")
                if severity not in issues_by_severity:
                    issues_by_severity[severity] = []
                issues_by_severity[severity].append(issue)
            
            for severity in ["critical", "high", "medium", "low"]:
                if severity in issues_by_severity:
                    count = len(issues_by_severity[severity])
                    comment += f"\n- **{severity.title()}**: {count} issues"
        
        comment += f"\n\n---\n*Generated by [KiroLinter DevOps](https://kirolinter.dev) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*"
        
        return comment