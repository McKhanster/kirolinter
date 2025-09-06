"""
Execution Manager

Manages workflow execution resources, scheduling, and coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..models.workflow import WorkflowDefinition, WorkflowResult, WorkflowStatus

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of execution resources"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    CONCURRENT_EXECUTIONS = "concurrent_executions"


@dataclass
class ResourceRequirement:
    """Resource requirement specification"""
    resource_type: ResourceType
    amount: float
    unit: str
    priority: int = 1  # 1=low, 2=medium, 3=high


@dataclass
class ResourceAllocation:
    """Resource allocation tracking"""
    execution_id: str
    workflow_id: str
    allocated_resources: Dict[ResourceType, float] = field(default_factory=dict)
    allocated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ExecutionManager:
    """Manages workflow execution resources and scheduling"""
    
    def __init__(self, max_concurrent_workflows: int = 10):
        """
        Initialize execution manager
        
        Args:
            max_concurrent_workflows: Maximum number of concurrent workflow executions
        """
        self.max_concurrent_workflows = max_concurrent_workflows
        
        # Resource tracking
        self.total_resources = {
            ResourceType.CPU: 8.0,  # CPU cores
            ResourceType.MEMORY: 16.0,  # GB
            ResourceType.NETWORK: 1000.0,  # Mbps
            ResourceType.STORAGE: 100.0,  # GB
            ResourceType.CONCURRENT_EXECUTIONS: float(max_concurrent_workflows)
        }
        
        self.allocated_resources: Dict[str, ResourceAllocation] = {}
        self.execution_queue: List[str] = []
        self.resource_lock = asyncio.Lock()
    
    async def can_execute_workflow(self, workflow: WorkflowDefinition,
                                 execution_id: str) -> bool:
        """
        Check if workflow can be executed with current resource availability
        
        Args:
            workflow: Workflow definition
            execution_id: Execution identifier
            
        Returns:
            bool: True if workflow can be executed
        """
        async with self.resource_lock:
            required_resources = self._calculate_resource_requirements(workflow)
            available_resources = self._get_available_resources()
            
            # Check if we have enough resources
            for resource_type, required_amount in required_resources.items():
                if available_resources.get(resource_type, 0) < required_amount:
                    logger.debug(f"Insufficient {resource_type}: need {required_amount}, "
                               f"available {available_resources.get(resource_type, 0)}")
                    return False
            
            return True
    
    async def allocate_resources(self, workflow: WorkflowDefinition,
                               execution_id: str) -> bool:
        """
        Allocate resources for workflow execution
        
        Args:
            workflow: Workflow definition
            execution_id: Execution identifier
            
        Returns:
            bool: True if resources allocated successfully
        """
        async with self.resource_lock:
            if not await self.can_execute_workflow(workflow, execution_id):
                return False
            
            required_resources = self._calculate_resource_requirements(workflow)
            
            # Create allocation
            allocation = ResourceAllocation(
                execution_id=execution_id,
                workflow_id=workflow.id,
                allocated_resources=required_resources,
                expires_at=datetime.utcnow() + timedelta(hours=2)  # 2-hour timeout
            )
            
            self.allocated_resources[execution_id] = allocation
            
            logger.info(f"Resources allocated for execution {execution_id}: {required_resources}")
            return True
    
    async def release_resources(self, execution_id: str):
        """
        Release resources for completed workflow
        
        Args:
            execution_id: Execution identifier
        """
        async with self.resource_lock:
            if execution_id in self.allocated_resources:
                allocation = self.allocated_resources[execution_id]
                logger.info(f"Releasing resources for execution {execution_id}: "
                          f"{allocation.allocated_resources}")
                del self.allocated_resources[execution_id]
            
            # Remove from queue if present
            if execution_id in self.execution_queue:
                self.execution_queue.remove(execution_id)
    
    async def queue_workflow(self, workflow: WorkflowDefinition, execution_id: str) -> int:
        """
        Queue workflow for execution when resources become available
        
        Args:
            workflow: Workflow definition
            execution_id: Execution identifier
            
        Returns:
            int: Position in queue (0-based)
        """
        async with self.resource_lock:
            if execution_id not in self.execution_queue:
                self.execution_queue.append(execution_id)
            
            position = self.execution_queue.index(execution_id)
            logger.info(f"Workflow {workflow.id} queued at position {position}")
            return position
    
    async def get_next_executable_workflow(self) -> Optional[str]:
        """
        Get next workflow from queue that can be executed
        
        Returns:
            Optional[str]: Execution ID of next executable workflow
        """
        async with self.resource_lock:
            for execution_id in self.execution_queue[:]:
                # Check if this workflow can now be executed
                # Note: We'd need the workflow definition here, which would require
                # storing it or looking it up. For now, we'll return the first queued item.
                return execution_id
            
            return None
    
    async def cleanup_expired_allocations(self):
        """Clean up expired resource allocations"""
        async with self.resource_lock:
            now = datetime.utcnow()
            expired_executions = []
            
            for execution_id, allocation in self.allocated_resources.items():
                if allocation.expires_at and allocation.expires_at < now:
                    expired_executions.append(execution_id)
            
            for execution_id in expired_executions:
                logger.warning(f"Cleaning up expired allocation for execution {execution_id}")
                await self.release_resources(execution_id)
    
    def get_resource_utilization(self) -> Dict[ResourceType, Dict[str, float]]:
        """
        Get current resource utilization
        
        Returns:
            Dict mapping resource types to utilization info
        """
        utilization = {}
        
        for resource_type in ResourceType:
            total = self.total_resources.get(resource_type, 0)
            allocated = sum(
                allocation.allocated_resources.get(resource_type, 0)
                for allocation in self.allocated_resources.values()
            )
            available = total - allocated
            utilization_pct = (allocated / total * 100) if total > 0 else 0
            
            utilization[resource_type] = {
                "total": total,
                "allocated": allocated,
                "available": available,
                "utilization_percent": utilization_pct
            }
        
        return utilization
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics
        
        Returns:
            Dict containing execution statistics
        """
        return {
            "active_executions": len(self.allocated_resources),
            "queued_executions": len(self.execution_queue),
            "max_concurrent_workflows": self.max_concurrent_workflows,
            "resource_utilization": self.get_resource_utilization()
        }
    
    def _calculate_resource_requirements(self, workflow: WorkflowDefinition) -> Dict[ResourceType, float]:
        """Calculate resource requirements for workflow"""
        requirements = {
            ResourceType.CONCURRENT_EXECUTIONS: 1.0,  # Always need one execution slot
            ResourceType.CPU: 1.0,  # Default CPU requirement
            ResourceType.MEMORY: 1.0,  # Default memory requirement (GB)
        }
        
        # Adjust based on workflow complexity
        stage_count = len(workflow.stages)
        if stage_count > 5:
            requirements[ResourceType.CPU] = 2.0
            requirements[ResourceType.MEMORY] = 2.0
        elif stage_count > 10:
            requirements[ResourceType.CPU] = 4.0
            requirements[ResourceType.MEMORY] = 4.0
        
        # Adjust based on stage types
        for stage in workflow.stages:
            if stage.type.value in ["build", "test"]:
                requirements[ResourceType.CPU] += 0.5
                requirements[ResourceType.MEMORY] += 0.5
            elif stage.type.value in ["security_scan", "analysis"]:
                requirements[ResourceType.CPU] += 0.25
                requirements[ResourceType.MEMORY] += 0.25
        
        return requirements
    
    def _get_available_resources(self) -> Dict[ResourceType, float]:
        """Get currently available resources"""
        available = {}
        
        for resource_type, total in self.total_resources.items():
            allocated = sum(
                allocation.allocated_resources.get(resource_type, 0)
                for allocation in self.allocated_resources.values()
            )
            available[resource_type] = total - allocated
        
        return available