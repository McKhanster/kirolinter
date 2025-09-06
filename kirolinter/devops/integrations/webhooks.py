"""
Webhook Handlers for DevOps Integration

Handles incoming webhooks from various platforms like GitHub, GitLab, Jenkins, etc.
to trigger appropriate workflows and maintain real-time GitOps integration.
"""

import logging
import asyncio
import hashlib
import hmac
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from aiohttp import web
from aiohttp.web import Request, Response

from .git_events import GitEvent, GitEventType, GitEventDetector

logger = logging.getLogger(__name__)


class WebhookSource(Enum):
    """Webhook source platforms"""
    GITHUB = "github"
    GITLAB = "gitlab"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"
    BITBUCKET = "bitbucket"
    GENERIC = "generic"


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    source: WebhookSource
    secret: Optional[str] = None
    enabled: bool = True
    endpoint_path: str = "/webhook"
    verify_signature: bool = True
    supported_events: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default supported events based on source"""
        if not self.supported_events:
            if self.source == WebhookSource.GITHUB:
                self.supported_events = ['push', 'pull_request', 'create', 'delete', 'release']
            elif self.source == WebhookSource.GITLAB:
                self.supported_events = ['push', 'merge_request', 'tag_push', 'pipeline']
            elif self.source == WebhookSource.JENKINS:
                self.supported_events = ['build_started', 'build_completed', 'build_failed']
            else:
                self.supported_events = ['push', 'pull_request', 'build']


@dataclass
class WebhookEvent:
    """Represents a webhook event"""
    source: WebhookSource
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    headers: Dict[str, str]
    signature: Optional[str] = None
    verified: bool = False
    webhook_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate webhook ID if not provided"""
        if not self.webhook_id:
            data_str = f"{self.source.value}-{self.event_type}-{self.timestamp}"
            self.webhook_id = hashlib.md5(data_str.encode()).hexdigest()[:16]


class WebhookVerifier:
    """Handles webhook signature verification"""
    
    @staticmethod
    def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature"""
        try:
            if not signature.startswith('sha256='):
                return False
            
            signature = signature[7:]  # Remove 'sha256='
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying GitHub signature: {e}")
            return False
    
    @staticmethod
    def verify_gitlab_signature(payload: bytes, token: str, secret: str) -> bool:
        """Verify GitLab webhook token"""
        return hmac.compare_digest(token, secret)
    
    @staticmethod
    def verify_jenkins_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify Jenkins webhook signature"""
        try:
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha1
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying Jenkins signature: {e}")
            return False


