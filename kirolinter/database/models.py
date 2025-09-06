"""Database Models

Pydantic models for database entities and API validation in the DevOps orchestration system.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, validator
from uuid import UUID, uuid4


# Enums
class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class StageStatus(str, Enum):
    """Workflow stage status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class QualityGateType(str, Enum):
    """Quality gate types"""
    PRE_COMMIT = "pre_commit"
    PRE_MERGE = "pre_merge"
    PRE_DEPLOY = "pre_deploy"
    POST_DEPLOY = "post_deploy"


class QualityGateStatus(str, Enum):
    """Quality gate execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BYPASSED = "bypassed"


class CICDPlatform(str, Enum):
    """Supported CI/CD platforms"""
    GITHUB = "github"
    GITLAB = "gitlab"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"


class PipelineStatus(str, Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeploymentStatus(str, Enum):
    """Deployment status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStrategy(str, Enum):
    """Deployment strategies"""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"


class NotificationType(str, Enum):
    """Notification types"""
    WORKFLOW = "workflow"
    ALERT = "alert"
    DIGEST = "digest"
    SYSTEM = "system"


class NotificationSeverity(str, Enum):
    """Notification severity levels"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class NotificationStatus(str, Enum):
    """Notification status"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Base Models
class BaseDBModel(BaseModel):
    """Base model for database entities"""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class TimestampedModel(BaseDBModel):
    """Model with created_at and updated_at timestamps"""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Workflow Models
class WorkflowDefinition(TimestampedModel):
    """Workflow definition model"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=50)
    definition: Dict[str, Any] = Field(...)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = Field(None, max_length=255)
    is_active: bool = Field(default=True)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Workflow name cannot be empty')
        return v.strip()
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        # Simple version validation (semantic versioning)
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning (x.y.z)')
        return v


class WorkflowExecution(BaseDBModel):
    """Workflow execution model"""
    workflow_definition_id: UUID = Field(...)
    execution_id: str = Field(..., max_length=255)
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    triggered_by: Optional[str] = Field(None, max_length=255)
    environment: str = Field(default="default", max_length=100)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('execution_id')
    @classmethod
    def validate_execution_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Execution ID cannot be empty')
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def validate_completion(cls, values):
        if isinstance(values, dict):
            status = values.get('status')
            completed_at = values.get('completed_at')
            
            if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                if not completed_at:
                    values['completed_at'] = datetime.utcnow()
        
        return values


class WorkflowStageResult(BaseDBModel):
    """Workflow stage result model"""
    workflow_execution_id: UUID = Field(...)
    stage_id: str = Field(..., max_length=255)
    stage_name: str = Field(..., max_length=255)
    stage_type: str = Field(..., max_length=100)
    status: StageStatus = Field(default=StageStatus.PENDING)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Metrics Models
class DevOpsMetric(BaseDBModel):
    """DevOps metrics model"""
    metric_type: str = Field(..., max_length=100)
    metric_name: str = Field(..., max_length=255)
    source_type: str = Field(..., max_length=100)  # ci_cd, infrastructure, application
    source_name: str = Field(..., max_length=255)  # github, aws, prometheus, etc.
    timestamp: datetime = Field(...)
    value: Optional[float] = None
    string_value: Optional[str] = None
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def validate_value(cls, values):
        if isinstance(values, dict):
            value = values.get('value')
            string_value = values.get('string_value')
            
            if value is None and string_value is None:
                raise ValueError('Either value or string_value must be provided')
        
        return values


# Quality Gate Models
class QualityGate(TimestampedModel):
    """Quality gate model"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    gate_type: QualityGateType = Field(...)
    criteria: Dict[str, Any] = Field(...)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    created_by: Optional[str] = Field(None, max_length=255)
    
    @field_validator('criteria')
    @classmethod
    def validate_criteria(cls, v):
        if not v:
            raise ValueError('Quality gate criteria cannot be empty')
        return v


class QualityGateExecution(BaseDBModel):
    """Quality gate execution model"""
    quality_gate_id: UUID = Field(...)
    workflow_execution_id: Optional[UUID] = None
    execution_context: Dict[str, Any] = Field(...)
    status: QualityGateStatus = Field(default=QualityGateStatus.PENDING)
    result: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = Field(None, ge=0, le=100)
    passed: Optional[bool] = None
    bypass_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# CI/CD Integration Models
class CICDIntegration(TimestampedModel):
    """CI/CD integration model"""
    name: str = Field(..., max_length=255)
    platform: CICDPlatform = Field(...)
    configuration: Dict[str, Any] = Field(...)
    credentials_encrypted: Optional[str] = None
    is_active: bool = Field(default=True)
    last_sync_at: Optional[datetime] = None
    sync_status: str = Field(default="pending", max_length=50)
    error_message: Optional[str] = None
    
    @field_validator('configuration')
    @classmethod
    def validate_configuration(cls, v):
        if not v:
            raise ValueError('Integration configuration cannot be empty')
        return v


class PipelineExecution(TimestampedModel):
    """Pipeline execution model"""
    cicd_integration_id: UUID = Field(...)
    external_id: str = Field(..., max_length=255)
    pipeline_name: str = Field(..., max_length=255)
    branch: Optional[str] = Field(None, max_length=255)
    commit_sha: Optional[str] = Field(None, max_length=255)
    status: PipelineStatus = Field(...)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    trigger_event: Optional[str] = Field(None, max_length=100)
    triggered_by: Optional[str] = Field(None, max_length=255)
    pipeline_data: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)


