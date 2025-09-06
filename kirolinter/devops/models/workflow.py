"""
Workflow Data Models

Defines the core data structures for workflow orchestration including
workflow definitions, execution state, and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TriggerType(str, Enum):
    """Workflow trigger types"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    GIT_PUSH = "git_push"
    PR_CREATED = "pr_created"
    PR_UPDATED = "pr_updated"
    DEPLOYMENT = "deployment"


class StageType(str, Enum):
    """Workflow stage types"""
    ANALYSIS = "analysis"
    QUALITY_GATE = "quality_gate"
    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    ROLLBACK = "rollback"


@dataclass
class WorkflowTrigger:
    """Defines when and how a workflow should be triggered"""
    type: TriggerType
    conditions: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # Cron expression for scheduled triggers
    webhook_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStage:
    """Individual stage within a workflow"""
    id: str
    name: str
    type: StageType
    dependencies: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 3
    allow_failure: bool = False
    parallel: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())


@dataclass
class QualityGate:
    """Quality gate configuration for workflow stages"""
    id: str
    name: str
    gate_type: str  # pre_commit, pre_merge, pre_deploy, post_deploy
    criteria: Dict[str, Any] = field(default_factory=dict)
    thresholds: Dict[str, Union[int, float]] = field(default_factory=dict)
    bypass_conditions: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class DeploymentStrategy:
    """Deployment strategy configuration"""
    type: str  # blue_green, rolling, canary, recreate
    parameters: Dict[str, Any] = field(default_factory=dict)
    environments: List[str] = field(default_factory=list)
    approval_required: bool = False


@dataclass
class RollbackStrategy:
    """Rollback strategy configuration"""
    automatic: bool = True
    conditions: List[str] = field(default_factory=list)
    timeout_seconds: int = 600
    preserve_data: bool = True


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    stages: List[WorkflowStage] = field(default_factory=list)
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    quality_gates: List[QualityGate] = field(default_factory=list)
    deployment_strategy: Optional[DeploymentStrategy] = None
    rollback_strategy: Optional[RollbackStrategy] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())


@dataclass
class ExecutionContext:
    """Runtime context for workflow execution"""
    workflow_id: str
    execution_id: str
    triggered_by: str
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    environment: str = "default"
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid4())


@dataclass
class StageResult:
    """Result of a single workflow stage execution"""
    stage_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    logs: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Complete workflow execution result"""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stage_results: List[StageResult] = field(default_factory=list)
    quality_gate_results: Dict[str, Any] = field(default_factory=dict)
    deployment_result: Optional[Dict[str, Any]] = None
    rollback_result: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of completed stages"""
        if not self.stage_results:
            return 0.0
        
        successful = sum(1 for result in self.stage_results 
                        if result.status == WorkflowStatus.COMPLETED)
        return successful / len(self.stage_results)
    
    @property
    def failed_stages(self) -> List[StageResult]:
        """Get list of failed stages"""
        return [result for result in self.stage_results 
                if result.status == WorkflowStatus.FAILED]


# Pydantic models for API serialization
class WorkflowDefinitionAPI(BaseModel):
    """API model for workflow definition"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    version: str = Field(default="1.0.0")
    stages: List[Dict[str, Any]] = Field(default_factory=list)
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    quality_gates: List[Dict[str, Any]] = Field(default_factory=list)
    deployment_strategy: Optional[Dict[str, Any]] = None
    rollback_strategy: Optional[Dict[str, Any]] = None
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowExecutionRequest(BaseModel):
    """API model for workflow execution request"""
    workflow_id: str
    triggered_by: str = "manual"
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    environment: str = "default"
    variables: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResultAPI(BaseModel):
    """API model for workflow execution result"""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stage_results: List[Dict[str, Any]] = Field(default_factory=list)
    quality_gate_results: Dict[str, Any] = Field(default_factory=dict)
    deployment_result: Optional[Dict[str, Any]] = None
    rollback_result: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    success_rate: float = Field(default=0.0)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }