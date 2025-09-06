"""
Universal Pipeline Management Interface

Provides a unified interface that abstracts differences between CI/CD platforms
and provides consistent management capabilities across GitHub Actions, GitLab CI,
and other supported platforms.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from ..integrations.cicd.base_connector import (
    BaseCICDConnector, 
    UniversalWorkflowInfo, 
    TriggerResult,
    PlatformType,
    WorkflowStatus
)
from ..integrations.cicd.github_actions import GitHubActionsConnector
from ..integrations.cicd.gitlab_ci import GitLabCIConnector

logger = logging.getLogger(__name__)


class PipelineOperationStatus(Enum):
    """Status of pipeline operations"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


@dataclass
class PipelineRegistryEntry:
    """Registry entry for a pipeline"""
    pipeline_id: str
    platform: PlatformType
    repository: str
    workflow_id: Union[int, str]
    name: str
    status: WorkflowStatus
    last_run: Optional[datetime] = None
    success_rate: float = 0.0
    avg_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossPlatformOperation:
    """Represents an operation across multiple platforms"""
    operation_id: str
    operation_type: str
    platforms: List[PlatformType]
    status: PipelineOperationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)


@dataclass
class PipelineCoordinationRule:
    """Rules for coordinating pipelines across platforms"""
    rule_id: str
    name: str
    condition: str  # JSON condition
    action: str     # Action to take
    platforms: List[PlatformType]
    priority: int = 0
    enabled: bool = True


class PipelineRegistry:
    """Registry for managing pipeline information across platforms"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.pipelines: Dict[str, PipelineRegistryEntry] = {}
        self.platform_mappings: Dict[PlatformType, List[str]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def register_pipeline(self, entry: PipelineRegistryEntry) -> bool:
        """Register a pipeline in the registry"""
        try:
            self.pipelines[entry.pipeline_id] = entry
            
            # Update platform mappings
            if entry.platform not in self.platform_mappings:
                self.platform_mappings[entry.platform] = []
            
            if entry.pipeline_id not in self.platform_mappings[entry.platform]:
                self.platform_mappings[entry.platform].append(entry.pipeline_id)
            
            # Store in Redis if available
            if self.redis:
                pipeline_data = {
                    'pipeline_id': entry.pipeline_id,
                    'platform': entry.platform.value,
                    'repository': entry.repository,
                    'workflow_id': str(entry.workflow_id),
                    'name': entry.name,
                    'status': entry.status.value,
                    'last_run': entry.last_run.isoformat() if entry.last_run else None,
                    'success_rate': entry.success_rate,
                    'avg_duration': entry.avg_duration,
                    'metadata': json.dumps(entry.metadata)
                }
                await self.redis.hset(f"pipeline:{entry.pipeline_id}", mapping=pipeline_data)
                await self.redis.sadd("pipeline_registry", entry.pipeline_id)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to register pipeline {entry.pipeline_id}: {e}")
            return False
    
    async def get_pipeline(self, pipeline_id: str) -> Optional[PipelineRegistryEntry]:
        """Get pipeline by ID"""
        return self.pipelines.get(pipeline_id)
    
    async def get_pipelines_by_platform(self, platform: PlatformType) -> List[PipelineRegistryEntry]:
        """Get all pipelines for a specific platform"""
        pipeline_ids = self.platform_mappings.get(platform, [])
        return [self.pipelines[pid] for pid in pipeline_ids if pid in self.pipelines]
    
    async def get_pipelines_by_repository(self, repository: str) -> List[PipelineRegistryEntry]:
        """Get all pipelines for a specific repository"""
        return [p for p in self.pipelines.values() if p.repository == repository]
    
    async def update_pipeline_stats(self, pipeline_id: str, success_rate: float, avg_duration: float, last_run: datetime) -> bool:
        """Update pipeline statistics"""
        if pipeline_id in self.pipelines:
            pipeline = self.pipelines[pipeline_id]
            pipeline.success_rate = success_rate
            pipeline.avg_duration = avg_duration
            pipeline.last_run = last_run
            
            # Update in Redis
            if self.redis:
                await self.redis.hset(f"pipeline:{pipeline_id}", mapping={
                    'success_rate': success_rate,
                    'avg_duration': avg_duration,
                    'last_run': last_run.isoformat()
                })
            return True
        return False


class CrossPlatformCoordinator:
    """Coordinates operations across multiple CI/CD platforms"""
    
    def __init__(self, registry: PipelineRegistry):
        self.registry = registry
        self.coordination_rules: Dict[str, PipelineCoordinationRule] = {}
        self.active_operations: Dict[str, CrossPlatformOperation] = {}
        self.resource_locks: Dict[str, set] = {}  # Resource -> set of operation IDs
        self.logger = logging.getLogger(__name__)
    
    async def add_coordination_rule(self, rule: PipelineCoordinationRule) -> bool:
        """Add a coordination rule"""
        try:
            self.coordination_rules[rule.rule_id] = rule
            self.logger.info(f"Added coordination rule: {rule.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add coordination rule {rule.rule_id}: {e}")
            return False
    
    async def coordinate_cross_platform_operation(self, 
                                                operation_type: str, 
                                                platforms: List[PlatformType],
                                                repository: str,
                                                **kwargs) -> CrossPlatformOperation:
        """Coordinate an operation across multiple platforms"""
        operation_id = f"{operation_type}_{repository}_{datetime.now().timestamp()}"
        
        operation = CrossPlatformOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            platforms=platforms,
            status=PipelineOperationStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        self.active_operations[operation_id] = operation
        
        try:
            # Check for resource conflicts
            conflicts = await self._check_resource_conflicts(repository, platforms)
            if conflicts:
                operation.status = PipelineOperationStatus.FAILED
                operation.errors['resource_conflicts'] = f"Resource conflicts detected: {conflicts}"
                return operation
            
            # Reserve resources
            await self._reserve_resources(operation_id, repository, platforms)
            
            # Apply coordination rules
            await self._apply_coordination_rules(operation, repository, **kwargs)
            
            operation.status = PipelineOperationStatus.SUCCESS
            operation.completed_at = datetime.now()
            
        except Exception as e:
            operation.status = PipelineOperationStatus.FAILED
            operation.errors['coordination_error'] = str(e)
            self.logger.error(f"Cross-platform operation {operation_id} failed: {e}")
        finally:
            # Release resources
            await self._release_resources(operation_id, repository, platforms)
        
        return operation
    
    async def _check_resource_conflicts(self, repository: str, platforms: List[PlatformType]) -> List[str]:
        """Check for resource conflicts"""
        conflicts = []
        resource_key = f"repo:{repository}"
        
        for platform in platforms:
            platform_resource = f"{resource_key}:{platform.value}"
            if platform_resource in self.resource_locks and self.resource_locks[platform_resource]:
                conflicts.append(f"{platform.value} platform busy")
        
        return conflicts
    
    async def _reserve_resources(self, operation_id: str, repository: str, platforms: List[PlatformType]) -> None:
        """Reserve resources for operation"""
        resource_key = f"repo:{repository}"
        
        for platform in platforms:
            platform_resource = f"{resource_key}:{platform.value}"
            if platform_resource not in self.resource_locks:
                self.resource_locks[platform_resource] = set()
            self.resource_locks[platform_resource].add(operation_id)
    
    async def _release_resources(self, operation_id: str, repository: str, platforms: List[PlatformType]) -> None:
        """Release reserved resources"""
        resource_key = f"repo:{repository}"
        
        for platform in platforms:
            platform_resource = f"{resource_key}:{platform.value}"
            if platform_resource in self.resource_locks:
                self.resource_locks[platform_resource].discard(operation_id)
                if not self.resource_locks[platform_resource]:
                    del self.resource_locks[platform_resource]
    
    async def _apply_coordination_rules(self, operation: CrossPlatformOperation, repository: str, **kwargs) -> None:
        """Apply coordination rules to operation"""
        for rule in self.coordination_rules.values():
            if not rule.enabled:
                continue
            
            # Check if rule applies to this operation
            if not any(platform in rule.platforms for platform in operation.platforms):
                continue
            
            try:
                # Simple rule evaluation (could be enhanced with proper rule engine)
                condition_met = await self._evaluate_condition(rule.condition, operation, repository, **kwargs)
                
                if condition_met:
                    await self._execute_rule_action(rule.action, operation, repository, **kwargs)
                    self.logger.info(f"Applied coordination rule: {rule.name}")
            except Exception as e:
                self.logger.error(f"Failed to apply coordination rule {rule.rule_id}: {e}")
    
    async def _evaluate_condition(self, condition: str, operation: CrossPlatformOperation, repository: str, **kwargs) -> bool:
        """Evaluate rule condition (simplified implementation)"""
        try:
            # Parse JSON condition
            condition_data = json.loads(condition)
            
            # Simple condition evaluation
            if condition_data.get('type') == 'platform_count':
                return len(operation.platforms) >= condition_data.get('min_platforms', 1)
            
            if condition_data.get('type') == 'repository_match':
                return repository == condition_data.get('repository')
            
            return True
        except:
            return False
    
    async def _execute_rule_action(self, action: str, operation: CrossPlatformOperation, repository: str, **kwargs) -> None:
        """Execute rule action (simplified implementation)"""
        try:
            action_data = json.loads(action)
            
            if action_data.get('type') == 'delay':
                delay_seconds = action_data.get('seconds', 0)
                await asyncio.sleep(delay_seconds)
            
            if action_data.get('type') == 'log':
                message = action_data.get('message', 'Coordination rule executed')
                self.logger.info(f"Rule action: {message}")
        except:
            pass


class UniversalPipelineManager:
    """Universal interface for managing CI/CD pipelines across multiple platforms"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.connectors: Dict[PlatformType, BaseCICDConnector] = {}
        self.active_connections: Dict[PlatformType, bool] = {}
        self.pipeline_registry = PipelineRegistry(redis_client)
        self.coordinator = CrossPlatformCoordinator(self.pipeline_registry)
        self.logger = logging.getLogger(__name__)
    
    def register_connector(self, platform: PlatformType, connector: BaseCICDConnector) -> bool:
        """Register a CI/CD platform connector"""
        try:
            self.connectors[platform] = connector
            self.active_connections[platform] = False
            self.logger.info(f"Registered {platform.value} connector")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register {platform.value} connector: {e}")
            return False
    
    def register_github_connector(self, github_token: str, webhook_secret: str = None) -> bool:
        """Register GitHub Actions connector"""
        try:
            connector = GitHubActionsConnector(github_token, webhook_secret)
            return self.register_connector(PlatformType.GITHUB_ACTIONS, connector)
        except Exception as e:
            self.logger.error(f"Failed to register GitHub connector: {e}")
            return False
    
    def register_gitlab_connector(self, gitlab_token: str, gitlab_url: str = "https://gitlab.com", webhook_token: str = None) -> bool:
        """Register GitLab CI connector"""
        try:
            connector = GitLabCIConnector(gitlab_token, gitlab_url, webhook_token)
            return self.register_connector(PlatformType.GITLAB_CI, connector)
        except Exception as e:
            self.logger.error(f"Failed to register GitLab connector: {e}")
            return False
    
    async def test_connections(self) -> Dict[PlatformType, bool]:
        """Test connections to all registered platforms"""
        results = {}
        
        for platform, connector in self.connectors.items():
            try:
                health = await connector.get_connector_status()
                is_healthy = health.get('status') == 'healthy'
                results[platform] = is_healthy
                self.active_connections[platform] = is_healthy
                
                if is_healthy:
                    self.logger.info(f"{platform.value} connection: OK")
                else:
                    self.logger.warning(f"{platform.value} connection: FAILED - {health.get('error', 'Unknown error')}")
            except Exception as e:
                results[platform] = False
                self.active_connections[platform] = False
                self.logger.error(f"{platform.value} connection test failed: {e}")
        
        return results
    
    async def discover_all_workflows(self, repository: str) -> Dict[PlatformType, List[UniversalWorkflowInfo]]:
        """Discover workflows across all connected platforms"""
        results = {}
        
        for platform, connector in self.connectors.items():
            if not self.active_connections.get(platform, False):
                continue
            
            try:
                workflows = await connector.discover_workflows(repository)
                results[platform] = workflows
                
                # Register workflows in registry
                for workflow in workflows:
                    pipeline_id = f"{platform.value}:{repository}:{workflow.id}"
                    entry = PipelineRegistryEntry(
                        pipeline_id=pipeline_id,
                        platform=platform,
                        repository=repository,
                        workflow_id=workflow.id,
                        name=workflow.name,
                        status=workflow.status,
                        metadata=workflow.metadata or {}
                    )
                    await self.pipeline_registry.register_pipeline(entry)
                
                self.logger.info(f"Discovered {len(workflows)} workflows on {platform.value}")
            except Exception as e:
                self.logger.error(f"Failed to discover workflows on {platform.value}: {e}")
                results[platform] = []
        
        return results
    
    async def trigger_cross_platform_workflows(self, 
                                             repository: str, 
                                             platforms: List[PlatformType] = None,
                                             branch: str = "main",
                                             inputs: Dict[str, Any] = None) -> CrossPlatformOperation:
        """Trigger workflows across multiple platforms"""
        if platforms is None:
            platforms = [p for p, active in self.active_connections.items() if active]
        
        operation = await self.coordinator.coordinate_cross_platform_operation(
            operation_type="trigger_workflows",
            platforms=platforms,
            repository=repository,
            branch=branch,
            inputs=inputs or {}
        )
        
        # Execute triggers on each platform
        for platform in platforms:
            if platform not in self.connectors:
                continue
            
            connector = self.connectors[platform]
            
            try:
                # Get workflows for this platform
                pipelines = await self.pipeline_registry.get_pipelines_by_platform(platform)
                repo_pipelines = [p for p in pipelines if p.repository == repository]
                
                platform_results = []
                for pipeline in repo_pipelines:
                    result = await connector.trigger_workflow(
                        repository=repository,
                        workflow_id=pipeline.workflow_id,
                        branch=branch,
                        inputs=inputs
                    )
                    platform_results.append({
                        'workflow_id': pipeline.workflow_id,
                        'result': result.success,
                        'run_id': result.run_id,
                        'error': result.error
                    })
                
                operation.results[platform.value] = platform_results
                
            except Exception as e:
                operation.errors[platform.value] = str(e)
                self.logger.error(f"Failed to trigger workflows on {platform.value}: {e}")
        
        return operation
    
    async def get_unified_status(self, repository: str) -> Dict[str, Any]:
        """Get unified status across all platforms"""
        status = {
            'repository': repository,
            'platforms': {},
            'summary': {
                'total_pipelines': 0,
                'running_pipelines': 0,
                'failed_pipelines': 0,
                'success_rate': 0.0
            }
        }
        
        total_pipelines = 0
        running_count = 0
        failed_count = 0
        success_count = 0
        
        for platform, connector in self.connectors.items():
            if not self.active_connections.get(platform, False):
                continue
            
            try:
                pipelines = await self.pipeline_registry.get_pipelines_by_repository(repository)
                platform_pipelines = [p for p in pipelines if p.platform == platform]
                
                platform_status = {
                    'connected': True,
                    'pipelines': len(platform_pipelines),
                    'running': 0,
                    'failed': 0,
                    'success': 0
                }
                
                for pipeline in platform_pipelines:
                    total_pipelines += 1
                    
                    if pipeline.status == WorkflowStatus.RUNNING:
                        running_count += 1
                        platform_status['running'] += 1
                    elif pipeline.status == WorkflowStatus.FAILED:
                        failed_count += 1
                        platform_status['failed'] += 1
                    elif pipeline.status == WorkflowStatus.SUCCESS:
                        success_count += 1
                        platform_status['success'] += 1
                
                status['platforms'][platform.value] = platform_status
                
            except Exception as e:
                status['platforms'][platform.value] = {
                    'connected': False,
                    'error': str(e)
                }
        
        # Calculate summary
        status['summary']['total_pipelines'] = total_pipelines
        status['summary']['running_pipelines'] = running_count
        status['summary']['failed_pipelines'] = failed_count
        
        if total_pipelines > 0:
            status['summary']['success_rate'] = (success_count / total_pipelines) * 100
        
        return status
    
    async def cancel_cross_platform_workflows(self, 
                                            repository: str, 
                                            platforms: List[PlatformType] = None) -> CrossPlatformOperation:
        """Cancel running workflows across multiple platforms"""
        if platforms is None:
            platforms = [p for p, active in self.active_connections.items() if active]
        
        operation = await self.coordinator.coordinate_cross_platform_operation(
            operation_type="cancel_workflows",
            platforms=platforms,
            repository=repository
        )
        
        # Execute cancellations on each platform
        for platform in platforms:
            if platform not in self.connectors:
                continue
            
            connector = self.connectors[platform]
            
            try:
                # Get running workflows for this platform
                pipelines = await self.pipeline_registry.get_pipelines_by_repository(repository)
                running_pipelines = [
                    p for p in pipelines 
                    if p.platform == platform and p.status == WorkflowStatus.RUNNING
                ]
                
                platform_results = []
                for pipeline in running_pipelines:
                    # Note: Need to get actual run ID from the connector
                    # This is a simplified implementation
                    result = await connector.cancel_workflow(repository, str(pipeline.workflow_id))
                    platform_results.append({
                        'workflow_id': pipeline.workflow_id,
                        'cancelled': result
                    })
                
                operation.results[platform.value] = platform_results
                
            except Exception as e:
                operation.errors[platform.value] = str(e)
                self.logger.error(f"Failed to cancel workflows on {platform.value}: {e}")
        
        return operation
    
    async def get_cross_platform_analytics(self, repository: str = None, days: int = 30) -> Dict[str, Any]:
        """Get analytics across all platforms"""
        analytics = {
            'time_range_days': days,
            'platforms': {},
            'summary': {
                'total_executions': 0,
                'average_success_rate': 0.0,
                'average_duration': 0.0,
                'most_active_platform': None
            }
        }
        
        platform_stats = []
        total_executions = 0
        total_success_rate = 0.0
        total_duration = 0.0
        
        for platform, connector in self.connectors.items():
            if not self.active_connections.get(platform, False):
                continue
            
            try:
                # Get pipelines for this platform
                if repository:
                    pipelines = await self.pipeline_registry.get_pipelines_by_repository(repository)
                    platform_pipelines = [p for p in pipelines if p.platform == platform]
                else:
                    platform_pipelines = await self.pipeline_registry.get_pipelines_by_platform(platform)
                
                platform_executions = len(platform_pipelines)
                platform_success_rate = sum(p.success_rate for p in platform_pipelines) / max(len(platform_pipelines), 1)
                platform_avg_duration = sum(p.avg_duration for p in platform_pipelines) / max(len(platform_pipelines), 1)
                
                analytics['platforms'][platform.value] = {
                    'executions': platform_executions,
                    'success_rate': platform_success_rate,
                    'average_duration': platform_avg_duration,
                    'pipelines': len(platform_pipelines)
                }
                
                platform_stats.append((platform.value, platform_executions))
                total_executions += platform_executions
                total_success_rate += platform_success_rate
                total_duration += platform_avg_duration
                
            except Exception as e:
                analytics['platforms'][platform.value] = {'error': str(e)}
        
        # Calculate summary
        active_platforms = len([p for p in analytics['platforms'].values() if 'error' not in p])
        
        if active_platforms > 0:
            analytics['summary']['total_executions'] = total_executions
            analytics['summary']['average_success_rate'] = total_success_rate / active_platforms
            analytics['summary']['average_duration'] = total_duration / active_platforms
            
            if platform_stats:
                analytics['summary']['most_active_platform'] = max(platform_stats, key=lambda x: x[1])[0]
        
        return analytics
    
    async def optimize_pipeline_execution(self, repository: str) -> Dict[str, Any]:
        """Provide optimization recommendations for pipeline execution"""
        optimization = {
            'repository': repository,
            'recommendations': [],
            'potential_improvements': {},
            'resource_optimization': {}
        }
        
        try:
            # Get current status and analytics
            status = await self.get_unified_status(repository)
            analytics = await self.get_cross_platform_analytics(repository)
            
            # Analyze for optimization opportunities
            total_pipelines = status['summary']['total_pipelines']
            success_rate = status['summary']['success_rate']
            avg_duration = analytics['summary']['average_duration']
            
            # Success rate optimization
            if success_rate < 90:
                optimization['recommendations'].append({
                    'type': 'success_rate',
                    'priority': 'high',
                    'description': f'Success rate is {success_rate:.1f}%, consider reviewing failing pipelines',
                    'action': 'Review and fix failing workflows'
                })
            
            # Duration optimization
            if avg_duration > 600:  # 10 minutes
                optimization['recommendations'].append({
                    'type': 'duration',
                    'priority': 'medium',
                    'description': f'Average duration is {avg_duration/60:.1f} minutes, consider parallelization',
                    'action': 'Optimize workflow parallelization and caching'
                })
            
            # Platform distribution optimization
            platform_counts = {p: data.get('pipelines', 0) for p, data in analytics['platforms'].items()}
            max_platform = max(platform_counts.values()) if platform_counts else 0
            min_platform = min(platform_counts.values()) if platform_counts else 0
            
            if max_platform - min_platform > 3:
                optimization['recommendations'].append({
                    'type': 'load_balancing',
                    'priority': 'low',
                    'description': 'Uneven distribution of pipelines across platforms',
                    'action': 'Consider redistributing workflows for better load balancing'
                })
            
            optimization['potential_improvements'] = {
                'success_rate_increase': max(0, 95 - success_rate),
                'duration_reduction': max(0, avg_duration - 300),  # Target 5 minutes
                'resource_savings': f"{len(self.active_connections)} platforms active"
            }
            
        except Exception as e:
            optimization['error'] = str(e)
            self.logger.error(f"Failed to generate optimization recommendations: {e}")
        
        return optimization