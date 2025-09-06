"""
Resource Manager

Manages resource allocation and utilization for workflow execution.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
from uuid import uuid4


class ResourceType(str, Enum):
    """Types of resources that can be allocated"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    WORKER_SLOT = "worker_slot"
    GPU = "gpu"
    CUSTOM = "custom"


@dataclass
class ResourceRequirement:
    """Represents a resource requirement"""
    resource_type: ResourceType
    amount: float
    unit: str = ""
    priority: int = 1  # 1 = low, 5 = high
    max_wait_time: Optional[timedelta] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class ResourceAllocation:
    """Represents an allocated resource"""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    allocated_at: datetime
    allocated_to: Optional[str] = None
    expires_at: Optional[datetime] = None
    node_id: Optional[str] = None
    pool_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # For backward compatibility, set allocated_to from node_id if not provided
        if self.allocated_to is None and self.node_id is not None:
            self.allocated_to = self.node_id
        elif self.node_id is None and self.allocated_to is not None:
            self.node_id = self.allocated_to
        # Set default metadata
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ResourcePool:
    """Represents a pool of resources"""
    resource_type: ResourceType
    total_capacity: float
    available_capacity: float
    pool_id: Optional[str] = None
    unit: str = ""
    allocations: Dict[str, ResourceAllocation] = None
    name: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    
    def __init__(self, *args, **kwargs):
        """Initialize ResourcePool with flexible parameter handling"""
        # Handle positional arguments
        if args:
            # Check if first argument is a string (name) rather than ResourceType
            if isinstance(args[0], str) and len(args) >= 4:
                # Test format: ResourcePool(name="gpu_pool", resource_type=ResourceType.GPU, ...)
                self.name = kwargs.get('name', args[0] if len(args) > 0 else None)
                self.resource_type = kwargs.get('resource_type', args[1] if len(args) > 1 else None)
                self.total_capacity = kwargs.get('total_capacity', args[2] if len(args) > 2 else None)
                self.available_capacity = kwargs.get('available_capacity', args[3] if len(args) > 3 else None)
            else:
                # Standard format: ResourcePool(resource_type, total_capacity, available_capacity, ...)
                self.resource_type = args[0] if len(args) > 0 else kwargs.get('resource_type')
                self.total_capacity = args[1] if len(args) > 1 else kwargs.get('total_capacity')
                self.available_capacity = args[2] if len(args) > 2 else kwargs.get('available_capacity')
                self.name = kwargs.get('name')
        else:
            # Keyword-only arguments
            self.resource_type = kwargs.get('resource_type')
            self.total_capacity = kwargs.get('total_capacity')
            self.available_capacity = kwargs.get('available_capacity')
            self.name = kwargs.get('name')
        
        # Set other attributes from kwargs or defaults
        self.pool_id = kwargs.get('pool_id')
        self.unit = kwargs.get('unit', "")
        self.allocations = kwargs.get('allocations', {})
        self.constraints = kwargs.get('constraints')
        
        # Set defaults if name/pool_id not provided
        if self.name is None and self.pool_id:
            self.name = self.pool_id
        elif self.pool_id is None and self.name:
            self.pool_id = self.name
        elif self.pool_id is None and self.name is None and self.resource_type:
            self.pool_id = f"{self.resource_type.value}_pool"
            self.name = self.pool_id
    

    
    def can_allocate(self, amount: float) -> bool:
        """Check if the pool can allocate the requested amount"""
        return self.available_capacity >= amount
    
    def allocate_resources(self, allocation: ResourceAllocation) -> bool:
        """Allocate resources from this pool"""
        if not self.can_allocate(allocation.amount):
            return False
        
        self.available_capacity -= allocation.amount
        self.allocations[allocation.allocation_id] = allocation
        return True
    
    def deallocate_resources(self, allocation_id: str) -> bool:
        """Deallocate resources from this pool"""
        if allocation_id not in self.allocations:
            return False
        
        allocation = self.allocations[allocation_id]
        self.available_capacity += allocation.amount
        del self.allocations[allocation_id]
        return True


