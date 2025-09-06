"""
Workers Module

Distributed task processing workers for KiroLinter DevOps orchestration.
"""

from .celery_app import app as celery_app

__all__ = ['celery_app']