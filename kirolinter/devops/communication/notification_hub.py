"""
Notification Hub

Centralized notification system for DevOps events with support for
multiple communication platforms and intelligent routing.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Supported notification channels"""
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class NotificationTemplate:
    """Template for notifications"""
    id: str
    name: str
    title_template: str
    message_template: str
    channel_specific_templates: Dict[str, Dict[str, str]] = field(default_factory=dict)
    required_variables: List[str] = field(default_factory=list)
    
    def render(self, variables: Dict[str, Any], channel: NotificationChannel = None) -> Dict[str, str]:
        """Render template with variables"""
        # Use channel-specific template if available
        if channel and channel.value in self.channel_specific_templates:
            templates = self.channel_specific_templates[channel.value]
            title = templates.get("title", self.title_template)
            message = templates.get("message", self.message_template)
        else:
            title = self.title_template
            message = self.message_template
        
        # Simple variable substitution
        for var, value in variables.items():
            title = title.replace(f"{{{var}}}", str(value))
            message = message.replace(f"{{{var}}}", str(value))
        
        return {"title": title, "message": message}


@dataclass
class NotificationRule:
    """Rule for routing notifications"""
    id: str
    name: str
    conditions: Dict[str, Any]  # Conditions for when this rule applies
    channels: List[NotificationChannel]
    priority_threshold: NotificationPriority = NotificationPriority.LOW
    escalation_delay_minutes: int = 0
    escalation_channels: List[NotificationChannel] = field(default_factory=list)
    active: bool = True
    
    def matches(self, event: Dict[str, Any]) -> bool:
        """Check if this rule matches the event"""
        for condition_key, condition_value in self.conditions.items():
            event_value = event.get(condition_key)
            
            if isinstance(condition_value, list):
                if event_value not in condition_value:
                    return False
            elif isinstance(condition_value, dict):
                # Support for operators like {">=": 0.8}
                for operator, threshold in condition_value.items():
                    if operator == ">=" and event_value < threshold:
                        return False
                    elif operator == "<=" and event_value > threshold:
                        return False
                    elif operator == ">" and event_value <= threshold:
                        return False
                    elif operator == "<" and event_value >= threshold:
                        return False
                    elif operator == "==" and event_value != threshold:
                        return False
            else:
                if event_value != condition_value:
                    return False
        
        return True


@dataclass
class Notification:
    """Individual notification"""
    id: str
    title: str
    message: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivery_status: Dict[str, str] = field(default_factory=dict)  # channel -> status
    retry_count: int = 0
    max_retries: int = 3


class NotificationHub:
    """Centralized notification hub for DevOps events"""
    
    def __init__(self):
        """Initialize notification hub"""
        self.templates: Dict[str, NotificationTemplate] = {}
        self.rules: List[NotificationRule] = []
        self.channel_configs: Dict[NotificationChannel, Dict[str, Any]] = {}
        self.pending_notifications: List[Notification] = []
        self.sent_notifications: List[Notification] = []
        self.escalation_tasks: Dict[str, asyncio.Task] = {}
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def add_template(self, template: NotificationTemplate):
        """Add a notification template"""
        self.templates[template.id] = template
        logger.info(f"Added notification template: {template.name}")
    
    def add_rule(self, rule: NotificationRule):
        """Add a notification rule"""
        self.rules.append(rule)
        logger.info(f"Added notification rule: {rule.name}")
    
    def configure_channel(self, channel: NotificationChannel, config: Dict[str, Any]):
        """Configure a notification channel"""
        self.channel_configs[channel] = config
        logger.info(f"Configured notification channel: {channel}")
    
    async def send_notification(self, event_type: str, event_data: Dict[str, Any], 
                              template_id: str = None, priority: NotificationPriority = None):
        """
        Send notification based on event
        
        Args:
            event_type: Type of event (deployment, quality_alert, etc.)
            event_data: Event data for template rendering
            template_id: Specific template to use (optional)
            priority: Override priority (optional)
        """
        logger.info(f"Processing notification for event: {event_type}")
        
        # Find matching rules
        matching_rules = [rule for rule in self.rules if rule.active and rule.matches(event_data)]
        
        if not matching_rules:
            logger.warning(f"No matching rules for event type: {event_type}")
            return
        
        # Determine template
        if not template_id:
            template_id = event_data.get("template_id", event_type)
        
        template = self.templates.get(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            return
        
        # Process each matching rule
        for rule in matching_rules:
            # Check priority threshold
            event_priority = priority or NotificationPriority(event_data.get("priority", "medium"))
            if self._priority_level(event_priority) < self._priority_level(rule.priority_threshold):
                continue
            
            # Create notification
            notification = await self._create_notification(template, rule, event_data, event_priority)
            
            # Send to channels
            await self._send_to_channels(notification, rule.channels)
            
            # Set up escalation if configured
            if rule.escalation_channels and rule.escalation_delay_minutes > 0:
                await self._schedule_escalation(notification, rule)
    
    async def send_direct_notification(self, title: str, message: str, 
                                     channels: List[NotificationChannel],
                                     priority: NotificationPriority = NotificationPriority.MEDIUM):
        """
        Send direct notification without rules or templates
        
        Args:
            title: Notification title
            message: Notification message
            channels: Channels to send to
            priority: Notification priority
        """
        notification = Notification(
            id=f"direct_{int(datetime.utcnow().timestamp())}",
            title=title,
            message=message,
            priority=priority,
            channels=channels
        )
        
        await self._send_to_channels(notification, channels)
    
    async def _create_notification(self, template: NotificationTemplate, 
                                 rule: NotificationRule, event_data: Dict[str, Any],
                                 priority: NotificationPriority) -> Notification:
        """Create notification from template and event data"""
        # Render template
        rendered = template.render(event_data)
        
        notification = Notification(
            id=f"{rule.id}_{int(datetime.utcnow().timestamp())}",
            title=rendered["title"],
            message=rendered["message"],
            priority=priority,
            channels=rule.channels,
            variables=event_data
        )
        
        return notification
    
    async def _send_to_channels(self, notification: Notification, 
                              channels: List[NotificationChannel]):
        """Send notification to specified channels"""
        for channel in channels:
            try:
                success = await self._send_to_channel(notification, channel)
                notification.delivery_status[channel.value] = "sent" if success else "failed"
            except Exception as e:
                logger.error(f"Failed to send notification to {channel}: {e}")
                notification.delivery_status[channel.value] = "error"
        
        notification.sent_at = datetime.utcnow()
        self.sent_notifications.append(notification)
    
    async def _send_to_channel(self, notification: Notification, 
                             channel: NotificationChannel) -> bool:
        """Send notification to a specific channel"""
        config = self.channel_configs.get(channel, {})
        
        if channel == NotificationChannel.SLACK:
            return await self._send_slack(notification, config)
        elif channel == NotificationChannel.TEAMS:
            return await self._send_teams(notification, config)
        elif channel == NotificationChannel.DISCORD:
            return await self._send_discord(notification, config)
        elif channel == NotificationChannel.EMAIL:
            return await self._send_email(notification, config)
        elif channel == NotificationChannel.WEBHOOK:
            return await self._send_webhook(notification, config)
        else:
            logger.warning(f"Unsupported channel: {channel}")
            return False
    
    async def _send_slack(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send notification to Slack"""
        # Mock Slack integration - would use actual Slack API
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        logger.info(f"Sending Slack notification: {notification.title}")
        # Would implement actual Slack API call here
        return True
    
    async def _send_teams(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send notification to Microsoft Teams"""
        # Mock Teams integration - would use actual Teams API
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            logger.error("Teams webhook URL not configured")
            return False
        
        logger.info(f"Sending Teams notification: {notification.title}")
        # Would implement actual Teams API call here
        return True
    
    async def _send_discord(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send notification to Discord"""
        # Mock Discord integration - would use actual Discord API
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            logger.error("Discord webhook URL not configured")
            return False
        
        logger.info(f"Sending Discord notification: {notification.title}")
        # Would implement actual Discord API call here
        return True
    
    async def _send_email(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send email notification"""
        # Mock email integration - would use actual email service
        smtp_config = config.get("smtp", {})
        recipients = config.get("recipients", [])
        
        if not recipients:
            logger.error("No email recipients configured")
            return False
        
        logger.info(f"Sending email notification to {len(recipients)} recipients: {notification.title}")
        # Would implement actual email sending here
        return True
    
    async def _send_webhook(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send webhook notification"""
        # Mock webhook integration - would make actual HTTP request
        url = config.get("url")
        if not url:
            logger.error("Webhook URL not configured")
            return False
        
        logger.info(f"Sending webhook notification: {notification.title}")
        # Would implement actual HTTP request here
        return True
    
    async def _schedule_escalation(self, notification: Notification, rule: NotificationRule):
        """Schedule escalation for a notification"""
        if not rule.escalation_channels:
            return
        
        async def escalate():
            await asyncio.sleep(rule.escalation_delay_minutes * 60)
            
            # Check if issue is still unresolved (simplified check)
            logger.info(f"Escalating notification: {notification.title}")
            await self._send_to_channels(notification, rule.escalation_channels)
        
        task = asyncio.create_task(escalate())
        self.escalation_tasks[notification.id] = task
    
    def _priority_level(self, priority: NotificationPriority) -> int:
        """Convert priority to numeric level for comparison"""
        levels = {
            NotificationPriority.LOW: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.HIGH: 3,
            NotificationPriority.CRITICAL: 4
        }
        return levels.get(priority, 1)
    
    def _initialize_default_templates(self):
        """Initialize default notification templates"""
        # Deployment notification template
        deployment_template = NotificationTemplate(
            id="deployment",
            name="Deployment Notification",
            title_template="Deployment {status}: {application} v{version}",
            message_template="Deployment of {application} version {version} to {environment} has {status}.\nDuration: {duration}\nTriggered by: {triggered_by}",
            channel_specific_templates={
                "slack": {
                    "title": "🚀 Deployment {status}: {application} v{version}",
                    "message": "Deployment of *{application}* version `{version}` to `{environment}` has *{status}*.\n• Duration: {duration}\n• Triggered by: {triggered_by}"
                }
            },
            required_variables=["application", "version", "environment", "status", "duration", "triggered_by"]
        )
        self.add_template(deployment_template)
        
        # Quality alert template
        quality_alert_template = NotificationTemplate(
            id="quality_alert",
            name="Quality Alert",
            title_template="Quality Alert: {metric_name} for {application}",
            message_template="Quality metric {metric_name} for {application} is {status}.\nCurrent value: {current_value}\nThreshold: {threshold}\nRecommendation: {recommendation}",
            channel_specific_templates={
                "slack": {
                    "title": "⚠️ Quality Alert: {metric_name} for {application}",
                    "message": "Quality metric *{metric_name}* for `{application}` is *{status}*.\n• Current value: {current_value}\n• Threshold: {threshold}\n• Recommendation: {recommendation}"
                }
            },
            required_variables=["application", "metric_name", "status", "current_value", "threshold", "recommendation"]
        )
        self.add_template(quality_alert_template)
        
        # Pipeline failure template
        pipeline_failure_template = NotificationTemplate(
            id="pipeline_failure",
            name="Pipeline Failure",
            title_template="Pipeline Failed: {pipeline_name}",
            message_template="Pipeline {pipeline_name} has failed.\nBranch: {branch}\nCommit: {commit_sha}\nError: {error_message}\nLogs: {logs_url}",
            channel_specific_templates={
                "slack": {
                    "title": "❌ Pipeline Failed: {pipeline_name}",
                    "message": "Pipeline *{pipeline_name}* has failed.\n• Branch: `{branch}`\n• Commit: `{commit_sha}`\n• Error: {error_message}\n• <{logs_url}|View Logs>"
                }
            },
            required_variables=["pipeline_name", "branch", "commit_sha", "error_message", "logs_url"]
        )
        self.add_template(pipeline_failure_template)