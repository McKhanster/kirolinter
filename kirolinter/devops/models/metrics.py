"""
Metrics Data Models

Defines data structures for DevOps analytics and metrics including
quality metrics, performance data, and analytics aggregations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(str, Enum):
    """Metric units"""
    COUNT = "count"
    PERCENTAGE = "percentage"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    BYTES = "bytes"
    REQUESTS_PER_SECOND = "requests_per_second"
    ERRORS_PER_MINUTE = "errors_per_minute"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.value, str):
            try:
                self.value = float(self.value)
            except ValueError:
                raise ValueError(f"Invalid metric value: {self.value}")


@dataclass
class QualityMetrics:
    """Code quality metrics"""
    code_coverage: float = 0.0
    test_pass_rate: float = 0.0
    bug_density: float = 0.0  # Bugs per KLOC
    technical_debt_ratio: float = 0.0
    maintainability_index: float = 0.0
    cyclomatic_complexity: float = 0.0
    duplication_percentage: float = 0.0
    security_hotspots: int = 0
    vulnerabilities: int = 0
    code_smells: int = 0
    lines_of_code: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def overall_quality_score(self) -> float:
        """Calculate overall quality score (0-100)"""
        # Weighted average of key metrics
        weights = {
            'coverage': 0.25,
            'test_pass': 0.20,
            'maintainability': 0.20,
            'security': 0.15,
            'debt': 0.10,
            'complexity': 0.10
        }
        
        # Normalize metrics to 0-100 scale
        coverage_score = min(self.code_coverage * 100, 100)
        test_score = min(self.test_pass_rate * 100, 100)
        maintainability_score = min(self.maintainability_index, 100)
        security_score = max(100 - (self.vulnerabilities * 10 + self.security_hotspots * 5), 0)
        debt_score = max(100 - (self.technical_debt_ratio * 100), 0)
        complexity_score = max(100 - (self.cyclomatic_complexity * 2), 0)
        
        return (
            coverage_score * weights['coverage'] +
            test_score * weights['test_pass'] +
            maintainability_score * weights['maintainability'] +
            security_score * weights['security'] +
            debt_score * weights['debt'] +
            complexity_score * weights['complexity']
        )


@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    availability: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_io: float = 0.0
    active_connections: int = 0
    queue_depth: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def health_score(self) -> float:
        """Calculate system health score (0-100)"""
        # Performance-based health scoring
        response_score = max(100 - (self.response_time_ms / 10), 0)  # Penalty for slow response
        error_score = max(100 - (self.error_rate * 1000), 0)  # Heavy penalty for errors
        availability_score = self.availability * 100
        resource_score = max(100 - max(self.cpu_usage, self.memory_usage), 0)
        
        return (response_score * 0.3 + error_score * 0.3 + 
                availability_score * 0.25 + resource_score * 0.15)


@dataclass
class DeploymentMetrics:
    """Deployment-related metrics"""
    deployment_frequency: float = 0.0  # Deployments per day
    lead_time_hours: float = 0.0  # Time from commit to production
    mttr_hours: float = 0.0  # Mean time to recovery
    change_failure_rate: float = 0.0  # Percentage of deployments causing failures
    deployment_success_rate: float = 0.0
    rollback_rate: float = 0.0
    time_to_restore_hours: float = 0.0
    batch_size: int = 0  # Number of changes per deployment
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def dora_score(self) -> str:
        """Calculate DORA metrics performance level"""
        # DORA metrics thresholds
        if (self.deployment_frequency >= 1 and  # Daily deployments
            self.lead_time_hours <= 24 and      # Less than 1 day lead time
            self.mttr_hours <= 1 and            # Less than 1 hour MTTR
            self.change_failure_rate <= 0.15):  # Less than 15% failure rate
            return "Elite"
        elif (self.deployment_frequency >= 0.14 and  # Weekly deployments
              self.lead_time_hours <= 168 and        # Less than 1 week lead time
              self.mttr_hours <= 24 and              # Less than 1 day MTTR
              self.change_failure_rate <= 0.20):     # Less than 20% failure rate
            return "High"
        elif (self.deployment_frequency >= 0.03 and  # Monthly deployments
              self.lead_time_hours <= 720 and        # Less than 1 month lead time
              self.mttr_hours <= 168 and             # Less than 1 week MTTR
              self.change_failure_rate <= 0.30):     # Less than 30% failure rate
            return "Medium"
        else:
            return "Low"


@dataclass
class AnalyticsData:
    """Aggregated analytics data"""
    id: str
    name: str
    description: str
    metrics: Dict[str, List[MetricValue]] = field(default_factory=dict)
    aggregations: Dict[str, Any] = field(default_factory=dict)
    time_range_start: datetime = field(default_factory=datetime.utcnow)
    time_range_end: datetime = field(default_factory=datetime.utcnow)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
    
    def add_metric(self, name: str, value: Union[int, float], 
                   labels: Dict[str, str] = None, timestamp: datetime = None):
        """Add a metric value"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        metric_value = MetricValue(
            value=value,
            timestamp=timestamp or datetime.utcnow(),
            labels=labels or {}
        )
        self.metrics[name].append(metric_value)
    
    def calculate_aggregation(self, metric_name: str, 
                            aggregation_type: str = "avg") -> Optional[float]:
        """Calculate aggregation for a metric"""
        if metric_name not in self.metrics:
            return None
        
        values = [mv.value for mv in self.metrics[metric_name]]
        if not values:
            return None
        
        if aggregation_type == "avg":
            return sum(values) / len(values)
        elif aggregation_type == "sum":
            return sum(values)
        elif aggregation_type == "min":
            return min(values)
        elif aggregation_type == "max":
            return max(values)
        elif aggregation_type == "count":
            return len(values)
        else:
            return None


