"""Celery Application Configuration

Main Celery application setup for distributed task processing in KiroLinter DevOps orchestration.
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import logging
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
CELERY_CONFIG = {
    # Broker settings
    'broker_url': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Task settings
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    
    # Task routing
    'task_routes': {
        'kirolinter.workers.workflow_worker.*': {'queue': 'workflow'},
        'kirolinter.workers.analytics_worker.*': {'queue': 'analytics'},
        'kirolinter.workers.monitoring_worker.*': {'queue': 'monitoring'},
        'kirolinter.workers.notification_worker.*': {'queue': 'notifications'},
    },
    
    # Worker settings
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'worker_max_tasks_per_child': 1000,
    
    # Task execution settings
    'task_soft_time_limit': 300,  # 5 minutes
    'task_time_limit': 600,       # 10 minutes
    'task_max_retries': 3,
    'task_default_retry_delay': 60,
    
    # Result settings
    'result_expires': 3600,  # 1 hour
    'result_persistent': True,
    
    # Monitoring
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    
    # Security
    'worker_hijack_root_logger': False,
    'worker_log_color': False,
}

# Create Celery application
app = Celery('kirolinter_devops')
app.config_from_object(CELERY_CONFIG)

# Auto-discover tasks
app.autodiscover_tasks([
    'kirolinter.workers.workflow_worker',
    'kirolinter.workers.analytics_worker', 
    'kirolinter.workers.monitoring_worker',
    'kirolinter.workers.notification_worker',
])


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal"""
    logger.info(f"Worker {sender} is ready")
    
    # Initialize worker-specific resources
    try:
        # Initialize database connections (async)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        from kirolinter.database.connection import init_db_pool
        loop.run_until_complete(init_db_pool())
        
        # Initialize Redis connections (async)
        from kirolinter.cache.redis_client import init_redis_pool
        loop.run_until_complete(init_redis_pool())
        
        logger.info("Worker initialization completed successfully")
    except Exception as e:
        logger.error(f"Worker initialization failed: {e}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal"""
    logger.info(f"Worker {sender} is shutting down")
    
    # Cleanup resources
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Close database connections (async)
        from kirolinter.database.connection import close_db_pool
        loop.run_until_complete(close_db_pool())
        
        # Close Redis connections (async)
        from kirolinter.cache.redis_client import close_redis_pool
        loop.run_until_complete(close_redis_pool())
        
        logger.info("Worker cleanup completed successfully")
    except Exception as e:
        logger.error(f"Worker cleanup failed: {e}")


# Task retry configuration
def get_retry_config(task_name: str) -> Dict[str, Any]:
    """Get retry configuration for specific task types"""
    retry_configs = {
        'workflow_execution': {
            'max_retries': 3,
            'countdown': 60,
            'backoff': True,
            'jitter': True,
        },
        'analytics_processing': {
            'max_retries': 5,
            'countdown': 30,
            'backoff': True,
            'jitter': False,
        },
        'monitoring_collection': {
            'max_retries': 2,
            'countdown': 10,
            'backoff': False,
            'jitter': False,
        },
        'notification_sending': {
            'max_retries': 3,
            'countdown': 5,
            'backoff': True,
            'jitter': True,
        },
        'default': {
            'max_retries': 3,
            'countdown': 60,
            'backoff': True,
            'jitter': True,
        }
    }
    
    return retry_configs.get(task_name, retry_configs['default'])


# Health check task
@app.task(bind=True, name='health_check')
def health_check(self):
    """Health check task for monitoring worker status"""
    try:
        # Check database connectivity
        from kirolinter.database.connection import check_db_health
        db_healthy = check_db_health()
        
        # Check Redis connectivity
        from kirolinter.cache.redis_client import check_redis_health
        redis_healthy = check_redis_health()
        
        # Check worker resources
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        health_status = {
            'worker_id': self.request.id,
            'timestamp': app.now().isoformat(),
            'database_healthy': db_healthy,
            'redis_healthy': redis_healthy,
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'status': 'healthy' if db_healthy and redis_healthy else 'unhealthy'
        }
        
        logger.info(f"Health check completed: {health_status['status']}")
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'worker_id': self.request.id,
            'timestamp': app.now().isoformat(),
            'status': 'unhealthy',
            'error': str(e)
        }


# Task monitoring and metrics
@app.task(bind=True, name='collect_worker_metrics')
def collect_worker_metrics(self):
    """Collect worker performance metrics"""
    try:
        import psutil
        from datetime import datetime
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Celery metrics
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'worker_id': self.request.id,
            'system_metrics': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_free_gb': disk.free / (1024**3),
            },
            'celery_metrics': {
                'active_tasks_count': len(active_tasks or {}),
                'scheduled_tasks_count': len(scheduled_tasks or {}),
                'reserved_tasks_count': len(reserved_tasks or {}),
            }
        }
        
        # Store metrics in Redis for monitoring
        from kirolinter.cache.redis_client import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            redis_client.setex(
                f"worker_metrics:{self.request.id}",
                300,  # 5 minutes TTL
                app.json.dumps(metrics)
            )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to collect worker metrics: {e}")
        return {'error': str(e)}


# Custom task base class with enhanced error handling
class BaseTask(app.Task):
    """Base task class with enhanced error handling and monitoring"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"Task {task_id} completed successfully")
        
        # Record success metrics
        try:
            from kirolinter.cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                redis_client.incr(f"task_success:{self.name}")
                redis_client.expire(f"task_success:{self.name}", 86400)  # 24 hours
        except Exception as e:
            logger.warning(f"Failed to record success metrics: {e}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Record failure metrics
        try:
            from kirolinter.cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                redis_client.incr(f"task_failure:{self.name}")
                redis_client.expire(f"task_failure:{self.name}", 86400)  # 24 hours
                
                # Store failure details
                failure_data = {
                    'task_id': task_id,
                    'task_name': self.name,
                    'error': str(exc),
                    'args': args,
                    'kwargs': kwargs,
                    'timestamp': app.now().isoformat()
                }
                redis_client.lpush(f"task_failures:{self.name}", app.json.dumps(failure_data))
                redis_client.ltrim(f"task_failures:{self.name}", 0, 99)  # Keep last 100 failures
                redis_client.expire(f"task_failures:{self.name}", 86400)
        except Exception as e:
            logger.warning(f"Failed to record failure metrics: {e}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry"""
        logger.warning(f"Task {task_id} retrying due to: {exc}")
        
        # Record retry metrics
        try:
            from kirolinter.cache.redis_client import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                redis_client.incr(f"task_retry:{self.name}")
                redis_client.expire(f"task_retry:{self.name}", 86400)  # 24 hours
        except Exception as e:
            logger.warning(f"Failed to record retry metrics: {e}")


# Set the base task class
app.Task = BaseTask


if __name__ == '__main__':
    # Start worker with specific configuration
    app.start([
        'worker',
        '--loglevel=info',
        '--concurrency=4',
        '--queues=workflow,analytics,monitoring,notifications',
        '--hostname=worker@%h'
    ])