class WebhookParser:
    """Parses webhook payloads from different sources"""
    
    @staticmethod
    def parse_github_webhook(payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[GitEvent]:
        """Parse GitHub webhook into GitEvent"""
        try:
            event_type = headers.get('x-github-event', '')
            
            if event_type == 'push':
                return GitEvent(
                    event_type=GitEventType.PUSH,
                    repository_path=payload['repository']['full_name'],
                    timestamp=datetime.utcnow(),
                    branch=payload['ref'].replace('refs/heads/', '') if payload['ref'].startswith('refs/heads/') else None,
                    commit_hash=payload['after'],
                    author=payload.get('pusher', {}).get('name'),
                    message=f"Push to {payload['ref']}",
                    files_changed=[
                        f for commit in payload.get('commits', [])
                        for f in commit.get('modified', []) + commit.get('added', [])
                    ],
                    event_data={
                        'commits_count': len(payload.get('commits', [])),
                        'repository_url': payload['repository']['html_url'],
                        'pusher': payload.get('pusher', {}),
                        'forced': payload.get('forced', False)
                    }
                )
            
            elif event_type == 'pull_request':
                return GitEvent(
                    event_type=GitEventType.PULL_REQUEST,
                    repository_path=payload['repository']['full_name'],
                    timestamp=datetime.utcnow(),
                    branch=payload['pull_request']['head']['ref'],
                    commit_hash=payload['pull_request']['head']['sha'],
                    author=payload['pull_request']['user']['login'],
                    message=payload['pull_request']['title'],
                    event_data={
                        'action': payload.get('action'),
                        'pr_number': payload['pull_request']['number'],
                        'base_branch': payload['pull_request']['base']['ref'],
                        'head_branch': payload['pull_request']['head']['ref'],
                        'repository_url': payload['repository']['html_url'],
                        'pr_url': payload['pull_request']['html_url']
                    }
                )
            
            elif event_type == 'create':
                ref_type = payload.get('ref_type')
                if ref_type == 'branch':
                    return GitEvent(
                        event_type=GitEventType.BRANCH_CREATE,
                        repository_path=payload['repository']['full_name'],
                        timestamp=datetime.utcnow(),
                        branch=payload['ref'],
                        author=payload.get('sender', {}).get('login'),
                        event_data={
                            'ref_type': ref_type,
                            'ref': payload['ref'],
                            'repository_url': payload['repository']['html_url']
                        }
                    )
                elif ref_type == 'tag':
                    return GitEvent(
                        event_type=GitEventType.TAG_CREATE,
                        repository_path=payload['repository']['full_name'],
                        timestamp=datetime.utcnow(),
                        commit_hash=payload.get('master_branch'),
                        author=payload.get('sender', {}).get('login'),
                        event_data={
                            'ref_type': ref_type,
                            'ref': payload['ref'],
                            'tag_name': payload['ref'],
                            'repository_url': payload['repository']['html_url']
                        }
                    )
            
            elif event_type == 'delete':
                ref_type = payload.get('ref_type')
                if ref_type == 'branch':
                    return GitEvent(
                        event_type=GitEventType.BRANCH_DELETE,
                        repository_path=payload['repository']['full_name'],
                        timestamp=datetime.utcnow(),
                        branch=payload['ref'],
                        author=payload.get('sender', {}).get('login'),
                        event_data={
                            'ref_type': ref_type,
                            'ref': payload['ref'],
                            'repository_url': payload['repository']['html_url']
                        }
                    )
                elif ref_type == 'tag':
                    return GitEvent(
                        event_type=GitEventType.TAG_DELETE,
                        repository_path=payload['repository']['full_name'],
                        timestamp=datetime.utcnow(),
                        author=payload.get('sender', {}).get('login'),
                        event_data={
                            'ref_type': ref_type,
                            'ref': payload['ref'],
                            'tag_name': payload['ref'],
                            'repository_url': payload['repository']['html_url']
                        }
                    )
        
        except Exception as e:
            logger.error(f"Error parsing GitHub webhook: {e}")
        
        return None
    
    @staticmethod
    def parse_gitlab_webhook(payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[GitEvent]:
        """Parse GitLab webhook into GitEvent"""
        try:
            event_type = headers.get('x-gitlab-event', '')
            
            if event_type == 'Push Hook':
                return GitEvent(
                    event_type=GitEventType.PUSH,
                    repository_path=payload['project']['path_with_namespace'],
                    timestamp=datetime.utcnow(),
                    branch=payload['ref'].replace('refs/heads/', '') if payload['ref'].startswith('refs/heads/') else None,
                    commit_hash=payload['after'],
                    author=payload.get('user_name'),
                    message=f"Push to {payload['ref']}",
                    files_changed=[
                        f for commit in payload.get('commits', [])
                        for f in commit.get('modified', []) + commit.get('added', [])
                    ],
                    event_data={
                        'commits_count': len(payload.get('commits', [])),
                        'project_id': payload['project']['id'],
                        'project_url': payload['project']['web_url'],
                        'before': payload.get('before'),
                        'after': payload.get('after')
                    }
                )
            
            elif event_type == 'Merge Request Hook':
                return GitEvent(
                    event_type=GitEventType.PULL_REQUEST,
                    repository_path=payload['project']['path_with_namespace'],
                    timestamp=datetime.utcnow(),
                    branch=payload['object_attributes']['source_branch'],
                    commit_hash=payload['object_attributes']['last_commit']['id'],
                    author=payload['object_attributes']['author']['username'],
                    message=payload['object_attributes']['title'],
                    event_data={
                        'action': payload['object_attributes']['action'],
                        'mr_iid': payload['object_attributes']['iid'],
                        'source_branch': payload['object_attributes']['source_branch'],
                        'target_branch': payload['object_attributes']['target_branch'],
                        'project_url': payload['project']['web_url'],
                        'mr_url': payload['object_attributes']['url']
                    }
                )
        
        except Exception as e:
            logger.error(f"Error parsing GitLab webhook: {e}")
        
        return None
    
    @staticmethod
    def parse_jenkins_webhook(payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[GitEvent]:
        """Parse Jenkins webhook into GitEvent"""
        try:
            # Jenkins webhooks can vary, this is a basic example
            build_status = payload.get('build', {}).get('status')
            
            if build_status:
                # Map Jenkins build events to Git events
                # This is simplified - real implementation would be more complex
                return GitEvent(
                    event_type=GitEventType.COMMIT,  # Generic mapping
                    repository_path=payload.get('project', {}).get('name', 'unknown'),
                    timestamp=datetime.utcnow(),
                    commit_hash=payload.get('build', {}).get('scm', {}).get('commit'),
                    author=payload.get('build', {}).get('scm', {}).get('culprits', [{}])[0].get('fullName'),
                    message=f"Jenkins build {build_status}",
                    event_data={
                        'build_number': payload.get('build', {}).get('number'),
                        'build_status': build_status,
                        'build_url': payload.get('build', {}).get('full_url'),
                        'duration': payload.get('build', {}).get('duration')
                    }
                )
        
        except Exception as e:
            logger.error(f"Error parsing Jenkins webhook: {e}")
        
        return None


class WebhookHandler:
    """Main webhook handler that processes incoming webhooks"""
    
    def __init__(self, redis_client=None, git_event_detector: Optional[GitEventDetector] = None):
        """Initialize webhook handler"""
        self.redis_client = redis_client
        self.git_event_detector = git_event_detector
        self.configurations: Dict[str, WebhookConfig] = {}
        self.event_handlers: Dict[WebhookSource, List[Callable]] = {
            source: [] for source in WebhookSource
        }
        self.verifier = WebhookVerifier()
        self.parser = WebhookParser()
        self.logger = logging.getLogger(__name__)
    
    def add_webhook_config(self, endpoint: str, config: WebhookConfig):
        """Add webhook configuration"""
        self.configurations[endpoint] = config
        self.logger.info(f"Added webhook configuration for {config.source.value} at {endpoint}")
    
    def remove_webhook_config(self, endpoint: str):
        """Remove webhook configuration"""
        if endpoint in self.configurations:
            del self.configurations[endpoint]
            self.logger.info(f"Removed webhook configuration for {endpoint}")
    
    def register_webhook_handler(self, source: WebhookSource, handler: Callable[[WebhookEvent], None]):
        """Register a handler for webhook events from specific source"""
        self.event_handlers[source].append(handler)
        self.logger.info(f"Registered webhook handler for {source.value}")
    
    async def handle_webhook(self, request: Request) -> Response:
        """Handle incoming webhook requests"""
        try:
            # Get endpoint path
            endpoint = request.path
            
            # Check if we have configuration for this endpoint
            if endpoint not in self.configurations:
                return web.Response(text="Webhook endpoint not configured", status=404)
            
            config = self.configurations[endpoint]
            if not config.enabled:
                return web.Response(text="Webhook endpoint disabled", status=403)
            
            # Read request body and headers
            body = await request.read()
            headers = dict(request.headers)
            
            # Verify signature if required
            if config.verify_signature and config.secret:
                if not await self._verify_webhook_signature(config, body, headers):
                    return web.Response(text="Invalid signature", status=401)
            
            # Parse payload
            try:
                payload = json.loads(body.decode('utf-8')) if body else {}
            except json.JSONDecodeError:
                return web.Response(text="Invalid JSON payload", status=400)
            
            # Create webhook event
            webhook_event = WebhookEvent(
                source=config.source,
                event_type=self._extract_event_type(config.source, headers),
                payload=payload,
                timestamp=datetime.utcnow(),
                headers=headers,
                signature=headers.get('x-hub-signature-256') or headers.get('x-gitlab-token'),
                verified=True
            )
            
            # Process webhook event
            await self._process_webhook_event(webhook_event)
            
            # Store webhook event in Redis if available
            if self.redis_client:
                await self._store_webhook_event(webhook_event)
            
            return web.Response(text="OK", status=200)
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            return web.Response(text="Internal server error", status=500)
    
    async def _verify_webhook_signature(self, config: WebhookConfig, body: bytes, headers: Dict[str, str]) -> bool:
        """Verify webhook signature based on source"""
        try:
            if config.source == WebhookSource.GITHUB:
                signature = headers.get('x-hub-signature-256', '')
                return self.verifier.verify_github_signature(body, signature, config.secret)
            
            elif config.source == WebhookSource.GITLAB:
                token = headers.get('x-gitlab-token', '')
                return self.verifier.verify_gitlab_signature(body, token, config.secret)
            
            elif config.source == WebhookSource.JENKINS:
                signature = headers.get('x-jenkins-signature', '')
                return self.verifier.verify_jenkins_signature(body, signature, config.secret)
            
            else:
                # For other sources, we might implement different verification methods
                return True
        
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _extract_event_type(self, source: WebhookSource, headers: Dict[str, str]) -> str:
        """Extract event type from headers based on source"""
        if source == WebhookSource.GITHUB:
            return headers.get('x-github-event', 'unknown')
        elif source == WebhookSource.GITLAB:
            return headers.get('x-gitlab-event', 'unknown')
        elif source == WebhookSource.JENKINS:
            return headers.get('x-jenkins-event', 'build')
        else:
            return 'unknown'
    
    async def _process_webhook_event(self, webhook_event: WebhookEvent):
        """Process webhook event and convert to Git events if applicable"""
        try:
            # Convert webhook to GitEvent if possible
            git_event = None
            
            if webhook_event.source == WebhookSource.GITHUB:
                git_event = self.parser.parse_github_webhook(webhook_event.payload, webhook_event.headers)
            elif webhook_event.source == WebhookSource.GITLAB:
                git_event = self.parser.parse_gitlab_webhook(webhook_event.payload, webhook_event.headers)
            elif webhook_event.source == WebhookSource.JENKINS:
                git_event = self.parser.parse_jenkins_webhook(webhook_event.payload, webhook_event.headers)
            
            # If we have a Git event and a Git event detector, emit the event
            if git_event and self.git_event_detector:
                await self.git_event_detector._emit_event(git_event)
            
            # Call registered webhook handlers
            handlers = self.event_handlers.get(webhook_event.source, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(webhook_event)
                    else:
                        handler(webhook_event)
                except Exception as e:
                    self.logger.error(f"Error in webhook handler: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing webhook event: {e}")
    
    async def _store_webhook_event(self, webhook_event: WebhookEvent):
        """Store webhook event in Redis"""
        try:
            if not self.redis_client:
                return
            
            event_data = {
                'source': webhook_event.source.value,
                'event_type': webhook_event.event_type,
                'timestamp': webhook_event.timestamp.isoformat(),
                'webhook_id': webhook_event.webhook_id,
                'verified': webhook_event.verified,
                'payload_size': len(json.dumps(webhook_event.payload))
            }
            
            # Store webhook event
            key = f"webhooks:{webhook_event.source.value}:{webhook_event.webhook_id}"
            await self.redis_client.setex(key, 86400 * 7, json.dumps(event_data))  # 7 days
            
            # Add to webhook stream
            stream_key = f"webhooks:stream:{webhook_event.source.value}"
            await self.redis_client.xadd(stream_key, event_data, maxlen=1000)
            
        except Exception as e:
            self.logger.error(f"Error storing webhook event: {e}")
    
    async def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        stats = {
            'configured_endpoints': len(self.configurations),
            'endpoints': {},
            'handlers_registered': {
                source.value: len(handlers) 
                for source, handlers in self.event_handlers.items()
            }
        }
        
        for endpoint, config in self.configurations.items():
            stats['endpoints'][endpoint] = {
                'source': config.source.value,
                'enabled': config.enabled,
                'verify_signature': config.verify_signature,
                'supported_events': config.supported_events
            }
        
        # Get Redis stats if available
        if self.redis_client:
            try:
                for source in WebhookSource:
                    stream_key = f"webhooks:stream:{source.value}"
                    info = await self.redis_client.xinfo_stream(stream_key)
                    stats[f'{source.value}_events_count'] = info.get('length', 0)
            except Exception as e:
                self.logger.debug(f"Could not get Redis webhook stats: {e}")
        
        return stats
    
    async def get_recent_webhook_events(self, source: Optional[WebhookSource] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent webhook events"""
        events = []
        
        try:
            if not self.redis_client:
                return events
            
            sources_to_check = [source] if source else list(WebhookSource)
            
            for webhook_source in sources_to_check:
                if webhook_source is None:
                    continue
                    
                stream_key = f"webhooks:stream:{webhook_source.value}"
                try:
                    stream_events = await self.redis_client.xrange(stream_key, count=limit)
                    
                    for event_id, event_data in stream_events:
                        events.append({
                            'event_id': event_id,
                            'source': event_data.get('source'),
                            'event_type': event_data.get('event_type'),
                            'timestamp': event_data.get('timestamp'),
                            'webhook_id': event_data.get('webhook_id'),
                            'verified': event_data.get('verified', 'false') == 'true',
                            'payload_size': int(event_data.get('payload_size', 0))
                        })
                except Exception as e:
                    self.logger.debug(f"Could not get events for {webhook_source.value}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error getting recent webhook events: {e}")
        
        # Sort by timestamp and limit
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return events[:limit]


class WebhookServer:
    """HTTP server for handling webhooks"""
    
    def __init__(self, webhook_handler: WebhookHandler, host: str = '0.0.0.0', port: int = 8080):
        """Initialize webhook server"""
        self.webhook_handler = webhook_handler
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.logger = logging.getLogger(__name__)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup webhook routes"""
        # Main webhook handler - catch all webhook endpoints
        self.app.router.add_post('/webhook/{source}', self._route_webhook)
        self.app.router.add_post('/webhook', self._route_webhook)
        
        # Health check endpoint
        self.app.router.add_get('/health', self._health_check)
        
        # Status endpoint
        self.app.router.add_get('/status', self._status_check)
    
    async def _route_webhook(self, request: Request) -> Response:
        """Route webhook requests to handler"""
        return await self.webhook_handler.handle_webhook(request)
    
    async def _health_check(self, request: Request) -> Response:
        """Health check endpoint"""
        return web.Response(text="OK", status=200)
    
    async def _status_check(self, request: Request) -> Response:
        """Status check endpoint with webhook statistics"""
        try:
            stats = await self.webhook_handler.get_webhook_statistics()
            return web.Response(text=json.dumps(stats, indent=2), status=200, content_type='application/json')
        except Exception as e:
            self.logger.error(f"Error getting webhook status: {e}")
            return web.Response(text="Error getting status", status=500)
    
    async def start(self):
        """Start webhook server"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.logger.info(f"Webhook server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Error starting webhook server: {e}")
            raise
    
    async def stop(self):
        """Stop webhook server"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            self.logger.info("Webhook server stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping webhook server: {e}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get webhook server information"""
        return {
            'host': self.host,
            'port': self.port,
            'running': self.site is not None,
            'webhook_endpoints': list(self.webhook_handler.configurations.keys())
        }