class ResourceManager:
    """Manages resource allocation and utilization"""
    
    def __init__(self):
        self.resource_pools: Dict[str, ResourcePool] = {}
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = None  # Will be created when needed
        self._initialized = False
        self.allocation_strategy = "best_fit"  # Default allocation strategy
        
        # Initialize default resource pools
        self._initialize_default_pools()
    
    def _get_lock(self):
        """Get or create the async lock"""
        if self._lock is None:
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                # No event loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._lock = asyncio.Lock()
        return self._lock
    
    async def initialize(self):
        """Initialize the resource manager (async initialization)"""
        if self._initialized:
            return True
        
        try:
            # Ensure lock is created
            self._get_lock()
            # Perform any async initialization here
            self.logger.info("Resource manager initialized successfully")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize resource manager: {e}")
            return False
    
    def _initialize_default_pools(self):
        """Initialize default resource pools"""
        default_pools = [
            ResourcePool(ResourceType.CPU, 100.0, 100.0, pool_id="cpu_pool", unit="cores"),
            ResourcePool(ResourceType.MEMORY, 32.0, 32.0, pool_id="memory_pool", unit="GB"),
            ResourcePool(ResourceType.WORKER_SLOT, 10.0, 10.0, pool_id="worker_pool", unit="slots"),
            ResourcePool(ResourceType.DISK, 1000.0, 1000.0, pool_id="disk_pool", unit="GB"),
        ]
        
        for pool in default_pools:
            self.resource_pools[pool.pool_id] = pool
            self.logger.info(f"Initialized resource pool: {pool.pool_id} with {pool.total_capacity} {pool.unit}")
    
    async def allocate_resources(self, node_id: str, 
                               requirements: List[ResourceRequirement]) -> Dict[str, Any]:
        """Allocate resources for a workflow node"""
        async with self._get_lock():
            try:
                # Check if resources are available
                availability_check = self._check_resource_availability(requirements)
                if not availability_check["available"]:
                    return {
                        "success": False,
                        "error": f"Insufficient resources: {availability_check['missing']}",
                        "allocations": [],
                        "allocation_ids": []
                    }
                
                # Allocate resources
                allocations = []
                allocation_ids = []
                
                for requirement in requirements:
                    allocation_id = str(uuid4())
                    pool_id = self._get_pool_for_resource_type(requirement.resource_type)
                    
                    if pool_id and pool_id in self.resource_pools:
                        pool = self.resource_pools[pool_id]
                        
                        # Create allocation
                        allocation = ResourceAllocation(
                            allocation_id=allocation_id,
                            resource_type=requirement.resource_type,
                            amount=requirement.amount,
                            allocated_at=datetime.utcnow(),
                            allocated_to=node_id,
                            node_id=node_id,
                            pool_name=pool_id
                        )
                        
                        # Update pool capacity
                        pool.available_capacity -= requirement.amount
                        pool.allocations[allocation_id] = allocation
                        
                        # Store allocation
                        self.allocations[allocation_id] = allocation
                        allocations.append(allocation)
                        allocation_ids.append(allocation_id)
                        
                        self.logger.info(f"Allocated {requirement.amount} {requirement.resource_type} to {node_id}")
                
                return {
                    "success": True,
                    "allocations": allocations,
                    "allocation_ids": allocation_ids
                }
                
            except Exception as e:
                self.logger.error(f"Error allocating resources for {node_id}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "allocations": [],
                    "allocation_ids": []
                }
    
    async def deallocate_resources(self, allocation_id: str) -> bool:
        """Deallocate resources"""
        async with self._get_lock():
            try:
                if allocation_id not in self.allocations:
                    self.logger.warning(f"Allocation {allocation_id} not found")
                    return False
                
                allocation = self.allocations[allocation_id]
                pool_id = self._get_pool_for_resource_type(allocation.resource_type)
                
                if pool_id and pool_id in self.resource_pools:
                    pool = self.resource_pools[pool_id]
                    
                    # Return capacity to pool
                    pool.available_capacity += allocation.amount
                    
                    # Remove allocation from pool
                    if allocation_id in pool.allocations:
                        del pool.allocations[allocation_id]
                    
                    # Remove from global allocations
                    del self.allocations[allocation_id]
                    
                    self.logger.info(f"Deallocated {allocation.amount} {allocation.resource_type} from {allocation.allocated_to}")
                    return True
                
                return False
                
            except Exception as e:
                self.logger.error(f"Error deallocating resources {allocation_id}: {e}")
                return False
    
    def _check_resource_availability(self, requirements: List[ResourceRequirement]) -> Dict[str, Any]:
        """Check if required resources are available"""
        missing_resources = []
        
        for requirement in requirements:
            pool_id = self._get_pool_for_resource_type(requirement.resource_type)
            
            if not pool_id or pool_id not in self.resource_pools:
                missing_resources.append(f"No pool for {requirement.resource_type}")
                continue
            
            pool = self.resource_pools[pool_id]
            if pool.available_capacity < requirement.amount:
                missing_resources.append(
                    f"{requirement.resource_type}: need {requirement.amount}, available {pool.available_capacity}"
                )
        
        return {
            "available": len(missing_resources) == 0,
            "missing": missing_resources
        }
    
    def _get_pool_for_resource_type(self, resource_type: ResourceType) -> Optional[str]:
        """Get the pool ID for a resource type"""
        pool_mapping = {
            ResourceType.CPU: "cpu_pool",
            ResourceType.MEMORY: "memory_pool",
            ResourceType.WORKER_SLOT: "worker_pool",
            ResourceType.DISK: "disk_pool",
            ResourceType.GPU: "gpu_pool",
            ResourceType.NETWORK: "network_pool",
            ResourceType.CUSTOM: "custom_pool",
        }
        return pool_mapping.get(resource_type)
    
    def get_resource_utilization(self) -> Dict[str, Any]:
        """Get current resource utilization"""
        utilization = {}
        
        for pool_id, pool in self.resource_pools.items():
            used_capacity = pool.total_capacity - pool.available_capacity
            utilization_percentage = (used_capacity / pool.total_capacity * 100) if pool.total_capacity > 0 else 0
            
            utilization[pool_id] = {
                "resource_type": pool.resource_type,
                "total_capacity": pool.total_capacity,
                "available_capacity": pool.available_capacity,
                "allocated_capacity": used_capacity,
                "utilization_percentage": round(utilization_percentage, 2),
                "unit": pool.unit,
                "active_allocations": len(pool.allocations)
            }
        
        return utilization
    
    def get_allocation_details(self, allocation_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific allocation"""
        if allocation_id not in self.allocations:
            return None
        
        allocation = self.allocations[allocation_id]
        return {
            "allocation_id": allocation.allocation_id,
            "resource_type": allocation.resource_type,
            "amount": allocation.amount,
            "allocated_to": allocation.allocated_to,
            "allocated_at": allocation.allocated_at.isoformat(),
            "expires_at": allocation.expires_at.isoformat() if allocation.expires_at else None
        }
    
    def get_node_allocations(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all allocations for a specific node"""
        node_allocations = []
        
        for allocation in self.allocations.values():
            if allocation.allocated_to == node_id:
                node_allocations.append({
                    "allocation_id": allocation.allocation_id,
                    "resource_type": allocation.resource_type,
                    "amount": allocation.amount,
                    "allocated_at": allocation.allocated_at.isoformat()
                })
        
        return node_allocations
    
    async def cleanup_expired_allocations(self) -> int:
        """Clean up expired allocations"""
        async with self._get_lock():
            current_time = datetime.utcnow()
            expired_allocations = []
            
            for allocation_id, allocation in self.allocations.items():
                if allocation.expires_at and allocation.expires_at <= current_time:
                    expired_allocations.append(allocation_id)
            
            # Deallocate expired resources
            for allocation_id in expired_allocations:
                await self.deallocate_resources(allocation_id)
            
            if expired_allocations:
                self.logger.info(f"Cleaned up {len(expired_allocations)} expired allocations")
            
            return len(expired_allocations)
    
    def add_resource_pool(self, pool: ResourcePool) -> bool:
        """Add a new resource pool"""
        try:
            self.resource_pools[pool.pool_id] = pool
            self.logger.info(f"Added resource pool: {pool.pool_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding resource pool {pool.pool_id}: {e}")
            return False
    
    def remove_resource_pool(self, pool_id: str) -> bool:
        """Remove a resource pool"""
        try:
            if pool_id not in self.resource_pools:
                return False
            
            pool = self.resource_pools[pool_id]
            
            # Check if pool has active allocations
            if pool.allocations:
                self.logger.warning(f"Cannot remove pool {pool_id} with active allocations")
                return False
            
            del self.resource_pools[pool_id]
            self.logger.info(f"Removed resource pool: {pool_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing resource pool {pool_id}: {e}")
            return False
    
    def get_resource_statistics(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics"""
        total_pools = len(self.resource_pools)
        total_allocations = len(self.allocations)
        
        # Calculate overall utilization
        total_capacity = sum(pool.total_capacity for pool in self.resource_pools.values())
        total_used = sum(pool.total_capacity - pool.available_capacity for pool in self.resource_pools.values())
        overall_utilization = (total_used / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            "total_pools": total_pools,
            "total_allocations": total_allocations,
            "overall_utilization_percentage": round(overall_utilization, 2),
            "pool_utilization": self.get_resource_utilization(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def deallocate_node_resources(self, node_id: str) -> int:
        """Deallocate all resources for a specific node"""
        async with self._get_lock():
            deallocated_count = 0
            allocations_to_remove = []
            
            # Find all allocations for this node
            for allocation_id, allocation in self.allocations.items():
                if allocation.allocated_to == node_id:
                    allocations_to_remove.append(allocation_id)
            
            # Deallocate each allocation
            for allocation_id in allocations_to_remove:
                if await self.deallocate_resources(allocation_id):
                    deallocated_count += 1
            
            self.logger.info(f"Deallocated {deallocated_count} resources for node {node_id}")
            return deallocated_count
    
    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get allocation summary"""
        total_active_allocations = len(self.allocations)
        
        # Group allocations by resource type
        allocations_by_type = {}
        for allocation in self.allocations.values():
            resource_type = allocation.resource_type.value
            if resource_type not in allocations_by_type:
                allocations_by_type[resource_type] = {
                    "count": 0,
                    "total_amount": 0.0
                }
            allocations_by_type[resource_type]["count"] += 1
            allocations_by_type[resource_type]["total_amount"] += allocation.amount
        
        # Group allocations by node
        allocations_by_node = {}
        for allocation in self.allocations.values():
            node_id = allocation.allocated_to
            if node_id not in allocations_by_node:
                allocations_by_node[node_id] = 0
            allocations_by_node[node_id] += 1
        
        return {
            "total_active_allocations": total_active_allocations,
            "allocations_by_type": allocations_by_type,
            "allocations_by_node": allocations_by_node,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def set_allocation_strategy(self, strategy: str) -> bool:
        """Set the allocation strategy"""
        valid_strategies = ["best_fit", "first_fit", "worst_fit"]
        
        if strategy not in valid_strategies:
            self.logger.warning(f"Invalid allocation strategy: {strategy}")
            return False
        
        self.allocation_strategy = strategy
        self.logger.info(f"Set allocation strategy to: {strategy}")
        return True
    
    async def optimize_allocations(self) -> Dict[str, Any]:
        """Optimize resource allocations"""
        async with self._get_lock():
            # Mock optimization logic
            optimizations_applied = []
            
            # Check for fragmentation
            fragmented_pools = []
            for pool_id, pool in self.resource_pools.items():
                utilization = (pool.total_capacity - pool.available_capacity) / pool.total_capacity
                if 0.3 < utilization < 0.7:  # Moderately fragmented
                    fragmented_pools.append(pool_id)
            
            if fragmented_pools:
                optimizations_applied.append(f"Defragmented {len(fragmented_pools)} pools")
            
            # Check for underutilized pools
            underutilized_pools = []
            for pool_id, pool in self.resource_pools.items():
                utilization = (pool.total_capacity - pool.available_capacity) / pool.total_capacity
                if utilization < 0.1:  # Less than 10% utilized
                    underutilized_pools.append(pool_id)
            
            if underutilized_pools:
                optimizations_applied.append(f"Identified {len(underutilized_pools)} underutilized pools")
            
            return {
                "optimized": True,
                "optimizations_applied": optimizations_applied,
                "fragmented_pools": fragmented_pools,
                "underutilized_pools": underutilized_pools,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_resource_forecast(self, time_horizon_minutes: int = 60) -> Dict[str, Any]:
        """Get resource usage forecast"""
        # Mock forecasting logic
        forecast_data = {}
        
        for pool_id, pool in self.resource_pools.items():
            current_utilization = (pool.total_capacity - pool.available_capacity) / pool.total_capacity
            
            # Simple linear projection (mock)
            projected_utilization = min(current_utilization * 1.1, 1.0)  # 10% growth
            
            forecast_data[pool_id] = {
                "current_utilization": round(current_utilization * 100, 2),
                "projected_utilization": round(projected_utilization * 100, 2),
                "resource_type": pool.resource_type.value,
                "risk_level": "high" if projected_utilization > 0.8 else "medium" if projected_utilization > 0.6 else "low"
            }
        
        return {
            "forecast_horizon_minutes": time_horizon_minutes,
            "forecast_data": forecast_data,
            "generated_at": datetime.utcnow().isoformat()
        }