"""
GitLab CI Integration

Comprehensive GitLab CI connector providing pipeline management, 
triggering, status monitoring, and advanced CI/CD orchestration capabilities.
"""

import logging
import asyncio
import json
import aiohttp
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .base_connector import BaseCICDConnector, PlatformType, WorkflowStatus, UniversalWorkflowInfo, TriggerResult
from ..git_events import GitEvent, GitEventType

logger = logging.getLogger(__name__)


class GitLabPipelineStatus(Enum):
    """GitLab CI pipeline statuses"""
    CREATED = "created"
    WAITING_FOR_RESOURCE = "waiting_for_resource"
    PREPARING = "preparing"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class GitLabJobStatus(Enum):
    """GitLab CI job statuses"""
    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    SUCCESS = "success"
    CANCELED = "canceled"
    SKIPPED = "skipped"
    MANUAL = "manual"


@dataclass
class GitLabPipelineInfo:
    """GitLab pipeline information"""
    id: int
    project_id: int
    status: GitLabPipelineStatus
    ref: str
    sha: str
    before_sha: str
    tag: bool
    yaml_errors: Optional[str]
    user: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    committed_at: datetime
    duration: Optional[int]
    queued_duration: Optional[int]
    coverage: Optional[str]
    web_url: str


@dataclass
class GitLabJobInfo:
    """GitLab job information"""
    id: int
    status: GitLabJobStatus
    stage: str
    name: str
    ref: str
    tag: bool
    coverage: Optional[str]
    allow_failure: bool
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration: Optional[float]
    queued_duration: Optional[float]
    web_url: str
    commit: Dict[str, Any]
    pipeline: Dict[str, Any]


@dataclass
class GitLabProjectInfo:
    """GitLab project information"""
    id: int
    name: str
    path: str
    path_with_namespace: str
    web_url: str
    default_branch: str
    visibility: str
    archived: bool
    issues_enabled: bool
    merge_requests_enabled: bool
    wiki_enabled: bool
    jobs_enabled: bool
    snippets_enabled: bool
    container_registry_enabled: bool


