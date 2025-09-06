"""
Tests for Resource Manager

Comprehensive tests for resource allocation and management functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from kirolinter.devops.orchestration.resource_manager import (
    ResourceManager, ResourcePool, ResourceRequirement, ResourceAllocation,
    ResourceType
)


class TestResourceManager:
    """Test cases for ResourceManager"""
    
    @pytest.fixture
    def resource_manager(self):
        """Create a resource manager instance for testing"""
        return ResourceManager()
    
    @pytest.fixture
    def sample_requirements(self):
        """Create sample resource requirements"""
        return [
            ResourceRequirement(ResourceType.CPU, 2.0, "cores"),
            ResourceRequirement(ResourceType.MEMORY, 4.0, "GB"),
            ResourceRequirement(ResourceType.WORKER_SLOT, 1.0, "slots")
        ]
    
    def test_initialization(self, resource_manager):
        """Test resource manager initialization"""
        assert len(resource_manager.resource_pools) > 0
        assert "cpu_pool" in resource_manager.resource_pools
        assert "memory_pool" in resource_manager.resource_pools
        assert "worker_pool" in resource_manager.resource_pools
        
        # Check default pool configurations
        cpu_pool = resource_manager.resource_pools["cpu_pool"]
        assert cpu_pool.resource_type == ResourceType.CPU
        assert cpu_pool.total_capacity == 100.0
        assert cpu_pool.available_capacity == 100.0
    
    def test_add_resource_pool(self, resource_manager):
        """Test adding custom resource pools"""
        custom_pool = ResourcePool(
            resource_type=ResourceType.GPU,
            total_capacity=4.0,
            available_capacity=4.0,
            name="gpu_pool",
            unit="GPUs"
        )
        
        resource_manager.add_resource_pool(custom_pool)
        
        assert "gpu_pool" in resource_manager.resource_pools
        assert resource_manager.resource_pools["gpu_pool"].resource_type == ResourceType.GPU
    
    def test_remove_resource_pool(self, resource_manager):
        """Test removing resource pools"""
        # Add a custom pool
        custom_pool = ResourcePool(
            name="temp_pool",
            resource_type=ResourceType.CUSTOM,
            total_capacity=10.0,
            available_capacity=10.0
        )
        resource_manager.add_resource_pool(custom_pool)
        
        # Remove it
        success = resource_manager.remove_resource_pool("temp_pool")
        assert success is True
        assert "temp_pool" not in resource_manager.resource_pools
        
        # Try to remove non-existent pool
        success = resource_manager.remove_resource_pool("non_existent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_allocate_resources_success(self, resource_manager, sample_requirements):
        """Test successful resource allocation"""
        node_id = "test_node_1"
        
        result = await resource_manager.allocate_resources(node_id, sample_requirements)
        
        assert result["success"] is True
        assert "allocations" in result
        assert len(result["allocations"]) == len(sample_requirements)
        assert len(result["allocation_ids"]) == len(sample_requirements)
        
        # Verify allocations are tracked
        assert len(resource_manager.allocations) == len(sample_requirements)
    
    @pytest.mark.asyncio
    async def test_allocate_resources_insufficient(self, resource_manager):
        """Test resource allocation with insufficient resources"""
        node_id = "test_node_2"
        
        # Request more resources than available
        excessive_requirements = [
            ResourceRequirement(ResourceType.CPU, 200.0, "cores")  # More than available
        ]
        
        result = await resource_manager.allocate_resources(node_id, excessive_requirements)
        
        assert result["success"] is False
        assert "error" in result
        assert "insufficient" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_deallocate_resources(self, resource_manager, sample_requirements):
        """Test resource deallocation"""
        node_id = "test_node_3"
        
        # Allocate resources first
        allocation_result = await resource_manager.allocate_resources(node_id, sample_requirements)
        assert allocation_result["success"] is True
        
        allocation_ids = allocation_result["allocation_ids"]
        
        # Deallocate resources
        for allocation_id in allocation_ids:
            success = await resource_manager.deallocate_resources(allocation_id)
            assert success is True
        
        # Verify resources are returned to pools
        cpu_pool = resource_manager.resource_pools["cpu_pool"]
        assert cpu_pool.available_capacity == cpu_pool.total_capacity
    
    @pytest.mark.asyncio
    async def test_deallocate_node_resources(self, resource_manager, sample_requirements):
        """Test deallocating all resources for a node"""
        node_id = "test_node_4"
        
        # Allocate resources
        allocation_result = await resource_manager.allocate_resources(node_id, sample_requirements)
        assert allocation_result["success"] is True
        
        # Deallocate all resources for the node
        deallocated_count = await resource_manager.deallocate_node_resources(node_id)
        assert deallocated_count == len(sample_requirements)
        
        # Verify no active allocations for the node
        node_allocations = [
            alloc for alloc in resource_manager.allocations.values()
            if alloc.node_id == node_id
        ]
        assert len(node_allocations) == 0
    
    def test_get_resource_utilization(self, resource_manager):
        """Test resource utilization reporting"""
        utilization = resource_manager.get_resource_utilization()
        
        assert isinstance(utilization, dict)
        assert "cpu_pool" in utilization
        assert "memory_pool" in utilization
        
        cpu_util = utilization["cpu_pool"]
        assert "total_capacity" in cpu_util
        assert "available_capacity" in cpu_util
        assert "allocated_capacity" in cpu_util
        assert "utilization_percentage" in cpu_util
        assert "resource_type" in cpu_util
        assert "unit" in cpu_util
    
    def test_get_allocation_summary(self, resource_manager):
        """Test allocation summary reporting"""
        summary = resource_manager.get_allocation_summary()
        
        assert "total_active_allocations" in summary
        assert "allocations_by_type" in summary
        assert "allocations_by_node" in summary
        assert "total_historical_allocations" in summary
        
        assert isinstance(summary["allocations_by_type"], dict)
        assert isinstance(summary["allocations_by_node"], dict)
    
    @pytest.mark.asyncio
    async def test_allocation_strategies(self, resource_manager):
        """Test different allocation strategies"""
        # Test best fit strategy
        resource_manager.set_allocation_strategy("best_fit")
        assert resource_manager.allocation_strategy == "best_fit"
        
        # Test first fit strategy
        resource_manager.set_allocation_strategy("first_fit")
        assert resource_manager.allocation_strategy == "first_fit"
        
        # Test worst fit strategy
        resource_manager.set_allocation_strategy("worst_fit")
        assert resource_manager.allocation_strategy == "worst_fit"
        
        # Test invalid strategy
        success = resource_manager.set_allocation_strategy("invalid_strategy")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_resource_optimization(self, resource_manager):
        """Test resource allocation optimization"""
        optimization_result = await resource_manager.optimize_allocations()
        
        assert "optimized" in optimization_result
        assert "actions_taken" in optimization_result
        assert isinstance(optimization_result["actions_taken"], list)
    
    def test_resource_forecasting(self, resource_manager):
        """Test resource usage forecasting"""
        forecast = resource_manager.get_resource_forecast(time_horizon_minutes=60)
        
        assert "forecast_horizon_minutes" in forecast
        assert "generated_at" in forecast
        assert "pool_forecasts" in forecast
        
        pool_forecasts = forecast["pool_forecasts"]
        assert isinstance(pool_forecasts, dict)
        
        for pool_name, pool_forecast in pool_forecasts.items():
            assert "current_utilization" in pool_forecast
            assert "projected_utilization" in pool_forecast
            assert "capacity_warning" in pool_forecast
            assert "recommended_action" in pool_forecast
    
    @pytest.mark.asyncio
    async def test_resource_constraints(self, resource_manager):
        """Test resource allocation with constraints"""
        # Add a pool with specific constraints
        constrained_pool = ResourcePool(
            name="constrained_pool",
            resource_type=ResourceType.CUSTOM,
            total_capacity=10.0,
            available_capacity=10.0,
            metadata={"environment": "production", "security_level": "high"}
        )
        resource_manager.add_resource_pool(constrained_pool)
        
        # Request resources with matching constraints
        requirement_with_constraints = ResourceRequirement(
            ResourceType.CUSTOM,
            5.0,
            constraints={"environment": "production", "security_level": "high"}
        )
        
        result = await resource_manager.allocate_resources(
            "constrained_node",
            [requirement_with_constraints]
        )
        
        assert result["success"] is True
        
        # Request resources with non-matching constraints
        requirement_with_wrong_constraints = ResourceRequirement(
            ResourceType.CUSTOM,
            5.0,
            constraints={"environment": "development"}
        )
        
        result = await resource_manager.allocate_resources(
            "wrong_constrained_node",
            [requirement_with_wrong_constraints]
        )
        
        # Should fail due to constraint mismatch
        assert result["success"] is False


class TestResourcePool:
    """Test cases for ResourcePool"""
    
    @pytest.fixture
    def resource_pool(self):
        """Create a resource pool for testing"""
        return ResourcePool(
            name="test_pool",
            resource_type=ResourceType.CPU,
            total_capacity=100.0,
            available_capacity=100.0,
            unit="cores"
        )
    
    def test_can_allocate(self, resource_pool):
        """Test resource availability checking"""
        assert resource_pool.can_allocate(50.0) is True
        assert resource_pool.can_allocate(100.0) is True
        assert resource_pool.can_allocate(150.0) is False
    
    def test_allocate_resources(self, resource_pool):
        """Test resource allocation from pool"""
        initial_available = resource_pool.available_capacity
        
        success = resource_pool.allocate(25.0)
        assert success is True
        assert resource_pool.available_capacity == initial_available - 25.0
        assert resource_pool.allocated_capacity == 25.0
        
        # Try to allocate more than available
        success = resource_pool.allocate(100.0)
        assert success is False
    
    def test_deallocate_resources(self, resource_pool):
        """Test resource deallocation to pool"""
        # Allocate some resources first
        resource_pool.allocate(30.0)
        
        # Deallocate resources
        resource_pool.deallocate(15.0)
        
        assert resource_pool.available_capacity == 85.0  # 100 - 30 + 15
        assert resource_pool.allocated_capacity == 15.0  # 30 - 15
    
    def test_deallocate_more_than_allocated(self, resource_pool):
        """Test deallocating more resources than allocated"""
        resource_pool.allocate(20.0)
        
        # Try to deallocate more than allocated
        resource_pool.deallocate(30.0)
        
        # Should not exceed total capacity
        assert resource_pool.available_capacity <= resource_pool.total_capacity
        assert resource_pool.allocated_capacity >= 0


class TestResourceRequirement:
    """Test cases for ResourceRequirement"""
    
    def test_resource_requirement_creation(self):
        """Test creating resource requirements"""
        requirement = ResourceRequirement(
            ResourceType.MEMORY,
            8.0,
            unit="GB",
            priority=3,
            max_wait_time=timedelta(minutes=5),
            constraints={"zone": "us-west-1"}
        )
        
        assert requirement.resource_type == ResourceType.MEMORY
        assert requirement.amount == 8.0
        assert requirement.unit == "GB"
        assert requirement.priority == 3
        assert requirement.max_wait_time == timedelta(minutes=5)
        assert requirement.constraints["zone"] == "us-west-1"


class TestResourceAllocation:
    """Test cases for ResourceAllocation"""
    
    def test_resource_allocation_creation(self):
        """Test creating resource allocations"""
        allocation = ResourceAllocation(
            allocation_id="test_allocation_1",
            node_id="test_node",
            resource_type=ResourceType.CPU,
            amount=4.0,
            pool_name="cpu_pool",
            allocated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            metadata={"priority": "high"}
        )
        
        assert allocation.allocation_id == "test_allocation_1"
        assert allocation.node_id == "test_node"
        assert allocation.resource_type == ResourceType.CPU
        assert allocation.amount == 4.0
        assert allocation.pool_name == "cpu_pool"
        assert allocation.metadata["priority"] == "high"


@pytest.mark.asyncio
class TestResourceManagerIntegration:
    """Integration tests for ResourceManager"""
    
    @pytest.fixture
    def resource_manager(self):
        """Create resource manager for integration testing"""
        return ResourceManager()
    
    async def test_concurrent_allocations(self, resource_manager):
        """Test concurrent resource allocations"""
        requirements = [
            ResourceRequirement(ResourceType.CPU, 10.0),
            ResourceRequirement(ResourceType.MEMORY, 2.0)
        ]
        
        # Create multiple concurrent allocation requests
        tasks = []
        for i in range(5):
            task = resource_manager.allocate_resources(f"node_{i}", requirements)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Some allocations should succeed, others might fail due to resource constraints
        successful_allocations = [r for r in results if r["success"]]
        assert len(successful_allocations) > 0
        
        # Clean up allocations
        for result in successful_allocations:
            for allocation_id in result["allocation_ids"]:
                await resource_manager.deallocate_resources(allocation_id)
    
    async def test_resource_lifecycle(self, resource_manager):
        """Test complete resource lifecycle"""
        node_id = "lifecycle_test_node"
        requirements = [
            ResourceRequirement(ResourceType.CPU, 5.0),
            ResourceRequirement(ResourceType.MEMORY, 1.0)
        ]
        
        # 1. Check initial state
        initial_utilization = resource_manager.get_resource_utilization()
        initial_cpu_available = initial_utilization["cpu_pool"]["available_capacity"]
        
        # 2. Allocate resources
        allocation_result = await resource_manager.allocate_resources(node_id, requirements)
        assert allocation_result["success"] is True
        
        # 3. Verify allocation impact
        post_allocation_utilization = resource_manager.get_resource_utilization()
        post_cpu_available = post_allocation_utilization["cpu_pool"]["available_capacity"]
        assert post_cpu_available == initial_cpu_available - 5.0
        
        # 4. Check allocation summary
        summary = resource_manager.get_allocation_summary()
        assert summary["total_active_allocations"] == 2  # CPU + Memory
        
        # 5. Deallocate resources
        deallocated_count = await resource_manager.deallocate_node_resources(node_id)
        assert deallocated_count == 2
        
        # 6. Verify resources returned
        final_utilization = resource_manager.get_resource_utilization()
        final_cpu_available = final_utilization["cpu_pool"]["available_capacity"]
        assert final_cpu_available == initial_cpu_available
    
    async def test_resource_optimization_with_allocations(self, resource_manager):
        """Test resource optimization with active allocations"""
        # Create some allocations
        for i in range(3):
            requirements = [ResourceRequirement(ResourceType.CPU, 5.0)]
            await resource_manager.allocate_resources(f"opt_test_node_{i}", requirements)
        
        # Run optimization
        optimization_result = await resource_manager.optimize_allocations()
        
        assert optimization_result["optimized"] is True
        assert "actions_taken" in optimization_result
        
        # Clean up
        for i in range(3):
            await resource_manager.deallocate_node_resources(f"opt_test_node_{i}")


if __name__ == "__main__":
    pytest.main([__file__])