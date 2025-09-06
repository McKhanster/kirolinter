"""
DevOps Communication Integration

Communication and notification components for DevOps workflows including:
- Centralized notification hub
- Platform integrations (Slack, Teams, Discord)
- Webhook management
- Alert routing and escalation
"""

from .notification_hub import NotificationHub

__all__ = [
    "NotificationHub",
]