class GitLabCIConnector(BaseCICDConnector):
    """GitLab CI integration connector"""
    
    def __init__(self, gitlab_token: str, gitlab_url: str = "https://gitlab.com", webhook_token: Optional[str] = None):
        """Initialize GitLab CI connector"""
        super().__init__("gitlab_ci")
        
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url.rstrip('/')
        self.webhook_token = webhook_token
        self.api_url = f"{self.gitlab_url}/api/v4"
        
        # Session for HTTP requests
        self.session = None
        
        # Cache and state management
        self.pipeline_cache: Dict[str, Dict[int, GitLabPipelineInfo]] = {}
        self.job_cache: Dict[str, Dict[int, GitLabJobInfo]] = {}
        self.project_cache: Dict[str, GitLabProjectInfo] = {}
        self.status_callbacks: List[Callable] = []
        
        # Rate limiting and performance
        self.rate_limit_remaining = 2000
        self.rate_limit_reset = datetime.now()
        self.last_rate_limit_check = datetime.now()
        
        self.logger = logging.getLogger(__name__)
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if self.session is None:
            headers = {
                "Private-Token": self.gitlab_token,
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def _close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def add_status_callback(self, callback: Callable[[GitLabPipelineInfo], None]):
        """Add a callback for pipeline status updates"""
        self.status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable):
        """Remove a status callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    async def _check_rate_limit(self):
        """Check and handle GitLab API rate limits"""
        try:
            # GitLab has different rate limits than GitHub
            # Check every 10 minutes
            if (datetime.now() - self.last_rate_limit_check).total_seconds() < 600:
                return
            
            await self._ensure_session()
            async with self.session.get(f"{self.api_url}/user") as response:
                if response.status == 429:
                    self.logger.warning("GitLab API rate limit exceeded")
                    # Handle rate limiting
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await asyncio.sleep(retry_after)
                
                self.last_rate_limit_check = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error checking GitLab rate limit: {e}")
    
    async def get_project_by_path(self, project_path: str) -> Optional[GitLabProjectInfo]:
        """Get project information by path"""
        try:
            await self._ensure_session()
            encoded_path = project_path.replace('/', '%2F')
            
            async with self.session.get(f"{self.api_url}/projects/{encoded_path}") as response:
                if response.status == 200:
                    data = await response.json()
                    project_info = GitLabProjectInfo(
                        id=data['id'],
                        name=data['name'],
                        path=data['path'],
                        path_with_namespace=data['path_with_namespace'],
                        web_url=data['web_url'],
                        default_branch=data['default_branch'],
                        visibility=data['visibility'],
                        archived=data['archived'],
                        issues_enabled=data['issues_enabled'],
                        merge_requests_enabled=data['merge_requests_enabled'],
                        wiki_enabled=data['wiki_enabled'],
                        jobs_enabled=data['jobs_enabled'],
                        snippets_enabled=data['snippets_enabled'],
                        container_registry_enabled=data['container_registry_enabled']
                    )
                    
                    # Cache the project
                    self.project_cache[project_path] = project_info
                    return project_info
                else:
                    self.logger.error(f"Failed to get project {project_path}: {response.status}")
                    return None
        
        except Exception as e:
            self.logger.error(f"Error getting project {project_path}: {e}")
            return None
    
    async def discover_workflows(self, repository: str, **kwargs) -> List[UniversalWorkflowInfo]:
        """Discover pipelines in a GitLab project"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return []
            
            await self._ensure_session()
            pipelines = []
            
            # Get recent pipelines
            async with self.session.get(
                f"{self.api_url}/projects/{project.id}/pipelines",
                params={"per_page": 20, "order_by": "updated_at", "sort": "desc"}
            ) as response:
                
                if response.status == 200:
                    pipeline_data = await response.json()
                    
                    for pipeline in pipeline_data:
                        workflow_info = UniversalWorkflowInfo(
                            id=str(pipeline['id']),
                            name=f"Pipeline #{pipeline['id']}",
                            platform=PlatformType.GITLAB_CI,
                            status=self._map_gitlab_status_to_universal(pipeline['status']),
                            repository=repository,
                            branch=pipeline['ref'],
                            commit_sha=pipeline['sha'],
                            url=pipeline['web_url'],
                            created_at=pipeline['created_at'],
                            updated_at=pipeline['updated_at'],
                            metadata={
                                'project_id': project.id,
                                'before_sha': pipeline.get('before_sha'),
                                'tag': pipeline.get('tag', False),
                                'source': pipeline.get('source', 'unknown'),
                                'yaml_errors': pipeline.get('yaml_errors'),
                                'duration': pipeline.get('duration'),
                                'queued_duration': pipeline.get('queued_duration'),
                                'coverage': pipeline.get('coverage')
                            }
                        )
                        pipelines.append(workflow_info)
                
                return pipelines
        
        except Exception as e:
            self.logger.error(f"Error discovering workflows for {repository}: {e}")
            return []
    
    async def trigger_workflow(self, repository: str, workflow_id: Union[int, str], 
                              branch: str = "main", inputs: Optional[Dict[str, Any]] = None) -> TriggerResult:
        """Trigger a GitLab pipeline"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return TriggerResult(
                    success=False,
                    error=f"Project {repository} not found"
                )
            
            await self._ensure_session()
            
            # Prepare trigger data
            trigger_data = {
                "ref": branch
            }
            
            # Add variables if provided
            if inputs:
                variables = []
                for key, value in inputs.items():
                    variables.append({
                        "key": key,
                        "value": str(value)
                    })
                trigger_data["variables"] = variables
            
            # Trigger pipeline
            async with self.session.post(
                f"{self.api_url}/projects/{project.id}/pipeline",
                json=trigger_data
            ) as response:
                
                if response.status == 201:
                    pipeline_data = await response.json()
                    
                    return TriggerResult(
                        success=True,
                        workflow_id=str(pipeline_data['id']),
                        run_id=str(pipeline_data['id']),
                        url=pipeline_data['web_url'],
                        metadata={
                            'project_id': project.id,
                            'sha': pipeline_data['sha'],
                            'ref': pipeline_data['ref'],
                            'status': pipeline_data['status']
                        }
                    )
                else:
                    error_text = await response.text()
                    return TriggerResult(
                        success=False,
                        error=f"Failed to trigger pipeline: {response.status} - {error_text}"
                    )
        
        except Exception as e:
            self.logger.error(f"Error triggering workflow {workflow_id} for {repository}: {e}")
            return TriggerResult(
                success=False,
                error=str(e)
            )
    
    async def get_workflow_status(self, repository: str, workflow_id: Union[int, str], 
                                run_id: Optional[Union[int, str]] = None) -> UniversalWorkflowInfo:
        """Get GitLab pipeline status"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                raise ValueError(f"Project {repository} not found")
            
            await self._ensure_session()
            
            # Get pipeline details
            async with self.session.get(
                f"{self.api_url}/projects/{project.id}/pipelines/{workflow_id}"
            ) as response:
                
                if response.status == 200:
                    pipeline_data = await response.json()
                    
                    return UniversalWorkflowInfo(
                        id=str(pipeline_data['id']),
                        name=f"Pipeline #{pipeline_data['id']}",
                        platform=PlatformType.GITLAB_CI,
                        status=self._map_gitlab_status_to_universal(pipeline_data['status']),
                        repository=repository,
                        branch=pipeline_data['ref'],
                        commit_sha=pipeline_data['sha'],
                        url=pipeline_data['web_url'],
                        created_at=pipeline_data['created_at'],
                        updated_at=pipeline_data['updated_at'],
                        metadata={
                            'project_id': project.id,
                            'before_sha': pipeline_data.get('before_sha'),
                            'tag': pipeline_data.get('tag', False),
                            'source': pipeline_data.get('source', 'unknown'),
                            'yaml_errors': pipeline_data.get('yaml_errors'),
                            'duration': pipeline_data.get('duration'),
                            'queued_duration': pipeline_data.get('queued_duration'),
                            'coverage': pipeline_data.get('coverage'),
                            'started_at': pipeline_data.get('started_at'),
                            'finished_at': pipeline_data.get('finished_at')
                        }
                    )
                else:
                    raise ValueError(f"Pipeline {workflow_id} not found: {response.status}")
        
        except Exception as e:
            self.logger.error(f"Error getting workflow status for {workflow_id}: {e}")
            raise
    
    async def cancel_workflow(self, repository: str, run_id: Union[int, str]) -> bool:
        """Cancel a GitLab pipeline"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return False
            
            await self._ensure_session()
            
            # Cancel pipeline
            async with self.session.post(
                f"{self.api_url}/projects/{project.id}/pipelines/{run_id}/cancel"
            ) as response:
                
                return response.status in [200, 201]
        
        except Exception as e:
            self.logger.error(f"Error canceling workflow {run_id} for {repository}: {e}")
            return False
    
    async def get_connector_status(self) -> Dict[str, Any]:
        """Get GitLab CI connector status and health information"""
        try:
            start_time = datetime.now()
            await self._ensure_session()
            
            # Test API connectivity
            async with self.session.get(f"{self.api_url}/user") as response:
                response_time = (datetime.now() - start_time).total_seconds()
                
                if response.status == 200:
                    user_data = await response.json()
                    return {
                        "status": "healthy",
                        "platform": "GitLab CI",
                        "connected": True,
                        "gitlab_url": self.gitlab_url,
                        "api_url": self.api_url,
                        "user": user_data.get('name', 'Unknown'),
                        "response_time": response_time,
                        "rate_limit_remaining": self.rate_limit_remaining
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "platform": "GitLab CI",
                        "connected": False,
                        "error": f"API returned status {response.status}",
                        "response_time": response_time
                    }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "platform": "GitLab CI",
                "connected": False,
                "error": str(e)
            }
    
    async def get_pipeline_jobs(self, repository: str, pipeline_id: Union[int, str]) -> List[GitLabJobInfo]:
        """Get jobs for a specific pipeline"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return []
            
            await self._ensure_session()
            jobs = []
            
            async with self.session.get(
                f"{self.api_url}/projects/{project.id}/pipelines/{pipeline_id}/jobs"
            ) as response:
                
                if response.status == 200:
                    jobs_data = await response.json()
                    
                    for job_data in jobs_data:
                        job_info = GitLabJobInfo(
                            id=job_data['id'],
                            status=GitLabJobStatus(job_data['status']),
                            stage=job_data['stage'],
                            name=job_data['name'],
                            ref=job_data['ref'],
                            tag=job_data['tag'],
                            coverage=job_data.get('coverage'),
                            allow_failure=job_data['allow_failure'],
                            created_at=datetime.fromisoformat(job_data['created_at'].replace('Z', '+00:00')),
                            started_at=datetime.fromisoformat(job_data['started_at'].replace('Z', '+00:00')) if job_data.get('started_at') else None,
                            finished_at=datetime.fromisoformat(job_data['finished_at'].replace('Z', '+00:00')) if job_data.get('finished_at') else None,
                            duration=job_data.get('duration'),
                            queued_duration=job_data.get('queued_duration'),
                            web_url=job_data['web_url'],
                            commit=job_data['commit'],
                            pipeline=job_data['pipeline']
                        )
                        jobs.append(job_info)
                
                return jobs
        
        except Exception as e:
            self.logger.error(f"Error getting pipeline jobs for {pipeline_id}: {e}")
            return []
    
    async def get_job_logs(self, repository: str, job_id: Union[int, str]) -> str:
        """Get logs for a specific job"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return ""
            
            await self._ensure_session()
            
            async with self.session.get(
                f"{self.api_url}/projects/{project.id}/jobs/{job_id}/trace"
            ) as response:
                
                if response.status == 200:
                    return await response.text()
                else:
                    return f"Failed to get logs for job {job_id}: {response.status}"
        
        except Exception as e:
            self.logger.error(f"Error getting job logs for {job_id}: {e}")
            return f"Error getting logs: {str(e)}"
    
    def _map_gitlab_status_to_universal(self, gitlab_status: str) -> WorkflowStatus:
        """Map GitLab pipeline status to universal workflow status"""
        status_mapping = {
            'created': WorkflowStatus.QUEUED,
            'waiting_for_resource': WorkflowStatus.QUEUED,
            'preparing': WorkflowStatus.QUEUED,
            'pending': WorkflowStatus.QUEUED,
            'running': WorkflowStatus.RUNNING,
            'success': WorkflowStatus.SUCCESS,
            'failed': WorkflowStatus.FAILED,
            'canceled': WorkflowStatus.CANCELLED,
            'cancelled': WorkflowStatus.CANCELLED,
            'skipped': WorkflowStatus.SKIPPED,
            'manual': WorkflowStatus.QUEUED,
            'scheduled': WorkflowStatus.QUEUED
        }
        
        return status_mapping.get(gitlab_status, WorkflowStatus.UNKNOWN)
    
    async def setup_webhook(self, repository: str, webhook_url: str, events: List[str] = None) -> bool:
        """Setup GitLab webhook for pipeline events"""
        try:
            await self._check_rate_limit()
            project = await self.get_project_by_path(repository)
            
            if not project:
                return False
            
            if events is None:
                events = ['pipeline_events', 'job_events']
            
            await self._ensure_session()
            
            webhook_data = {
                "url": webhook_url,
                "pipeline_events": "pipeline_events" in events,
                "job_events": "job_events" in events,
                "push_events": "push_events" in events,
                "merge_requests_events": "merge_requests_events" in events,
                "enable_ssl_verification": True
            }
            
            if self.webhook_token:
                webhook_data["token"] = self.webhook_token
            
            async with self.session.post(
                f"{self.api_url}/projects/{project.id}/hooks",
                json=webhook_data
            ) as response:
                
                return response.status == 201
        
        except Exception as e:
            self.logger.error(f"Error setting up webhook for {repository}: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()


class GitLabCIQualityGateIntegration:
    """GitLab CI Quality Gate Integration"""
    
    def __init__(self, connector: GitLabCIConnector):
        self.connector = connector
        self.logger = logging.getLogger(__name__)
    
    async def create_quality_gate_pipeline(self, repository: str, branch: str = "main") -> bool:
        """Create a quality gate pipeline configuration"""
        try:
            # This would create a .gitlab-ci.yml with quality gates
            gitlab_ci_config = {
                "stages": ["quality", "test", "build", "deploy"],
                "kirolinter_quality": {
                    "stage": "quality",
                    "image": "python:3.9",
                    "script": [
                        "pip install kirolinter",
                        "kirolinter --format json --output quality_report.json .",
                        "python -c \"import json; report=json.load(open('quality_report.json')); exit(1 if len(report.get('issues', [])) > 0 else 0)\""
                    ],
                    "artifacts": {
                        "reports": {
                            "junit": "quality_report.json"
                        },
                        "paths": ["quality_report.json"],
                        "expire_in": "1 week"
                    },
                    "only": ["merge_requests", "main"]
                }
            }
            
            # In a real implementation, this would commit the .gitlab-ci.yml file
            self.logger.info(f"Quality gate pipeline configuration prepared for {repository}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating quality gate pipeline: {e}")
            return False
    
    async def check_quality_gate(self, repository: str, pipeline_id: Union[int, str]) -> Dict[str, Any]:
        """Check if pipeline passes quality gates"""
        try:
            jobs = await self.connector.get_pipeline_jobs(repository, pipeline_id)
            quality_jobs = [job for job in jobs if 'quality' in job.name.lower() or 'kirolinter' in job.name.lower()]
            
            if not quality_jobs:
                return {
                    "passed": False,
                    "reason": "No quality gate jobs found",
                    "jobs_checked": 0
                }
            
            passed_jobs = [job for job in quality_jobs if job.status == GitLabJobStatus.SUCCESS]
            
            return {
                "passed": len(passed_jobs) == len(quality_jobs),
                "total_jobs": len(quality_jobs),
                "passed_jobs": len(passed_jobs),
                "failed_jobs": len(quality_jobs) - len(passed_jobs),
                "jobs": [
                    {
                        "name": job.name,
                        "status": job.status.value,
                        "duration": job.duration,
                        "url": job.web_url
                    }
                    for job in quality_jobs
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error checking quality gate for pipeline {pipeline_id}: {e}")
            return {
                "passed": False,
                "reason": f"Error checking quality gate: {str(e)}",
                "jobs_checked": 0
            }