# Risk Assessment Models
class RiskAssessment(BaseDBModel):
    """Risk assessment model"""
    assessment_type: str = Field(..., max_length=100)
    target_identifier: str = Field(..., max_length=255)
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel = Field(...)
    factors: Dict[str, Any] = Field(...)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    mitigation_strategies: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    model_version: Optional[str] = Field(None, max_length=50)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('factors')
    @classmethod
    def validate_factors(cls, v):
        if not v:
            raise ValueError('Risk factors cannot be empty')
        return v


# Deployment Models
class Deployment(TimestampedModel):
    """Deployment model"""
    deployment_id: str = Field(..., max_length=255)
    application_name: str = Field(..., max_length=255)
    version: str = Field(..., max_length=255)
    environment: str = Field(..., max_length=100)
    status: DeploymentStatus = Field(default=DeploymentStatus.PENDING)
    deployment_strategy: Optional[DeploymentStrategy] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(None, ge=0)
    deployed_by: Optional[str] = Field(None, max_length=255)
    commit_sha: Optional[str] = Field(None, max_length=255)
    pipeline_execution_id: Optional[UUID] = None
    risk_assessment_id: Optional[UUID] = None
    rollback_deployment_id: Optional[UUID] = None
    deployment_data: Dict[str, Any] = Field(default_factory=dict)
    health_checks: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('deployment_id')
    @classmethod
    def validate_deployment_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Deployment ID cannot be empty')
        return v.strip()


# Notification Models
class Notification(BaseDBModel):
    """Notification model"""
    notification_type: NotificationType = Field(...)
    title: str = Field(..., max_length=500)
    content: str = Field(...)
    severity: NotificationSeverity = Field(default=NotificationSeverity.INFO)
    target_platforms: Dict[str, Any] = Field(...)
    sent_platforms: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('target_platforms')
    @classmethod
    def validate_target_platforms(cls, v):
        if not v:
            raise ValueError('Target platforms cannot be empty')
        return v


# Analytics Models
class AnalyticsAggregation(BaseDBModel):
    """Analytics aggregation model"""
    aggregation_type: str = Field(..., max_length=100)  # hourly, daily, weekly, monthly
    metric_category: str = Field(..., max_length=100)   # workflow, cicd, infrastructure, quality
    time_bucket: datetime = Field(...)
    aggregated_data: Dict[str, Any] = Field(...)
    record_count: int = Field(default=0, ge=0)
    
    @field_validator('aggregation_type')
    @classmethod
    def validate_aggregation_type(cls, v):
        valid_types = ['hourly', 'daily', 'weekly', 'monthly']
        if v not in valid_types:
            raise ValueError(f'Aggregation type must be one of: {valid_types}')
        return v


# System Configuration Models
class SystemConfiguration(TimestampedModel):
    """System configuration model"""
    config_key: str = Field(..., max_length=255)
    config_value: Dict[str, Any] = Field(...)
    description: Optional[str] = None
    is_encrypted: bool = Field(default=False)
    updated_by: Optional[str] = Field(None, max_length=255)
    
    @validator('config_key')
    def validate_config_key(cls, v):
        if not v or not v.strip():
            raise ValueError('Configuration key cannot be empty')
        return v.strip()


# Audit Log Models
class AuditLog(BaseDBModel):
    """Audit log model"""
    entity_type: str = Field(..., max_length=100)
    entity_id: UUID = Field(...)
    action: str = Field(..., max_length=100)
    actor: str = Field(..., max_length=255)
    changes: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        valid_types = ['workflow', 'quality_gate', 'integration', 'deployment', 'notification', 'configuration']
        if v not in valid_types:
            raise ValueError(f'Entity type must be one of: {valid_types}')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['create', 'update', 'delete', 'execute', 'cancel', 'retry']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of: {valid_actions}')
        return v


# API Request/Response Models
class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution"""
    workflow_definition_id: UUID
    input_data: Dict[str, Any] = Field(default_factory=dict)
    environment: str = Field(default="default")
    triggered_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution"""
    execution_id: str
    workflow_id: UUID
    status: WorkflowStatus
    message: str
    started_at: Optional[datetime] = None
    estimated_duration_seconds: Optional[float] = None


class QualityGateExecutionRequest(BaseModel):
    """Request model for quality gate execution"""
    quality_gate_id: UUID
    execution_context: Dict[str, Any]
    workflow_execution_id: Optional[UUID] = None


class MetricsQueryRequest(BaseModel):
    """Request model for metrics query"""
    metric_types: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    source_names: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dimensions: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class MetricsQueryResponse(BaseModel):
    """Response model for metrics query"""
    metrics: List[DevOpsMetric]
    total_count: int
    query_time_seconds: float
    aggregations: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    notification_type: NotificationType
    title: str = Field(..., max_length=500)
    content: str
    severity: NotificationSeverity = Field(default=NotificationSeverity.INFO)
    target_platforms: Dict[str, Any]
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckResponse(BaseModel):
    """Response model for health checks"""
    healthy: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    components: Dict[str, Dict[str, Any]]
    uptime_seconds: float


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(cls, items: List[Any], total_count: int, pagination: PaginationParams):
        total_pages = (total_count + pagination.page_size - 1) // pagination.page_size
        
        return cls(
            items=items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
        )