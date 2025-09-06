"""
Workflow Graph Management

Manages workflow graph structure, dependencies, and execution order.
"""

from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging


class NodeStatus(str, Enum):
    """Node execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class WorkflowNode:
    """Represents a node in the workflow graph"""
    id: str
    name: str
    task_type: str
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    max_retries: int = 3
    status: NodeStatus = NodeStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class WorkflowGraph:
    """Manages workflow graph structure and execution order"""
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.execution_order: List[List[str]] = []
        self.logger = logging.getLogger(__name__)
    
    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.id] = node
        self.logger.debug(f"Added node {node.id} to workflow graph")
    
    def add_dependency(self, from_node_id: str, to_node_id: str) -> None:
        """Add a dependency between nodes"""
        if to_node_id not in self.nodes:
            raise ValueError(f"Target node {to_node_id} not found in graph")
        
        if from_node_id not in self.nodes:
            raise ValueError(f"Source node {from_node_id} not found in graph")
        
        if from_node_id not in self.nodes[to_node_id].dependencies:
            self.nodes[to_node_id].dependencies.append(from_node_id)
            self.logger.debug(f"Added dependency: {from_node_id} -> {to_node_id}")
    
    def validate_graph(self) -> tuple[bool, List[str]]:
        """Validate the graph for cycles and other issues"""
        errors = []
        
        # Check for circular dependencies
        if self._has_circular_dependencies():
            errors.append("Circular dependencies detected in workflow graph")
        
        # Check for missing dependencies
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep_id}")
        
        return len(errors) == 0, errors
    
    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dep_id in self.nodes[node_id].dependencies:
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def compute_execution_order(self) -> List[List[str]]:
        """Compute the execution order using topological sort"""
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                in_degree[node_id] += 1
        
        # Initialize queue with nodes that have no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        execution_order = []
        
        while queue:
            # Process all nodes at the current level (can run in parallel)
            current_level = queue[:]
            queue = []
            execution_order.append(current_level)
            
            # Update in-degrees for dependent nodes
            for node_id in current_level:
                for other_node_id, other_node in self.nodes.items():
                    if node_id in other_node.dependencies:
                        in_degree[other_node_id] -= 1
                        if in_degree[other_node_id] == 0:
                            queue.append(other_node_id)
        
        self.execution_order = execution_order
        return execution_order
    
    def get_ready_nodes(self) -> List[str]:
        """Get nodes that are ready to execute"""
        ready_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            all_deps_completed = True
            for dep_id in node.dependencies:
                if self.nodes[dep_id].status != NodeStatus.COMPLETED:
                    all_deps_completed = False
                    break
            
            if all_deps_completed:
                ready_nodes.append(node_id)
        
        return ready_nodes
    
    def update_node_status(self, node_id: str, status: NodeStatus, 
                          error_message: Optional[str] = None) -> None:
        """Update the status of a node"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in graph")
        
        node = self.nodes[node_id]
        old_status = node.status
        node.status = status
        
        if status == NodeStatus.RUNNING and old_status == NodeStatus.PENDING:
            node.started_at = datetime.utcnow()
        elif status in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.CANCELLED]:
            node.completed_at = datetime.utcnow()
        
        if error_message:
            node.error_message = error_message
        
        self.logger.info(f"Node {node_id} status changed: {old_status} -> {status}")
    
    def get_critical_path(self) -> List[str]:
        """Calculate the critical path through the workflow"""
        # Simple implementation - find the longest path
        def calculate_path_length(node_id: str, visited: Set[str]) -> int:
            if node_id in visited:
                return 0
            
            visited.add(node_id)
            max_length = 0
            
            # Find nodes that depend on this node
            for other_node_id, other_node in self.nodes.items():
                if node_id in other_node.dependencies:
                    length = calculate_path_length(other_node_id, visited.copy())
                    max_length = max(max_length, length)
            
            return max_length + 1
        
        # Find the node with the longest path
        longest_path = []
        max_length = 0
        
        for node_id in self.nodes:
            if not self.nodes[node_id].dependencies:  # Start nodes
                path_length = calculate_path_length(node_id, set())
                if path_length > max_length:
                    max_length = path_length
                    # Reconstruct the path (simplified)
                    longest_path = self._reconstruct_path(node_id)
        
        return longest_path
    
    def _reconstruct_path(self, start_node_id: str) -> List[str]:
        """Reconstruct the critical path from a starting node"""
        path = [start_node_id]
        current_node_id = start_node_id
        
        while True:
            # Find the next node in the critical path
            next_node_id = None
            for node_id, node in self.nodes.items():
                if current_node_id in node.dependencies:
                    next_node_id = node_id
                    break
            
            if next_node_id:
                path.append(next_node_id)
                current_node_id = next_node_id
            else:
                break
        
        return path
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the workflow graph"""
        total_nodes = len(self.nodes)
        status_counts = {}
        
        for status in NodeStatus:
            status_counts[status.value] = sum(
                1 for node in self.nodes.values() if node.status == status
            )
        
        # Calculate average dependencies per node
        total_deps = sum(len(node.dependencies) for node in self.nodes.values())
        avg_deps = total_deps / total_nodes if total_nodes > 0 else 0
        
        return {
            "total_nodes": total_nodes,
            "status_counts": status_counts,
            "average_dependencies_per_node": avg_deps,
            "execution_levels": len(self.execution_order),
            "max_parallel_nodes": max(len(level) for level in self.execution_order) if self.execution_order else 0
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        stats = self.get_graph_statistics()
        
        completed_nodes = [node_id for node_id, node in self.nodes.items() 
                          if node.status == NodeStatus.COMPLETED]
        failed_nodes = [node_id for node_id, node in self.nodes.items() 
                       if node.status == NodeStatus.FAILED]
        
        return {
            "total_nodes": len(self.nodes),
            "completed_nodes": len(completed_nodes),
            "failed_nodes": len(failed_nodes),
            "success_rate": len(completed_nodes) / len(self.nodes) if self.nodes else 0,
            "completion_rate": len(completed_nodes) / len(self.nodes) if self.nodes else 0,
            "failure_rate": len(failed_nodes) / len(self.nodes) if self.nodes else 0,
            "status_counts": stats["status_counts"],
            "completed_node_ids": completed_nodes,
            "failed_node_ids": failed_nodes
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary"""
        nodes_dict = {}
        for node_id, node in self.nodes.items():
            nodes_dict[node_id] = {
                "id": node.id,
                "name": node.name,
                "task_type": node.task_type,
                "dependencies": node.dependencies,
                "parameters": node.parameters,
                "resource_requirements": node.resource_requirements,
                "timeout_seconds": node.timeout_seconds,
                "max_retries": node.max_retries,
                "status": node.status.value,
                "created_at": node.created_at.isoformat(),
                "started_at": node.started_at.isoformat() if node.started_at else None,
                "completed_at": node.completed_at.isoformat() if node.completed_at else None,
                "error_message": node.error_message,
                "retry_count": node.retry_count
            }
        
        return {
            "nodes": nodes_dict,
            "execution_order": self.execution_order,
            "statistics": self.get_graph_statistics(),
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "total_nodes": len(self.nodes),
                "graph_type": "workflow_graph"
            }
        }
    
    def clone(self) -> 'WorkflowGraph':
        """Create a deep copy of the graph"""
        cloned_graph = WorkflowGraph()
        
        # Clone all nodes
        for node_id, node in self.nodes.items():
            cloned_node = WorkflowNode(
                id=node.id,
                name=node.name,
                task_type=node.task_type,
                dependencies=node.dependencies.copy(),
                parameters=node.parameters.copy(),
                resource_requirements=node.resource_requirements.copy(),
                timeout_seconds=node.timeout_seconds,
                max_retries=node.max_retries,
                status=node.status,
                created_at=node.created_at,
                started_at=node.started_at,
                completed_at=node.completed_at,
                error_message=node.error_message,
                retry_count=node.retry_count
            )
            cloned_graph.add_node(cloned_node)
        
        # Copy execution order
        cloned_graph.execution_order = [level.copy() for level in self.execution_order]
        
        return cloned_graph
    
    @classmethod
    def from_dict(cls, graph_dict: Dict[str, Any]) -> 'WorkflowGraph':
        """Create a WorkflowGraph from a dictionary"""
        graph = cls()
        
        # Restore nodes
        for node_id, node_data in graph_dict["nodes"].items():
            node = WorkflowNode(
                id=node_data["id"],
                name=node_data["name"],
                task_type=node_data["task_type"],
                dependencies=node_data["dependencies"],
                parameters=node_data["parameters"],
                resource_requirements=node_data["resource_requirements"],
                timeout_seconds=node_data["timeout_seconds"],
                max_retries=node_data["max_retries"],
                status=NodeStatus(node_data["status"]),
                created_at=datetime.fromisoformat(node_data["created_at"]),
                started_at=datetime.fromisoformat(node_data["started_at"]) if node_data["started_at"] else None,
                completed_at=datetime.fromisoformat(node_data["completed_at"]) if node_data["completed_at"] else None,
                error_message=node_data["error_message"],
                retry_count=node_data["retry_count"]
            )
            graph.add_node(node)
        
        # Restore execution order
        graph.execution_order = graph_dict["execution_order"]
        
        return graph