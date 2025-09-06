"""
Deployment Data Models

Defines data structures for deployment orchestration including
deployment plans, strategies, and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DeploymentStatus(str, Enum):
    """Deployment execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"
    ROLLING_BACK = "rolling_back"


class DeploymentType(str, Enum):
    """Deployment strategy types"""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    RECREATE = "recreate"
    A_B_TESTING = "a_b_testing"


class EnvironmentType(str, Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    PREVIEW = "preview"


class RollbackTrigger(str, Enum):
    """Rollback trigger conditions"""
    MANUAL = "manual"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    HEALTH_CHECK = "health_check"
    CUSTOM_METRIC = "custom_metric"


@dataclass
class DeploymentStrategy:
    """Deployment strategy configuration"""
    type: DeploymentType
    parameters: Dict[str, Any] = field(default_factory=dict)
    environments: List[str] = field(default_factory=list)
    approval_required: bool = False
    approval_timeout_minutes: int = 60
    health_checks: List[Dict[str, Any]] = field(default_factory=list)
    rollback_on_failure: bool = True
    max_unavailable: str = "25%"  # Percentage or absolute number
    max_surge: str = "25%"  # For rolling deployments
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get deployment parameter with default"""
        return self.parameters.get(key, default)


@dataclass
class RollbackStrategy:
    """Rollback strategy configuration"""
    automatic: bool = True
    conditions: List[RollbackTrigger] = field(default_factory=list)
    timeout_seconds: int = 600
    preserve_data: bool = True
    notification_channels: List[str] = field(default_factory=list)
    custom_conditions: Dict[str, Any] = field(default_factory=dict)
    
    def should_rollback(self, metrics: Dict[str, float]) -> bool:
        """Determine if rollback should be triggered based on metrics"""
        for condition in self.conditions:
            if condition == RollbackTrigger.ERROR_RATE:
                error_rate = metrics.get("error_rate", 0.0)
                threshold = self.custom_conditions.get("error_rate_threshold", 0.05)
                if error_rate > threshold:
                    return True
            elif condition == RollbackTrigger.RESPONSE_TIME:
                response_time = metrics.get("response_time_ms", 0.0)
                threshold = self.custom_conditions.get("response_time_threshold", 5000)
                if response_time > threshold:
                    return True
        return False


@dataclass
class DeploymentTarget:
    """Deployment target configuration"""
    environment: EnvironmentType
    cluster: str
    namespace: Optional[str] = None
    region: Optional[str] = None
    replicas: int = 1
    resources: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    volumes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeploymentPlan:
    """Complete deployment plan"""
    id: str
    name: str
    version: str
    application: str
    targets: List[DeploymentTarget] = field(default_factory=list)
    strategy: DeploymentStrategy = field(default_factory=lambda: DeploymentStrategy(DeploymentType.ROLLING))
    rollback_strategy: RollbackStrategy = field(default_factory=RollbackStrategy)
    dependencies: List[str] = field(default_factory=list)
    pre_deployment_tasks: List[Dict[str, Any]] = field(default_factory=list)
    post_deployment_tasks: List[Dict[str, Any]] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())


@dataclass
class DeploymentExecution:
    """Deployment execution tracking"""
    id: str
    plan_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    triggered_by: str = "system"
    current_stage: str = "initializing"
    progress_percentage: float = 0.0
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    rollback_execution_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
    
    @property
    def is_active(self) -> bool:
        """Check if deployment is currently active"""
        return self.status in [DeploymentStatus.PENDING, DeploymentStatus.RUNNING]
    
    @property
    def is_complete(self) -> bool:
        """Check if deployment is complete (success or failure)"""
        return self.status in [
            DeploymentStatus.COMPLETED, 
            DeploymentStatus.FAILED, 
            DeploymentStatus.CANCELLED,
            DeploymentStatus.ROLLED_BACK
        ]


@dataclass
class DeploymentResult:
    """Complete deployment result"""
    execution_id: str
    plan_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    targets_deployed: List[str] = field(default_factory=list)
    targets_failed: List[str] = field(default_factory=list)
    health_check_results: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    rollback_result: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    logs_url: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate deployment success rate"""
        total_targets = len(self.targets_deployed) + len(self.targets_failed)
        if total_targets == 0:
            return 0.0
        return len(self.targets_deployed) / total_targets
    
    @property
    def is_successful(self) -> bool:
        """Check if deployment was successful"""
        return (
            self.status == DeploymentStatus.COMPLETED and
            len(self.targets_failed) == 0
        )


@dataclass
class DeploymentHistory:
    """Deployment history tracking"""
    application: str
    environment: EnvironmentType
    deployments: List[DeploymentResult] = field(default_factory=list)
    total_deployments: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    rollback_count: int = 0
    average_duration_minutes: float = 0.0
    last_deployment_at: Optional[datetime] = None
    last_successful_deployment_at: Optional[datetime] = None
    
    def add_deployment(self, result: DeploymentResult):
        """Add deployment result to history"""
        self.deployments.append(result)
        self.total_deployments += 1
        
        if result.is_successful:
            self.successful_deployments += 1
            self.last_successful_deployment_at = result.completed_at
        else:
            self.failed_deployments += 1
        
        if result.status == DeploymentStatus.ROLLED_BACK:
            self.rollback_count += 1
        
        self.last_deployment_at = result.completed_at
        
        # Update average duration
        if result.duration_seconds:
            duration_minutes = result.duration_seconds / 60
            self.average_duration_minutes = (
                (self.average_duration_minutes * (self.total_deployments - 1) + duration_minutes)
                / self.total_deployments
            )
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_deployments == 0:
            return 0.0
        return self.successful_deployments / self.total_deployments


# Pydantic models for API serialization
class DeploymentStrategyAPI(BaseModel):
    """API model for deployment strategy"""
    type: DeploymentType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    environments: List[str] = Field(default_factory=list)
    approval_required: bool = False
    approval_timeout_minutes: int = Field(default=60, ge=1, le=1440)
    health_checks: List[Dict[str, Any]] = Field(default_factory=list)
    rollback_on_failure: bool = True
    max_unavailable: str = Field(default="25%")
    max_surge: str = Field(default="25%")


class RollbackStrategyAPI(BaseModel):
    """API model for rollback strategy"""
    automatic: bool = True
    conditions: List[RollbackTrigger] = Field(default_factory=list)
    timeout_seconds: int = Field(default=600, ge=60, le=3600)
    preserve_data: bool = True
    notification_channels: List[str] = Field(default_factory=list)
    custom_conditions: Dict[str, Any] = Field(default_factory=dict)


class DeploymentTargetAPI(BaseModel):
    """API model for deployment target"""
    environment: EnvironmentType
    cluster: str = Field(..., min_length=1)
    namespace: Optional[str] = None
    region: Optional[str] = None
    replicas: int = Field(default=1, ge=1, le=100)
    resources: Dict[str, Any] = Field(default_factory=dict)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    secrets: List[str] = Field(default_factory=list)
    volumes: List[Dict[str, Any]] = Field(default_factory=list)


class DeploymentPlanAPI(BaseModel):
    """API model for deployment plan"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=50)
    application: str = Field(..., min_length=1, max_length=100)
    targets: List[DeploymentTargetAPI] = Field(default_factory=list)
    strategy: DeploymentStrategyAPI = Field(default_factory=lambda: DeploymentStrategyAPI(type=DeploymentType.ROLLING))
    rollback_strategy: RollbackStrategyAPI = Field(default_factory=RollbackStrategyAPI)
    dependencies: List[str] = Field(default_factory=list)
    pre_deployment_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    post_deployment_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeploymentResultAPI(BaseModel):
    """API model for deployment result"""
    execution_id: str
    plan_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    targets_deployed: List[str] = Field(default_factory=list)
    targets_failed: List[str] = Field(default_factory=list)
    health_check_results: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    rollback_result: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    logs_url: Optional[str] = Field(None, pattern=r'^https?://.+')
    error_message: Optional[str] = None
    success_rate: float = Field(default=0.0, ge=0, le=1)
    is_successful: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }