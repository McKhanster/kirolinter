"""
Celery Configuration

Configuration settings for Celery distributed task processing.
"""

import os
from kombu import Queue

# Broker settings
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Task routing
task_routes = {
    'kirolinter.workers.workflow_worker.*': {'queue': 'workflow'},
    'kirolinter.workers.analytics_worker.*': {'queue': 'analytics'},
    'kirolinter.workers.monitoring_worker.*': {'queue': 'monitoring'},
}

# Queue definitions
task_default_queue = 'default'
task_queues = (
    Queue('default', routing_key='default'),
    Queue('workflow', routing_key='workflow'),
    Queue('analytics', routing_key='analytics'),
    Queue('monitoring', routing_key='monitoring'),
    Queue('priority', routing_key='priority'),
)

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = False

# Task execution settings
task_acks_late = True
task_reject_on_worker_lost = True
task_ignore_result = False
task_store_errors_even_if_ignored = True

# Result settings
result_expires = 3600  # 1 hour
result_persistent = True

# Monitoring
worker_send_task_events = True
task_send_sent_event = True

# Security
worker_hijack_root_logger = False
worker_log_color = False

# Beat schedule (for periodic tasks)
beat_schedule = {
    'cleanup-expired-allocations': {
        'task': 'kirolinter.workers.monitoring_worker.cleanup_expired_allocations',
        'schedule': 300.0,  # Every 5 minutes
    },
    'collect-system-metrics': {
        'task': 'kirolinter.workers.monitoring_worker.collect_system_metrics',
        'schedule': 60.0,  # Every minute
    },
    'process-analytics-batch': {
        'task': 'kirolinter.workers.analytics_worker.process_analytics_batch',
        'schedule': 600.0,  # Every 10 minutes
    },
}

# Error handling
task_soft_time_limit = 300  # 5 minutes
task_time_limit = 600  # 10 minutes
task_max_retries = 3
task_default_retry_delay = 60  # 1 minute

# Logging
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'