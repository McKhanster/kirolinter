"""Execution Context Management

Provides context management for workflow execution including state tracking,
resource allocation, and execution metadata.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import json
from pathlib import Path


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Priority(Enum):
    """Execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_io_mb: float = 0.0
    network_io_mb: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    
    def calculate_duration(self) -> float:
        """Calculate execution duration"""
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        return self.duration_seconds


@dataclass
class ResourceAllocation:
    """Resource allocation information"""
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    disk_gb: float = 0.0
    gpu_count: int = 0
    worker_slots: int = 1
    custom_resources: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "disk_gb": self.disk_gb,
            "gpu_count": self.gpu_count,
            "worker_slots": self.worker_slots,
            "custom_resources": self.custom_resources
        }


@dataclass
class ExecutionEnvironment:
    """Execution environment configuration"""
    environment_name: str = "default"
    variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    timeout_seconds: int = 3600  # 1 hour default
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    
    def get_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable"""
        return self.variables.get(key, default)
    
    def set_variable(self, key: str, value: str) -> None:
        """Set environment variable"""
        self.variables[key] = value
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret value"""
        return self.secrets.get(key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Set secret value"""
        self.secrets[key] = value


class ExecutionContext:
    """Manages execution context for workflow nodes and stages"""
    
    def __init__(self, 
                 execution_id: Optional[str] = None,
                 workflow_id: Optional[str] = None,
                 node_id: Optional[str] = None):
        """Initialize execution context"""
        self.execution_id = execution_id or str(uuid.uuid4())
        self.workflow_id = workflow_id
        self.node_id = node_id
        
        # Execution state
        self.status = ExecutionStatus.PENDING
        self.priority = Priority.NORMAL
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Execution data
        self.input_data: Dict[str, Any] = {}
        self.output_data: Dict[str, Any] = {}
        self.intermediate_data: Dict[str, Any] = {}
        self.error_data: Optional[Dict[str, Any]] = None
        
        # Configuration
        self.environment = ExecutionEnvironment()
        self.resource_allocation = ResourceAllocation()
        self.metrics = ExecutionMetrics()
        
        # Dependencies and relationships
        self.parent_execution_id: Optional[str] = None
        self.child_execution_ids: Set[str] = set()
        self.dependency_execution_ids: Set[str] = set()
        
        # Metadata and tags
        self.metadata: Dict[str, Any] = {}
        self.tags: Set[str] = set()
        self.labels: Dict[str, str] = {}
        
        # Execution history
        self.status_history: List[Dict[str, Any]] = []
        self.checkpoint_data: Dict[str, Any] = {}
        
        # Callbacks and hooks
        self.pre_execution_hooks: List[str] = []
        self.post_execution_hooks: List[str] = []
        self.error_handlers: List[str] = []
    
    def update_status(self, status: ExecutionStatus, message: Optional[str] = None) -> None:
        """Update execution status"""
        old_status = self.status
        self.status = status
        self.updated_at = datetime.utcnow()
        
        # Record status change in history
        status_change = {
            "timestamp": self.updated_at.isoformat(),
            "from_status": old_status.value,
            "to_status": status.value,
            "message": message
        }
        self.status_history.append(status_change)
        
        # Update metrics based on status
        if status == ExecutionStatus.RUNNING and not self.metrics.start_time:
            self.metrics.start_time = self.updated_at
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            if not self.metrics.end_time:
                self.metrics.end_time = self.updated_at
                self.metrics.calculate_duration()
    
    def set_input_data(self, data: Dict[str, Any]) -> None:
        """Set input data for execution"""
        self.input_data = data.copy()
        self.updated_at = datetime.utcnow()
    
    def set_output_data(self, data: Dict[str, Any]) -> None:
        """Set output data from execution"""
        self.output_data = data.copy()
        self.updated_at = datetime.utcnow()
    
    def add_intermediate_data(self, key: str, value: Any) -> None:
        """Add intermediate data during execution"""
        self.intermediate_data[key] = value
        self.updated_at = datetime.utcnow()
    
    def set_error_data(self, error_data: Dict[str, Any]) -> None:
        """Set error data when execution fails"""
        self.error_data = error_data.copy()
        self.updated_at = datetime.utcnow()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the execution"""
        self.tags.add(tag)
        self.updated_at = datetime.utcnow()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the execution"""
        self.tags.discard(tag)
        self.updated_at = datetime.utcnow()
    
    def set_label(self, key: str, value: str) -> None:
        """Set a label on the execution"""
        self.labels[key] = value
        self.updated_at = datetime.utcnow()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the execution"""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def create_checkpoint(self, checkpoint_name: str, data: Dict[str, Any]) -> None:
        """Create a checkpoint for recovery purposes"""
        self.checkpoint_data[checkpoint_name] = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data.copy(),
            "status": self.status.value
        }
        self.updated_at = datetime.utcnow()
    
    def restore_from_checkpoint(self, checkpoint_name: str) -> bool:
        """Restore execution state from a checkpoint"""
        if checkpoint_name not in self.checkpoint_data:
            return False
        
        checkpoint = self.checkpoint_data[checkpoint_name]
        self.intermediate_data.update(checkpoint["data"])
        self.updated_at = datetime.utcnow()
        
        # Add restoration to status history
        self.status_history.append({
            "timestamp": self.updated_at.isoformat(),
            "action": "checkpoint_restore",
            "checkpoint_name": checkpoint_name,
            "checkpoint_timestamp": checkpoint["timestamp"]
        })
        
        return True
    
    def add_child_execution(self, child_execution_id: str) -> None:
        """Add a child execution ID"""
        self.child_execution_ids.add(child_execution_id)
        self.updated_at = datetime.utcnow()
    
    def add_dependency(self, dependency_execution_id: str) -> None:
        """Add a dependency execution ID"""
        self.dependency_execution_ids.add(dependency_execution_id)
        self.updated_at = datetime.utcnow()
    
    def is_ready_to_execute(self, completed_executions: Set[str]) -> bool:
        """Check if all dependencies are completed"""
        return self.dependency_execution_ids.issubset(completed_executions)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution context"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_seconds": self.metrics.duration_seconds,
            "has_input_data": bool(self.input_data),
            "has_output_data": bool(self.output_data),
            "has_error": self.error_data is not None,
            "child_count": len(self.child_execution_ids),
            "dependency_count": len(self.dependency_execution_ids),
            "tag_count": len(self.tags),
            "checkpoint_count": len(self.checkpoint_data),
            "resource_allocation": self.resource_allocation.to_dict()
        }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed execution metrics"""
        return {
            "execution_id": self.execution_id,
            "metrics": {
                "start_time": self.metrics.start_time.isoformat() if self.metrics.start_time else None,
                "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
                "duration_seconds": self.metrics.duration_seconds,
                "cpu_usage_percent": self.metrics.cpu_usage_percent,
                "memory_usage_mb": self.metrics.memory_usage_mb,
                "disk_io_mb": self.metrics.disk_io_mb,
                "network_io_mb": self.metrics.network_io_mb,
                "error_count": self.metrics.error_count,
                "retry_count": self.metrics.retry_count
            },
            "resource_allocation": self.resource_allocation.to_dict(),
            "status_history": self.status_history,
            "environment": {
                "name": self.environment.environment_name,
                "timeout_seconds": self.environment.timeout_seconds,
                "max_retries": self.environment.max_retries,
                "working_directory": self.environment.working_directory
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution context to dictionary"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "intermediate_data": self.intermediate_data,
            "error_data": self.error_data,
            "environment": {
                "environment_name": self.environment.environment_name,
                "variables": self.environment.variables,
                "working_directory": self.environment.working_directory,
                "timeout_seconds": self.environment.timeout_seconds,
                "max_retries": self.environment.max_retries,
                "retry_delay_seconds": self.environment.retry_delay_seconds
            },
            "resource_allocation": self.resource_allocation.to_dict(),
            "metrics": {
                "start_time": self.metrics.start_time.isoformat() if self.metrics.start_time else None,
                "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
                "duration_seconds": self.metrics.duration_seconds,
                "cpu_usage_percent": self.metrics.cpu_usage_percent,
                "memory_usage_mb": self.metrics.memory_usage_mb,
                "disk_io_mb": self.metrics.disk_io_mb,
                "network_io_mb": self.metrics.network_io_mb,
                "error_count": self.metrics.error_count,
                "retry_count": self.metrics.retry_count
            },
            "parent_execution_id": self.parent_execution_id,
            "child_execution_ids": list(self.child_execution_ids),
            "dependency_execution_ids": list(self.dependency_execution_ids),
            "metadata": self.metadata,
            "tags": list(self.tags),
            "labels": self.labels,
            "status_history": self.status_history,
            "checkpoint_data": self.checkpoint_data,
            "pre_execution_hooks": self.pre_execution_hooks,
            "post_execution_hooks": self.post_execution_hooks,
            "error_handlers": self.error_handlers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
        """Create execution context from dictionary"""
        context = cls(
            execution_id=data["execution_id"],
            workflow_id=data.get("workflow_id"),
            node_id=data.get("node_id")
        )
        
        # Restore basic properties
        context.status = ExecutionStatus(data["status"])
        context.priority = Priority(data["priority"])
        context.created_at = datetime.fromisoformat(data["created_at"])
        context.updated_at = datetime.fromisoformat(data["updated_at"])
        
        # Restore data
        context.input_data = data.get("input_data", {})
        context.output_data = data.get("output_data", {})
        context.intermediate_data = data.get("intermediate_data", {})
        context.error_data = data.get("error_data")
        
        # Restore environment
        env_data = data.get("environment", {})
        context.environment = ExecutionEnvironment(
            environment_name=env_data.get("environment_name", "default"),
            variables=env_data.get("variables", {}),
            working_directory=env_data.get("working_directory"),
            timeout_seconds=env_data.get("timeout_seconds", 3600),
            max_retries=env_data.get("max_retries", 3),
            retry_delay_seconds=env_data.get("retry_delay_seconds", 5.0)
        )
        
        # Restore resource allocation
        resource_data = data.get("resource_allocation", {})
        context.resource_allocation = ResourceAllocation(
            cpu_cores=resource_data.get("cpu_cores", 0.0),
            memory_gb=resource_data.get("memory_gb", 0.0),
            disk_gb=resource_data.get("disk_gb", 0.0),
            gpu_count=resource_data.get("gpu_count", 0),
            worker_slots=resource_data.get("worker_slots", 1),
            custom_resources=resource_data.get("custom_resources", {})
        )
        
        # Restore metrics
        metrics_data = data.get("metrics", {})
        context.metrics = ExecutionMetrics(
            start_time=datetime.fromisoformat(metrics_data["start_time"]) if metrics_data.get("start_time") else None,
            end_time=datetime.fromisoformat(metrics_data["end_time"]) if metrics_data.get("end_time") else None,
            duration_seconds=metrics_data.get("duration_seconds", 0.0),
            cpu_usage_percent=metrics_data.get("cpu_usage_percent", 0.0),
            memory_usage_mb=metrics_data.get("memory_usage_mb", 0.0),
            disk_io_mb=metrics_data.get("disk_io_mb", 0.0),
            network_io_mb=metrics_data.get("network_io_mb", 0.0),
            error_count=metrics_data.get("error_count", 0),
            retry_count=metrics_data.get("retry_count", 0)
        )
        
        # Restore relationships
        context.parent_execution_id = data.get("parent_execution_id")
        context.child_execution_ids = set(data.get("child_execution_ids", []))
        context.dependency_execution_ids = set(data.get("dependency_execution_ids", []))
        
        # Restore metadata and tags
        context.metadata = data.get("metadata", {})
        context.tags = set(data.get("tags", []))
        context.labels = data.get("labels", {})
        
        # Restore history and checkpoints
        context.status_history = data.get("status_history", [])
        context.checkpoint_data = data.get("checkpoint_data", {})
        
        # Restore hooks
        context.pre_execution_hooks = data.get("pre_execution_hooks", [])
        context.post_execution_hooks = data.get("post_execution_hooks", [])
        context.error_handlers = data.get("error_handlers", [])
        
        return context
    
    def save_to_file(self, file_path: str) -> None:
        """Save execution context to file"""
        data = self.to_dict()
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ExecutionContext':
        """Load execution context from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ExecutionContextManager:
    """Manages multiple execution contexts"""
    
    def __init__(self):
        """Initialize execution context manager"""
        self.contexts: Dict[str, ExecutionContext] = {}
        self.workflow_contexts: Dict[str, Set[str]] = {}  # workflow_id -> execution_ids
    
    def create_context(self, 
                      workflow_id: Optional[str] = None,
                      node_id: Optional[str] = None,
                      parent_execution_id: Optional[str] = None) -> ExecutionContext:
        """Create a new execution context"""
        context = ExecutionContext(workflow_id=workflow_id, node_id=node_id)
        context.parent_execution_id = parent_execution_id
        
        self.contexts[context.execution_id] = context
        
        # Track by workflow
        if workflow_id:
            if workflow_id not in self.workflow_contexts:
                self.workflow_contexts[workflow_id] = set()
            self.workflow_contexts[workflow_id].add(context.execution_id)
        
        # Add to parent's children
        if parent_execution_id and parent_execution_id in self.contexts:
            self.contexts[parent_execution_id].add_child_execution(context.execution_id)
        
        return context
    
    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context by ID"""
        return self.contexts.get(execution_id)
    
    def get_workflow_contexts(self, workflow_id: str) -> List[ExecutionContext]:
        """Get all execution contexts for a workflow"""
        if workflow_id not in self.workflow_contexts:
            return []
        
        return [
            self.contexts[execution_id] 
            for execution_id in self.workflow_contexts[workflow_id]
            if execution_id in self.contexts
        ]
    
    def remove_context(self, execution_id: str) -> bool:
        """Remove an execution context"""
        if execution_id not in self.contexts:
            return False
        
        context = self.contexts[execution_id]
        
        # Remove from workflow tracking
        if context.workflow_id and context.workflow_id in self.workflow_contexts:
            self.workflow_contexts[context.workflow_id].discard(execution_id)
        
        # Remove from parent's children
        if context.parent_execution_id and context.parent_execution_id in self.contexts:
            parent_context = self.contexts[context.parent_execution_id]
            parent_context.child_execution_ids.discard(execution_id)
        
        del self.contexts[execution_id]
        return True
    
    def get_ready_contexts(self) -> List[ExecutionContext]:
        """Get contexts that are ready to execute"""
        completed_executions = {
            execution_id for execution_id, context in self.contexts.items()
            if context.status == ExecutionStatus.COMPLETED
        }
        
        ready_contexts = []
        for context in self.contexts.values():
            if (context.status == ExecutionStatus.PENDING and 
                context.is_ready_to_execute(completed_executions)):
                ready_contexts.append(context)
        
        # Sort by priority
        ready_contexts.sort(key=lambda c: c.priority.value, reverse=True)
        return ready_contexts
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all execution contexts"""
        status_counts = {}
        for status in ExecutionStatus:
            status_counts[status.value] = sum(
                1 for context in self.contexts.values()
                if context.status == status
            )
        
        return {
            "total_contexts": len(self.contexts),
            "workflow_count": len(self.workflow_contexts),
            "status_counts": status_counts,
            "ready_to_execute": len(self.get_ready_contexts())
        }