@dataclass
class Alert:
    """System alert definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    condition: str  # e.g., "> 0.05", "< 95"
    threshold: float
    duration_minutes: int = 5  # Alert fires after condition is true for this duration
    notification_channels: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger based on current value"""
        if not self.enabled:
            return False
        
        if self.condition.startswith(">"):
            threshold = float(self.condition[1:].strip())
            return current_value > threshold
        elif self.condition.startswith("<"):
            threshold = float(self.condition[1:].strip())
            return current_value < threshold
        elif self.condition.startswith(">="):
            threshold = float(self.condition[2:].strip())
            return current_value >= threshold
        elif self.condition.startswith("<="):
            threshold = float(self.condition[2:].strip())
            return current_value <= threshold
        elif self.condition.startswith("=="):
            threshold = float(self.condition[2:].strip())
            return abs(current_value - threshold) < 0.001
        
        return False


# Pydantic models for API serialization
class QualityMetricsAPI(BaseModel):
    """API model for quality metrics"""
    code_coverage: float = Field(default=0.0, ge=0, le=1)
    test_pass_rate: float = Field(default=0.0, ge=0, le=1)
    bug_density: float = Field(default=0.0, ge=0)
    technical_debt_ratio: float = Field(default=0.0, ge=0, le=1)
    maintainability_index: float = Field(default=0.0, ge=0, le=100)
    cyclomatic_complexity: float = Field(default=0.0, ge=0)
    duplication_percentage: float = Field(default=0.0, ge=0, le=100)
    security_hotspots: int = Field(default=0, ge=0)
    vulnerabilities: int = Field(default=0, ge=0)
    code_smells: int = Field(default=0, ge=0)
    lines_of_code: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_quality_score: float = Field(default=0.0, ge=0, le=100)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PerformanceMetricsAPI(BaseModel):
    """API model for performance metrics"""
    response_time_ms: float = Field(default=0.0, ge=0)
    throughput_rps: float = Field(default=0.0, ge=0)
    error_rate: float = Field(default=0.0, ge=0, le=1)
    availability: float = Field(default=0.0, ge=0, le=1)
    cpu_usage: float = Field(default=0.0, ge=0, le=100)
    memory_usage: float = Field(default=0.0, ge=0, le=100)
    disk_usage: float = Field(default=0.0, ge=0, le=100)
    network_io: float = Field(default=0.0, ge=0)
    active_connections: int = Field(default=0, ge=0)
    queue_depth: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    health_score: float = Field(default=0.0, ge=0, le=100)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeploymentMetricsAPI(BaseModel):
    """API model for deployment metrics"""
    deployment_frequency: float = Field(default=0.0, ge=0)
    lead_time_hours: float = Field(default=0.0, ge=0)
    mttr_hours: float = Field(default=0.0, ge=0)
    change_failure_rate: float = Field(default=0.0, ge=0, le=1)
    deployment_success_rate: float = Field(default=0.0, ge=0, le=1)
    rollback_rate: float = Field(default=0.0, ge=0, le=1)
    time_to_restore_hours: float = Field(default=0.0, ge=0)
    batch_size: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dora_score: str = Field(default="Low")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlertAPI(BaseModel):
    """API model for alerts"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    severity: AlertSeverity
    metric_name: str = Field(..., min_length=1)
    condition: str = Field(..., pattern=r'^[><=!]+\s*\d+(\.\d+)?$')
    threshold: float
    duration_minutes: int = Field(default=5, ge=1, le=1440)
    notification_channels: List[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = Field(default=0, ge=0)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }