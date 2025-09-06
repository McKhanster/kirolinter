"""
Workflow Worker

Enhanced Celery worker for executing workflows in the background with
distributed task processing, intelligent failure recovery, and monitoring.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .celery_app import app, BaseTask, get_retry_config
from ..devops.orchestration.workflow_engine import WorkflowEngine
from ..devops.models.workflow import WorkflowDefinition, ExecutionContext, WorkflowResult, WorkflowStage, StageType

logger = logging.getLogger(__name__)

# Global workflow engine instance
workflow_engine = None

def get_workflow_engine():
    """Get or create workflow engine instance"""
    global workflow_engine
    if workflow_engine is None:
        workflow_engine = WorkflowEngine()
    return workflow_engine


@app.task(bind=True, base=BaseTask, name='workflow_worker.execute_workflow')
def execute_workflow_task(self, workflow_definition_dict: Dict[str, Any],
                         context_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a workflow in the background
    
    Args:
        workflow_definition_dict: Serialized workflow definition
        context_dict: Optional execution context
        
    Returns:
        Dict containing workflow execution result
    """
    try:
        # Deserialize workflow definition
        workflow_definition = WorkflowDefinition.from_dict(workflow_definition_dict)
        
        # Create execution context
        if context_dict:
            context = ExecutionContext.from_dict(context_dict)
        else:
            context = ExecutionContext(
                workflow_id=workflow_definition.id,
                execution_id=self.request.id,
                triggered_by="celery_worker"
            )
        
        # Get workflow engine instance
        engine = get_workflow_engine()
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Starting workflow execution'})
        
        # Execute workflow asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                engine.execute_workflow(workflow_definition, context)
            )
            
            logger.info(f"Workflow {workflow_definition.id} completed with status: {result.status}")
            
            return {
                'success': True,
                'workflow_id': result.workflow_id,
                'execution_id': result.execution_id,
                'status': result.status.value,
                'duration_seconds': result.duration_seconds,
                'stage_count': len(result.stage_results),
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'error_message': result.error_message
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('workflow_execution')
        try:
            raise self.retry(
                exc=e,
                countdown=retry_config['countdown'],
                max_retries=retry_config['max_retries']
            )
        except self.MaxRetriesExceededError:
            # Update task state after max retries
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'workflow_id': workflow_definition_dict.get('id', 'unknown'),
                    'timestamp': datetime.utcnow().isoformat(),
                    'max_retries_exceeded': True
                }
            )
            
            return {
                'success': False,
                'error': str(e),
                'workflow_id': workflow_definition_dict.get('id', 'unknown'),
                'execution_id': self.request.id,
                'max_retries_exceeded': True
            }


@app.task(bind=True, name='workflow_worker.cancel_workflow')
def cancel_workflow_task(self, execution_id: str) -> Dict[str, Any]:
    """
    Cancel a running workflow
    
    Args:
        execution_id: Execution identifier
        
    Returns:
        Dict containing cancellation result
    """
    try:
        # Initialize workflow engine
        workflow_engine = WorkflowEngine()
        
        # Cancel workflow asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(
                workflow_engine.cancel_workflow(execution_id)
            )
            
            logger.info(f"Workflow cancellation for {execution_id}: {'success' if success else 'failed'}")
            
            return {
                'success': success,
                'execution_id': execution_id,
                'cancelled_at': datetime.utcnow().isoformat()
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Workflow cancellation failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'execution_id': execution_id
        }


@app.task(bind=True, name='workflow_worker.get_workflow_status')
def get_workflow_status_task(self, execution_id: str) -> Dict[str, Any]:
    """
    Get workflow execution status
    
    Args:
        execution_id: Execution identifier
        
    Returns:
        Dict containing workflow status
    """
    try:
        # Initialize workflow engine
        workflow_engine = WorkflowEngine()
        
        # Get status asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                workflow_engine.get_execution_status(execution_id)
            )
            
            if result:
                return {
                    'found': True,
                    'workflow_id': result.workflow_id,
                    'execution_id': result.execution_id,
                    'status': result.status.value,
                    'started_at': result.started_at.isoformat() if result.started_at else None,
                    'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                    'duration_seconds': result.duration_seconds,
                    'stage_count': len(result.stage_results),
                    'error_message': result.error_message
                }
            else:
                return {
                    'found': False,
                    'execution_id': execution_id
                }
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        
        return {
            'found': False,
            'error': str(e),
            'execution_id': execution_id
        }


@app.task(bind=True, name='workflow_worker.retry_failed_stage')
def retry_failed_stage_task(self, workflow_id: str, execution_id: str,
                           stage_id: str) -> Dict[str, Any]:
    """
    Retry a failed workflow stage
    
    Args:
        workflow_id: Workflow identifier
        execution_id: Execution identifier
        stage_id: Stage identifier to retry
        
    Returns:
        Dict containing retry result
    """
    try:
        logger.info(f"Retrying stage {stage_id} for workflow {workflow_id}")
        
        # In a real implementation, this would:
        # 1. Load the workflow state
        # 2. Retry the specific stage
        # 3. Update the workflow result
        
        # Mock implementation
        return {
            'success': True,
            'workflow_id': workflow_id,
            'execution_id': execution_id,
            'stage_id': stage_id,
            'retried_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stage retry failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'workflow_id': workflow_id,
            'execution_id': execution_id,
            'stage_id': stage_id
        }


@app.task(bind=True, name='workflow_worker.cleanup_completed_workflows')
def cleanup_completed_workflows_task(self, max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up completed workflow data
    
    Args:
        max_age_hours: Maximum age of completed workflows to keep
        
    Returns:
        Dict containing cleanup statistics
    """
    try:
        logger.info(f"Cleaning up workflows older than {max_age_hours} hours")
        
        # In a real implementation, this would:
        # 1. Query database for old completed workflows
        # 2. Archive or delete old workflow data
        # 3. Clean up associated resources
        
        # Mock implementation
        cleaned_count = 5  # Mock number of cleaned workflows
        
        return {
            'success': True,
            'cleaned_workflows': cleaned_count,
            'max_age_hours': max_age_hours,
            'cleaned_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Workflow cleanup failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'max_age_hours': max_age_hours
        }

# Enhanced workflow execution tasks
@app.task(bind=True, base=BaseTask, name='workflow_worker.execute_workflow_stage')
def execute_workflow_stage_task(self, stage_data: Dict[str, Any], context_data: Dict[str, Any]):
    """
    Execute a single workflow stage
    
    Args:
        stage_data: Stage definition and parameters
        context_data: Execution context information
        
    Returns:
        Dict containing stage execution result
    """
    try:
        # Update task progress
        stage_id = stage_data.get('id', 'unknown')
        self.update_state(state='PROGRESS', meta={'status': f'Executing stage {stage_id}'})
        
        # Get workflow engine
        engine = get_workflow_engine()
        
        # Create stage and context objects
        stage = WorkflowStage(
            id=stage_data['id'],
            name=stage_data['name'],
            type=StageType(stage_data.get('type', 'generic')),
            dependencies=stage_data.get('dependencies', []),
            parameters=stage_data.get('parameters', {}),
            timeout_seconds=stage_data.get('timeout_seconds', 300),
            allow_failure=stage_data.get('allow_failure', False),
            retry_count=stage_data.get('retry_count', 0)
        )
        
        context = ExecutionContext(
            workflow_id=context_data['workflow_id'],
            execution_id=context_data['execution_id'],
            triggered_by=context_data.get('triggered_by', 'celery_worker'),
            environment=context_data.get('environment', 'default'),
            parameters=context_data.get('parameters', {}),
            metadata=context_data.get('metadata', {})
        )
        
        # Execute stage asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                engine._execute_stage(stage, context, None)
            )
            
            # Convert result to dict
            result_dict = {
                'success': result.status.value == 'completed',
                'stage_id': stage.id,
                'execution_id': context.execution_id,
                'status': result.status.value,
                'output': result.output,
                'error_message': result.error_message,
                'started_at': result.started_at.isoformat() if result.started_at else None,
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'duration_seconds': result.duration_seconds
            }
            
            # Update final state
            if result_dict['success']:
                self.update_state(state='SUCCESS', meta=result_dict)
            else:
                self.update_state(state='FAILURE', meta=result_dict)
            
            return result_dict
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Stage execution task failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('workflow_execution')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='workflow_worker.execute_parallel_stages')
def execute_parallel_stages_task(self, stages_data: List[Dict[str, Any]], context_data: Dict[str, Any]):
    """
    Execute multiple stages in parallel
    
    Args:
        stages_data: List of stage definitions
        context_data: Execution context information
        
    Returns:
        List of stage execution results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Executing {len(stages_data)} stages in parallel'})
        
        # Create subtasks for each stage
        stage_tasks = []
        for stage_data in stages_data:
            task = execute_workflow_stage_task.delay(stage_data, context_data)
            stage_tasks.append(task)
        
        # Wait for all stages to complete
        results = []
        for task in stage_tasks:
            try:
                result = task.get(timeout=1800)  # 30 minutes timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel stage task failed: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'stage_id': 'unknown',
                    'execution_id': context_data.get('execution_id')
                })
        
        # Check overall success
        all_successful = all(result.get('success', False) for result in results)
        
        if all_successful:
            self.update_state(state='SUCCESS', meta={'results': results})
        else:
            failed_stages = [r for r in results if not r.get('success', False)]
            self.update_state(state='FAILURE', meta={'results': results, 'failed_stages': failed_stages})
        
        return results
        
    except Exception as e:
        logger.error(f"Parallel stages task failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('workflow_execution')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='workflow_worker.generate_dynamic_workflow')
def generate_dynamic_workflow_task(self, code_changes: Dict[str, Any], context: Dict[str, Any]):
    """
    Generate a dynamic workflow based on code changes
    
    Args:
        code_changes: Information about code changes
        context: Additional context for workflow generation
        
    Returns:
        Dict containing generated workflow definition
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Analyzing code changes and generating workflow'})
        
        # Get workflow engine
        engine = get_workflow_engine()
        
        # Generate workflow asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            workflow_def = loop.run_until_complete(
                engine.generate_dynamic_workflow(code_changes, context)
            )
            
            # Convert to dict for serialization
            workflow_dict = {
                'id': workflow_def.id,
                'name': workflow_def.name,
                'description': workflow_def.description,
                'version': workflow_def.version,
                'nodes': [
                    {
                        'id': node.id,
                        'name': node.name,
                        'task_type': node.task_type,
                        'dependencies': node.dependencies,
                        'parameters': node.parameters,
                        'resource_requirements': node.resource_requirements,
                        'timeout_seconds': node.timeout_seconds,
                        'max_retries': node.max_retries
                    }
                    for node in workflow_def.nodes
                ],
                'dependencies': workflow_def.dependencies,
                'metadata': workflow_def.metadata,
                'timeout_seconds': workflow_def.timeout_seconds,
                'max_parallel_nodes': workflow_def.max_parallel_nodes
            }
            
            self.update_state(state='SUCCESS', meta=workflow_dict)
            return workflow_dict
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Dynamic workflow generation failed: {e}")
        
        # Don't retry workflow generation failures
        return {
            'success': False,
            'error': str(e),
            'code_changes': code_changes
        }


@app.task(bind=True, base=BaseTask, name='workflow_worker.optimize_workflow_performance')
def optimize_workflow_performance_task(self, workflow_id: str):
    """
    Optimize workflow performance based on historical data
    
    Args:
        workflow_id: Workflow identifier to optimize
        
    Returns:
        Dict containing optimization results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Optimizing workflow {workflow_id}'})
        
        # Get workflow engine
        engine = get_workflow_engine()
        
        # Optimize performance asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            optimization_result = loop.run_until_complete(
                engine.optimize_performance()
            )
            
            self.update_state(state='SUCCESS', meta=optimization_result)
            return optimization_result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Workflow optimization failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'workflow_id': workflow_id
        }


@app.task(bind=True, base=BaseTask, name='workflow_worker.collect_workflow_metrics')
def collect_workflow_metrics_task(self, time_range_hours: int = 24):
    """
    Collect workflow execution metrics
    
    Args:
        time_range_hours: Time range for metrics collection
        
    Returns:
        Dict containing collected metrics
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Collecting metrics for last {time_range_hours} hours'})
        
        # Get workflow engine
        engine = get_workflow_engine()
        
        # Get performance metrics
        metrics = engine.get_performance_metrics()
        
        # Add timestamp and time range
        metrics['collected_at'] = datetime.utcnow().isoformat()
        metrics['time_range_hours'] = time_range_hours
        
        # Store metrics in Redis for monitoring dashboard
        try:
            from ..cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(
                    f"workflow_metrics:{datetime.utcnow().strftime('%Y%m%d_%H')}",
                    3600,  # 1 hour TTL
                    app.json.dumps(metrics)
                )
        except Exception as e:
            logger.warning(f"Failed to store metrics in Redis: {e}")
        
        self.update_state(state='SUCCESS', meta=metrics)
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'time_range_hours': time_range_hours
        }


@app.task(bind=True, base=BaseTask, name='workflow_worker.handle_workflow_failure')
def handle_workflow_failure_task(self, failure_data: Dict[str, Any]):
    """
    Handle workflow execution failure with intelligent recovery
    
    Args:
        failure_data: Failure context and information
        
    Returns:
        Dict containing recovery actions taken
    """
    try:
        # Update task progress
        execution_id = failure_data.get('execution_id', 'unknown')
        self.update_state(state='PROGRESS', meta={'status': f'Handling failure for execution {execution_id}'})
        
        # Get workflow engine
        engine = get_workflow_engine()
        
        # Handle failure asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_result = loop.run_until_complete(
                engine.handle_failure(
                    workflow_id=failure_data.get('workflow_id'),
                    execution_id=execution_id,
                    failure_context=failure_data
                )
            )
            
            self.update_state(state='SUCCESS', meta=recovery_result)
            return recovery_result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failure handling task failed: {e}")
        
        # Don't retry failure handling to avoid infinite loops
        return {
            'success': False,
            'error': f'Failure handling failed: {str(e)}',
            'execution_id': failure_data.get('execution_id')
        }


# Periodic maintenance tasks
@app.task(bind=True, base=BaseTask, name='workflow_worker.cleanup_old_executions')
def cleanup_old_executions_task(self, max_age_days: int = 7):
    """
    Clean up old workflow execution data
    
    Args:
        max_age_days: Maximum age of executions to keep
        
    Returns:
        Dict containing cleanup statistics
    """
    try:
        logger.info(f"Cleaning up workflow executions older than {max_age_days} days")
        
        # In a real implementation, this would:
        # 1. Query database for old executions
        # 2. Archive or delete old execution data
        # 3. Clean up associated resources and cache entries
        
        # Mock cleanup for now
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        # Clean up Redis cache entries
        try:
            from ..cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                # Clean up old metrics
                pattern = "workflow_metrics:*"
                keys = redis_client.keys(pattern)
                for key in keys:
                    # Extract date from key and check if old
                    try:
                        date_str = key.decode().split(':')[1]
                        key_date = datetime.strptime(date_str, '%Y%m%d_%H')
                        if key_date < cutoff_date:
                            redis_client.delete(key)
                            cleaned_count += 1
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            logger.warning(f"Failed to clean up Redis cache: {e}")
        
        result = {
            'success': True,
            'cleaned_executions': cleaned_count,
            'max_age_days': max_age_days,
            'cutoff_date': cutoff_date.isoformat(),
            'cleaned_at': datetime.utcnow().isoformat()
        }
        
        self.update_state(state='SUCCESS', meta=result)
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'max_age_days': max_age_days
        }


# Monitoring and health check tasks
@app.task(bind=True, base=BaseTask, name='workflow_worker.workflow_health_check')
def workflow_health_check_task(self):
    """
    Perform health check on workflow system
    
    Returns:
        Dict containing health status
    """
    try:
        # Check workflow engine health
        engine = get_workflow_engine()
        
        # Get system metrics
        metrics = engine.get_performance_metrics()
        
        # Check resource utilization
        resource_utilization = engine.resource_manager.get_resource_utilization()
        
        # Check failure statistics
        failure_stats = engine.failure_handler.get_failure_statistics()
        
        # Determine overall health
        health_score = 100
        issues = []
        
        # Check resource utilization
        for pool_name, pool_info in resource_utilization.items():
            utilization = pool_info.get('utilization_percentage', 0)
            if utilization > 90:
                health_score -= 20
                issues.append(f"High resource utilization in {pool_name}: {utilization:.1f}%")
            elif utilization > 80:
                health_score -= 10
                issues.append(f"Moderate resource utilization in {pool_name}: {utilization:.1f}%")
        
        # Check failure rate
        total_failures = failure_stats.get('total_failures', 0)
        if total_failures > 100:
            health_score -= 30
            issues.append(f"High failure count: {total_failures}")
        elif total_failures > 50:
            health_score -= 15
            issues.append(f"Moderate failure count: {total_failures}")
        
        # Check success rate
        success_rate = metrics.get('success_rate', 1.0)
        if success_rate < 0.8:
            health_score -= 25
            issues.append(f"Low success rate: {success_rate:.1%}")
        elif success_rate < 0.9:
            health_score -= 10
            issues.append(f"Moderate success rate: {success_rate:.1%}")
        
        health_status = {
            'healthy': health_score >= 80,
            'health_score': max(0, health_score),
            'issues': issues,
            'metrics': metrics,
            'resource_utilization': resource_utilization,
            'failure_statistics': failure_stats,
            'checked_at': datetime.utcnow().isoformat()
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        return {
            'healthy': False,
            'health_score': 0,
            'error': str(e),
            'checked_at': datetime.utcnow().isoformat()
        }