"""
Pipeline Data Models

Defines data structures for CI/CD pipeline integrations including
platform configurations, metrics, and integration status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class IntegrationStatus(str, Enum):
    """Pipeline integration status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"
    DISCONNECTED = "disconnected"


class PlatformType(str, Enum):
    """Supported CI/CD platforms"""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"
    GENERIC = "generic"


class PipelineEventType(str, Enum):
    """Pipeline event types"""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUEUED = "queued"
    SKIPPED = "skipped"


@dataclass
class PipelineConfig:
    """Configuration for a CI/CD pipeline integration"""
    platform: PlatformType
    repository_url: str
    branch_patterns: List[str] = field(default_factory=lambda: ["main", "develop"])
    trigger_events: List[str] = field(default_factory=lambda: ["push", "pull_request"])
    environment_variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)  # Encrypted storage
    webhook_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    authentication: Dict[str, Any] = field(default_factory=dict)
    timeout_minutes: int = 60
    retry_count: int = 3
    parallel_jobs: int = 1
    quality_gates_enabled: bool = True
    deployment_enabled: bool = False
    notification_channels: List[str] = field(default_factory=list)


@dataclass
class PipelineMetrics:
    """Metrics for pipeline performance and reliability"""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    cancelled_runs: int = 0
    average_duration_minutes: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    queue_time_minutes: float = 0.0
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    
    def update_metrics(self, duration_minutes: float, success: bool, queue_time: float = 0.0):
        """Update metrics with new run data"""
        self.total_runs += 1
        
        if success:
            self.successful_runs += 1
            self.last_success_at = datetime.utcnow()
        else:
            self.failed_runs += 1
            self.last_failure_at = datetime.utcnow()
        
        self.last_run_at = datetime.utcnow()
        
        # Update averages
        self.average_duration_minutes = (
            (self.average_duration_minutes * (self.total_runs - 1) + duration_minutes) 
            / self.total_runs
        )
        
        self.queue_time_minutes = (
            (self.queue_time_minutes * (self.total_runs - 1) + queue_time)
            / self.total_runs
        )
        
        # Update rates
        self.success_rate = self.successful_runs / self.total_runs
        self.failure_rate = self.failed_runs / self.total_runs


@dataclass
class PipelineIntegration:
    """Complete pipeline integration definition"""
    id: str
    name: str
    platform: PlatformType
    configuration: PipelineConfig
    status: IntegrationStatus = IntegrationStatus.INACTIVE
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
    
    @property
    def is_healthy(self) -> bool:
        """Check if integration is healthy"""
        return (
            self.status == IntegrationStatus.ACTIVE and
            self.error_message is None and
            (self.last_sync is None or 
             (datetime.utcnow() - self.last_sync).total_seconds() < 3600)
        )


@dataclass
class PipelineRun:
    """Individual pipeline run information"""
    id: str
    pipeline_id: str
    run_number: int
    status: PipelineEventType
    branch: str
    commit_sha: str
    commit_message: str
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    queue_time_minutes: float = 0.0
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    logs_url: Optional[str] = None
    quality_gate_results: Dict[str, Any] = field(default_factory=dict)
    deployment_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
    
    @property
    def is_success(self) -> bool:
        """Check if pipeline run was successful"""
        return self.status == PipelineEventType.COMPLETED
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline run is currently running"""
        return self.status == PipelineEventType.STARTED


@dataclass
class PipelineOptimization:
    """Pipeline optimization recommendations"""
    pipeline_id: str
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    potential_time_savings: float = 0.0
    potential_cost_savings: float = 0.0
    confidence_score: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)


# Pydantic models for API serialization
class PipelineConfigAPI(BaseModel):
    """API model for pipeline configuration"""
    platform: PlatformType
    repository_url: str = Field(..., pattern=r'^https?://.+')
    branch_patterns: List[str] = Field(default_factory=lambda: ["main", "develop"])
    trigger_events: List[str] = Field(default_factory=lambda: ["push", "pull_request"])
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    webhook_url: Optional[str] = Field(None, pattern=r'^https?://.+')
    api_endpoint: Optional[str] = Field(None, pattern=r'^https?://.+')
    timeout_minutes: int = Field(default=60, ge=1, le=480)
    retry_count: int = Field(default=3, ge=0, le=10)
    parallel_jobs: int = Field(default=1, ge=1, le=20)
    quality_gates_enabled: bool = True
    deployment_enabled: bool = False
    notification_channels: List[str] = Field(default_factory=list)


class PipelineIntegrationAPI(BaseModel):
    """API model for pipeline integration"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    platform: PlatformType
    configuration: PipelineConfigAPI
    status: IntegrationStatus = IntegrationStatus.INACTIVE
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineRunAPI(BaseModel):
    """API model for pipeline run"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline_id: str
    run_number: int = Field(..., ge=1)
    status: PipelineEventType
    branch: str = Field(..., min_length=1)
    commit_sha: str = Field(..., min_length=7, max_length=40)
    commit_message: str = Field(..., max_length=500)
    triggered_by: str = Field(..., min_length=1)
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[float] = Field(None, ge=0)
    queue_time_minutes: float = Field(default=0.0, ge=0)
    jobs: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    logs_url: Optional[str] = Field(None, pattern=r'^https?://.+')
    quality_gate_results: Dict[str, Any] = Field(default_factory=dict)
    deployment_results: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineMetricsAPI(BaseModel):
    """API model for pipeline metrics"""
    total_runs: int = Field(default=0, ge=0)
    successful_runs: int = Field(default=0, ge=0)
    failed_runs: int = Field(default=0, ge=0)
    cancelled_runs: int = Field(default=0, ge=0)
    average_duration_minutes: float = Field(default=0.0, ge=0)
    success_rate: float = Field(default=0.0, ge=0, le=1)
    failure_rate: float = Field(default=0.0, ge=0, le=1)
    queue_time_minutes: float = Field(default=0.0, ge=0)
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }