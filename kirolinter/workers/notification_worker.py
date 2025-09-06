"""
Notification Worker

Celery worker for sending notifications to various communication platforms
including Slack, Microsoft Teams, Discord, and email.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .celery_app import app, BaseTask, get_retry_config

logger = logging.getLogger(__name__)


class NotificationSender:
    """Handles sending notifications to various platforms"""
    
    def __init__(self):
        """Initialize notification sender"""
        self.platform_handlers = {
            'slack': self._send_slack_notification,
            'teams': self._send_teams_notification,
            'discord': self._send_discord_notification,
            'email': self._send_email_notification,
            'webhook': self._send_webhook_notification
        }
    
    async def send_notification(self, platform: str, config: Dict[str, Any], 
                              message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification to specified platform
        
        Args:
            platform: Target platform (slack, teams, discord, email, webhook)
            config: Platform-specific configuration
            message: Message content and metadata
            
        Returns:
            Dict containing send result
        """
        try:
            if platform not in self.platform_handlers:
                return {
                    'success': False,
                    'error': f'Unsupported platform: {platform}',
                    'platform': platform
                }
            
            handler = self.platform_handlers[platform]
            result = await handler(config, message)
            
            return {
                'success': True,
                'platform': platform,
                'message_id': result.get('message_id'),
                'sent_at': datetime.utcnow().isoformat(),
                **result
            }
            
        except Exception as e:
            logger.error(f"Failed to send {platform} notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform,
                'attempted_at': datetime.utcnow().isoformat()
            }
    
    async def send_multi_platform_notification(self, platforms_config: Dict[str, Dict[str, Any]], 
                                             message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification to multiple platforms
        
        Args:
            platforms_config: Configuration for multiple platforms
            message: Message content and metadata
            
        Returns:
            Dict containing results for all platforms
        """
        results = {}
        
        for platform, config in platforms_config.items():
            try:
                result = await self.send_notification(platform, config, message)
                results[platform] = result
            except Exception as e:
                logger.error(f"Failed to send notification to {platform}: {e}")
                results[platform] = {
                    'success': False,
                    'error': str(e),
                    'platform': platform
                }
        
        # Calculate overall success
        successful_sends = sum(1 for result in results.values() if result.get('success', False))
        total_sends = len(results)
        
        return {
            'overall_success': successful_sends > 0,
            'successful_sends': successful_sends,
            'total_sends': total_sends,
            'success_rate': successful_sends / total_sends if total_sends > 0 else 0,
            'results': results,
            'sent_at': datetime.utcnow().isoformat()
        }
    
    # Platform-specific notification handlers
    async def _send_slack_notification(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification"""
        # Mock implementation - would use Slack Web API
        await asyncio.sleep(0.2)  # Simulate API call
        
        # Format message for Slack
        slack_message = self._format_slack_message(message)
        
        return {
            'message_id': f"slack_{datetime.utcnow().timestamp()}",
            'channel': config.get('channel', '#general'),
            'formatted_message': slack_message,
            'webhook_url': config.get('webhook_url', 'https://hooks.slack.com/...'),
            'response_status': 200
        }
    
    async def _send_teams_notification(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send Microsoft Teams notification"""
        # Mock implementation - would use Teams webhook
        await asyncio.sleep(0.3)  # Simulate API call
        
        # Format message for Teams
        teams_message = self._format_teams_message(message)
        
        return {
            'message_id': f"teams_{datetime.utcnow().timestamp()}",
            'channel': config.get('channel', 'General'),
            'formatted_message': teams_message,
            'webhook_url': config.get('webhook_url', 'https://outlook.office.com/webhook/...'),
            'response_status': 200
        }
    
    async def _send_discord_notification(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send Discord notification"""
        # Mock implementation - would use Discord webhook
        await asyncio.sleep(0.2)  # Simulate API call
        
        # Format message for Discord
        discord_message = self._format_discord_message(message)
        
        return {
            'message_id': f"discord_{datetime.utcnow().timestamp()}",
            'channel': config.get('channel', 'general'),
            'formatted_message': discord_message,
            'webhook_url': config.get('webhook_url', 'https://discord.com/api/webhooks/...'),
            'response_status': 200
        }
    
    async def _send_email_notification(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification"""
        # Mock implementation - would use SMTP or email service
        await asyncio.sleep(0.5)  # Simulate email send
        
        # Format message for email
        email_content = self._format_email_message(message)
        
        return {
            'message_id': f"email_{datetime.utcnow().timestamp()}",
            'recipients': config.get('recipients', []),
            'subject': email_content['subject'],
            'body': email_content['body'],
            'smtp_server': config.get('smtp_server', 'smtp.example.com'),
            'response_status': 250  # SMTP success code
        }
    
    async def _send_webhook_notification(self, config: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """Send generic webhook notification"""
        # Mock implementation - would make HTTP POST request
        await asyncio.sleep(0.1)  # Simulate HTTP request
        
        return {
            'message_id': f"webhook_{datetime.utcnow().timestamp()}",
            'webhook_url': config.get('url', 'https://example.com/webhook'),
            'payload': message,
            'response_status': 200
        }
    
    # Message formatting methods
    def _format_slack_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Format message for Slack"""
        severity = message.get('severity', 'info')
        title = message.get('title', 'Notification')
        content = message.get('content', '')
        
        # Choose emoji based on severity
        emoji_map = {
            'critical': ':red_circle:',
            'error': ':warning:',
            'warning': ':yellow_circle:',
            'info': ':information_source:',
            'success': ':white_check_mark:'
        }
        
        emoji = emoji_map.get(severity, ':information_source:')
        
        slack_message = {
            'text': f"{emoji} {title}",
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"{emoji} *{title}*"
                    }
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': content
                    }
                }
            ]
        }
        
        # Add fields if present
        if 'fields' in message:
            fields = []
            for field_name, field_value in message['fields'].items():
                fields.append({
                    'type': 'mrkdwn',
                    'text': f"*{field_name}:* {field_value}"
                })
            
            if fields:
                slack_message['blocks'].append({
                    'type': 'section',
                    'fields': fields
                })
        
        # Add actions if present
        if 'actions' in message:
            actions = []
            for action in message['actions']:
                actions.append({
                    'type': 'button',
                    'text': {
                        'type': 'plain_text',
                        'text': action.get('text', 'Action')
                    },
                    'url': action.get('url', '#')
                })
            
            if actions:
                slack_message['blocks'].append({
                    'type': 'actions',
                    'elements': actions
                })
        
        return slack_message
    
    def _format_teams_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Format message for Microsoft Teams"""
        severity = message.get('severity', 'info')
        title = message.get('title', 'Notification')
        content = message.get('content', '')
        
        # Choose color based on severity
        color_map = {
            'critical': 'attention',
            'error': 'attention',
            'warning': 'warning',
            'info': 'default',
            'success': 'good'
        }
        
        theme_color = color_map.get(severity, 'default')
        
        teams_message = {
            '@type': 'MessageCard',
            '@context': 'https://schema.org/extensions',
            'summary': title,
            'themeColor': theme_color,
            'sections': [
                {
                    'activityTitle': title,
                    'activitySubtitle': content,
                    'markdown': True
                }
            ]
        }
        
        # Add facts if present
        if 'fields' in message:
            facts = []
            for field_name, field_value in message['fields'].items():
                facts.append({
                    'name': field_name,
                    'value': str(field_value)
                })
            
            if facts:
                teams_message['sections'][0]['facts'] = facts
        
        # Add actions if present
        if 'actions' in message:
            actions = []
            for action in message['actions']:
                actions.append({
                    '@type': 'OpenUri',
                    'name': action.get('text', 'Action'),
                    'targets': [
                        {
                            'os': 'default',
                            'uri': action.get('url', '#')
                        }
                    ]
                })
            
            if actions:
                teams_message['potentialAction'] = actions
        
        return teams_message
    
    def _format_discord_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Format message for Discord"""
        severity = message.get('severity', 'info')
        title = message.get('title', 'Notification')
        content = message.get('content', '')
        
        # Choose color based on severity
        color_map = {
            'critical': 0xFF0000,  # Red
            'error': 0xFF6600,     # Orange
            'warning': 0xFFFF00,   # Yellow
            'info': 0x0099FF,      # Blue
            'success': 0x00FF00    # Green
        }
        
        embed_color = color_map.get(severity, 0x0099FF)
        
        discord_message = {
            'embeds': [
                {
                    'title': title,
                    'description': content,
                    'color': embed_color,
                    'timestamp': datetime.utcnow().isoformat()
                }
            ]
        }
        
        # Add fields if present
        if 'fields' in message:
            fields = []
            for field_name, field_value in message['fields'].items():
                fields.append({
                    'name': field_name,
                    'value': str(field_value),
                    'inline': True
                })
            
            if fields:
                discord_message['embeds'][0]['fields'] = fields
        
        return discord_message
    
    def _format_email_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Format message for email"""
        title = message.get('title', 'Notification')
        content = message.get('content', '')
        severity = message.get('severity', 'info')
        
        # Create email subject
        severity_prefix = {
            'critical': '[CRITICAL]',
            'error': '[ERROR]',
            'warning': '[WARNING]',
            'info': '[INFO]',
            'success': '[SUCCESS]'
        }
        
        subject = f"{severity_prefix.get(severity, '[INFO]')} {title}"
        
        # Create email body
        body = f"{title}\n\n{content}\n\n"
        
        # Add fields if present
        if 'fields' in message:
            body += "Details:\n"
            for field_name, field_value in message['fields'].items():
                body += f"- {field_name}: {field_value}\n"
            body += "\n"
        
        # Add timestamp
        body += f"Sent at: {datetime.utcnow().isoformat()}\n"
        
        return {
            'subject': subject,
            'body': body
        }


# Global notification sender instance
notification_sender = NotificationSender()


# Celery Tasks
@app.task(bind=True, base=BaseTask, name='notification_worker.send_notification')
def send_notification_task(self, platform: str, config: Dict[str, Any], message: Dict[str, Any]):
    """
    Send notification to a specific platform
    
    Args:
        platform: Target platform
        config: Platform-specific configuration
        message: Message content and metadata
        
    Returns:
        Dict containing send result
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': f'Sending {platform} notification'})
        
        # Send notification asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                notification_sender.send_notification(platform, config, message)
            )
            
            # Log notification attempt
            logger.info(f"Notification sent to {platform}: {result.get('success', False)}")
            
            self.update_state(state='SUCCESS', meta=result)
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Notification sending failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('notification_sending')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='notification_worker.send_multi_platform_notification')
def send_multi_platform_notification_task(self, platforms_config: Dict[str, Dict[str, Any]], 
                                         message: Dict[str, Any]):
    """
    Send notification to multiple platforms
    
    Args:
        platforms_config: Configuration for multiple platforms
        message: Message content and metadata
        
    Returns:
        Dict containing results for all platforms
    """
    try:
        # Update task progress
        platform_names = list(platforms_config.keys())
        self.update_state(state='PROGRESS', meta={'status': f'Sending notifications to {len(platform_names)} platforms'})
        
        # Send notifications asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                notification_sender.send_multi_platform_notification(platforms_config, message)
            )
            
            # Log overall result
            logger.info(f"Multi-platform notification: {result['successful_sends']}/{result['total_sends']} successful")
            
            self.update_state(state='SUCCESS', meta=result)
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Multi-platform notification failed: {e}")
        
        # Retry with exponential backoff
        retry_config = get_retry_config('notification_sending')
        raise self.retry(
            exc=e,
            countdown=retry_config['countdown'],
            max_retries=retry_config['max_retries']
        )


@app.task(bind=True, base=BaseTask, name='notification_worker.send_workflow_notification')
def send_workflow_notification_task(self, workflow_result: Dict[str, Any], 
                                   notification_config: Dict[str, Any]):
    """
    Send workflow completion notification
    
    Args:
        workflow_result: Workflow execution result
        notification_config: Notification configuration
        
    Returns:
        Dict containing notification results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Preparing workflow notification'})
        
        # Create notification message based on workflow result
        workflow_id = workflow_result.get('workflow_id', 'unknown')
        status = workflow_result.get('status', 'unknown')
        duration = workflow_result.get('duration_seconds', 0)
        
        # Determine severity based on status
        severity_map = {
            'completed': 'success',
            'failed': 'error',
            'cancelled': 'warning',
            'timeout': 'error'
        }
        
        severity = severity_map.get(status, 'info')
        
        # Create message
        message = {
            'title': f'Workflow {status.title()}: {workflow_id}',
            'content': f'Workflow execution {status} in {duration:.1f} seconds',
            'severity': severity,
            'fields': {
                'Workflow ID': workflow_id,
                'Status': status.title(),
                'Duration': f'{duration:.1f}s',
                'Completed At': workflow_result.get('completed_at', 'Unknown')
            }
        }
        
        # Add error information if failed
        if status == 'failed' and 'error_message' in workflow_result:
            message['fields']['Error'] = workflow_result['error_message']
        
        # Add stage information if available
        if 'stage_results' in workflow_result:
            stage_results = workflow_result['stage_results']
            total_stages = len(stage_results)
            completed_stages = sum(1 for stage in stage_results if stage.get('status') == 'completed')
            message['fields']['Stages'] = f'{completed_stages}/{total_stages} completed'
        
        # Add actions
        if 'workflow_url' in notification_config:
            message['actions'] = [
                {
                    'text': 'View Workflow',
                    'url': notification_config['workflow_url'].format(workflow_id=workflow_id)
                }
            ]
        
        # Send notification to configured platforms
        platforms_config = notification_config.get('platforms', {})
        
        if not platforms_config:
            return {
                'success': False,
                'error': 'No notification platforms configured',
                'workflow_id': workflow_id
            }
        
        # Use multi-platform notification task
        result = send_multi_platform_notification_task.delay(platforms_config, message).get()
        
        return {
            'success': result.get('overall_success', False),
            'workflow_id': workflow_id,
            'notification_result': result
        }
        
    except Exception as e:
        logger.error(f"Workflow notification failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'workflow_id': workflow_result.get('workflow_id', 'unknown')
        }


@app.task(bind=True, base=BaseTask, name='notification_worker.send_alert_notification')
def send_alert_notification_task(self, alert_data: Dict[str, Any], 
                                notification_config: Dict[str, Any]):
    """
    Send alert notification for system issues
    
    Args:
        alert_data: Alert information
        notification_config: Notification configuration
        
    Returns:
        Dict containing notification results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Sending alert notification'})
        
        # Create alert message
        alert_type = alert_data.get('type', 'unknown')
        alert_severity = alert_data.get('severity', 'warning')
        alert_title = alert_data.get('title', 'System Alert')
        alert_description = alert_data.get('description', 'An alert has been triggered')
        
        message = {
            'title': f'{alert_severity.upper()}: {alert_title}',
            'content': alert_description,
            'severity': alert_severity,
            'fields': {
                'Alert Type': alert_type,
                'Severity': alert_severity.title(),
                'Triggered At': alert_data.get('triggered_at', datetime.utcnow().isoformat())
            }
        }
        
        # Add additional fields from alert data
        if 'metrics' in alert_data:
            for metric_name, metric_value in alert_data['metrics'].items():
                message['fields'][metric_name.title()] = str(metric_value)
        
        # Add source information
        if 'source' in alert_data:
            message['fields']['Source'] = alert_data['source']
        
        # Add actions for alert management
        if 'alert_url' in notification_config:
            message['actions'] = [
                {
                    'text': 'View Alert',
                    'url': notification_config['alert_url'].format(alert_id=alert_data.get('id', ''))
                }
            ]
        
        # Send notification to configured platforms
        platforms_config = notification_config.get('platforms', {})
        
        if not platforms_config:
            return {
                'success': False,
                'error': 'No notification platforms configured',
                'alert_id': alert_data.get('id', 'unknown')
            }
        
        # Use multi-platform notification task
        result = send_multi_platform_notification_task.delay(platforms_config, message).get()
        
        return {
            'success': result.get('overall_success', False),
            'alert_id': alert_data.get('id', 'unknown'),
            'notification_result': result
        }
        
    except Exception as e:
        logger.error(f"Alert notification failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'alert_id': alert_data.get('id', 'unknown')
        }


@app.task(bind=True, base=BaseTask, name='notification_worker.send_digest_notification')
def send_digest_notification_task(self, digest_data: Dict[str, Any], 
                                 notification_config: Dict[str, Any]):
    """
    Send periodic digest notification with summary information
    
    Args:
        digest_data: Digest information and metrics
        notification_config: Notification configuration
        
    Returns:
        Dict containing notification results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Preparing digest notification'})
        
        # Create digest message
        period = digest_data.get('period', 'daily')
        start_time = digest_data.get('start_time', '')
        end_time = digest_data.get('end_time', '')
        
        message = {
            'title': f'{period.title()} DevOps Digest',
            'content': f'Summary for {start_time} to {end_time}',
            'severity': 'info',
            'fields': {}
        }
        
        # Add workflow metrics
        if 'workflow_metrics' in digest_data:
            wf_metrics = digest_data['workflow_metrics']
            message['fields']['Workflows Executed'] = str(wf_metrics.get('total_executed', 0))
            message['fields']['Success Rate'] = f"{wf_metrics.get('success_rate', 0):.1%}"
            message['fields']['Avg Duration'] = f"{wf_metrics.get('avg_duration_minutes', 0):.1f}m"
        
        # Add CI/CD metrics
        if 'cicd_metrics' in digest_data:
            cicd_metrics = digest_data['cicd_metrics']
            message['fields']['Builds'] = str(cicd_metrics.get('total_builds', 0))
            message['fields']['Build Success Rate'] = f"{cicd_metrics.get('success_rate', 0):.1%}"
        
        # Add infrastructure metrics
        if 'infrastructure_metrics' in digest_data:
            infra_metrics = digest_data['infrastructure_metrics']
            message['fields']['Avg CPU Usage'] = f"{infra_metrics.get('avg_cpu_percent', 0):.1f}%"
            message['fields']['Avg Memory Usage'] = f"{infra_metrics.get('avg_memory_percent', 0):.1f}%"
        
        # Add alert summary
        if 'alert_summary' in digest_data:
            alert_summary = digest_data['alert_summary']
            message['fields']['Alerts Triggered'] = str(alert_summary.get('total_alerts', 0))
            message['fields']['Critical Alerts'] = str(alert_summary.get('critical_alerts', 0))
        
        # Add dashboard link
        if 'dashboard_url' in notification_config:
            message['actions'] = [
                {
                    'text': 'View Dashboard',
                    'url': notification_config['dashboard_url']
                }
            ]
        
        # Send notification to configured platforms
        platforms_config = notification_config.get('platforms', {})
        
        if not platforms_config:
            return {
                'success': False,
                'error': 'No notification platforms configured',
                'period': period
            }
        
        # Use multi-platform notification task
        result = send_multi_platform_notification_task.delay(platforms_config, message).get()
        
        return {
            'success': result.get('overall_success', False),
            'period': period,
            'notification_result': result
        }
        
    except Exception as e:
        logger.error(f"Digest notification failed: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'period': digest_data.get('period', 'unknown')
        }