"""
KiroLinter DevOps API

FastAPI-based REST API for DevOps orchestration platform providing:
- Workflow management endpoints
- Pipeline integration management
- Analytics and reporting
- Real-time status updates
"""

from .main import app

__all__ = ["app"]