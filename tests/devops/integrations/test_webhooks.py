"""
Tests for Webhook Integration System
"""

import pytest
import asyncio
import json
import hmac
import hashlib
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from kirolinter.devops.integrations.webhooks import (
    WebhookHandler, WebhookServer, WebhookConfig, WebhookEvent, WebhookSource,
    WebhookVerifier, WebhookParser
)
from kirolinter.devops.integrations.git_events import GitEvent, GitEventType


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.xadd = AsyncMock()
    redis_mock.xrange = AsyncMock(return_value=[])
    redis_mock.xinfo_stream = AsyncMock(return_value={'length': 0})
    return redis_mock


@pytest.fixture
def mock_git_event_detector():
    """Mock GitEventDetector"""
    detector = Mock()
    detector._emit_event = AsyncMock()
    return detector


class TestWebhookConfig:
    """Test WebhookConfig class"""
    
    def test_webhook_config_creation(self):
        """Test creating webhook configuration"""
        config = WebhookConfig(
            source=WebhookSource.GITHUB,
            secret="test-secret",
            endpoint_path="/github-webhook"
        )
        
        assert config.source == WebhookSource.GITHUB
        assert config.secret == "test-secret"
        assert config.endpoint_path == "/github-webhook"
        assert config.enabled is True
        assert config.verify_signature is True
        assert 'push' in config.supported_events
        assert 'pull_request' in config.supported_events
    
    def test_webhook_config_default_events(self):
        """Test default supported events for different sources"""
        # GitHub
        github_config = WebhookConfig(source=WebhookSource.GITHUB)
        assert 'push' in github_config.supported_events
        assert 'pull_request' in github_config.supported_events
        
        # GitLab
        gitlab_config = WebhookConfig(source=WebhookSource.GITLAB)
        assert 'push' in gitlab_config.supported_events
        assert 'merge_request' in gitlab_config.supported_events
        
        # Jenkins
        jenkins_config = WebhookConfig(source=WebhookSource.JENKINS)
        assert 'build_started' in jenkins_config.supported_events
        assert 'build_completed' in jenkins_config.supported_events


class TestWebhookEvent:
    """Test WebhookEvent class"""
    
    def test_webhook_event_creation(self):
        """Test creating webhook event"""
        payload = {'test': 'data'}
        headers = {'x-github-event': 'push'}
        
        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type='push',
            payload=payload,
            timestamp=datetime.utcnow(),
            headers=headers
        )
        
        assert event.source == WebhookSource.GITHUB
        assert event.event_type == 'push'
        assert event.payload == payload
        assert event.headers == headers
        assert event.webhook_id is not None
        assert event.verified is False
    
    def test_webhook_event_id_generation(self):
        """Test webhook event ID generation"""
        timestamp = datetime.utcnow()
        
        event1 = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type='push',
            payload={},
            timestamp=timestamp,
            headers={}
        )
        
        event2 = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type='push',
            payload={},
            timestamp=timestamp,
            headers={}
        )
        
        assert event1.webhook_id == event2.webhook_id


class TestWebhookVerifier:
    """Test WebhookVerifier class"""
    
    def test_verify_github_signature_valid(self):
        """Test valid GitHub signature verification"""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        
        # Create expected signature
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature_header = f"sha256={signature}"
        
        result = WebhookVerifier.verify_github_signature(payload, signature_header, secret)
        assert result is True
    
    def test_verify_github_signature_invalid(self):
        """Test invalid GitHub signature verification"""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid"
        
        result = WebhookVerifier.verify_github_signature(payload, invalid_signature, secret)
        assert result is False
    
    def test_verify_github_signature_wrong_format(self):
        """Test GitHub signature with wrong format"""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        wrong_format = "invalid-format"
        
        result = WebhookVerifier.verify_github_signature(payload, wrong_format, secret)
        assert result is False
    
    def test_verify_gitlab_signature_valid(self):
        """Test valid GitLab signature verification"""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        
        result = WebhookVerifier.verify_gitlab_signature(payload, secret, secret)
        assert result is True
    
    def test_verify_gitlab_signature_invalid(self):
        """Test invalid GitLab signature verification"""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        wrong_token = "wrong-token"
        
        result = WebhookVerifier.verify_gitlab_signature(payload, wrong_token, secret)
        assert result is False


class TestWebhookParser:
    """Test WebhookParser class"""
    
    def test_parse_github_push_webhook(self):
        """Test parsing GitHub push webhook"""
        payload = {
            'ref': 'refs/heads/main',
            'after': 'abc123',
            'pusher': {'name': 'testuser'},
            'repository': {'full_name': 'test/repo', 'html_url': 'https://github.com/test/repo'},
            'commits': [
                {
                    'modified': ['file1.py'],
                    'added': ['file2.py']
                }
            ]
        }
        headers = {'x-github-event': 'push'}
        
        event = WebhookParser.parse_github_webhook(payload, headers)
        
        assert event is not None
        assert event.event_type == GitEventType.PUSH
        assert event.repository_path == 'test/repo'
        assert event.branch == 'main'
        assert event.commit_hash == 'abc123'
        assert event.author == 'testuser'
        assert 'file1.py' in event.files_changed
        assert 'file2.py' in event.files_changed
    
    def test_parse_github_pull_request_webhook(self):
        """Test parsing GitHub pull request webhook"""
        payload = {
            'action': 'opened',
            'repository': {'full_name': 'test/repo', 'html_url': 'https://github.com/test/repo'},
            'pull_request': {
                'number': 123,
                'title': 'Test PR',
                'user': {'login': 'testuser'},
                'head': {'ref': 'feature-branch', 'sha': 'abc123'},
                'base': {'ref': 'main'},
                'html_url': 'https://github.com/test/repo/pull/123'
            }
        }
        headers = {'x-github-event': 'pull_request'}
        
        event = WebhookParser.parse_github_webhook(payload, headers)
        
        assert event is not None
        assert event.event_type == GitEventType.PULL_REQUEST
        assert event.repository_path == 'test/repo'
        assert event.branch == 'feature-branch'
        assert event.commit_hash == 'abc123'
        assert event.author == 'testuser'
        assert event.message == 'Test PR'
        assert event.event_data['pr_number'] == 123
        assert event.event_data['action'] == 'opened'
    
    def test_parse_github_create_branch_webhook(self):
        """Test parsing GitHub branch creation webhook"""
        payload = {
            'ref_type': 'branch',
            'ref': 'feature-branch',
            'repository': {'full_name': 'test/repo', 'html_url': 'https://github.com/test/repo'},
            'sender': {'login': 'testuser'}
        }
        headers = {'x-github-event': 'create'}
        
        event = WebhookParser.parse_github_webhook(payload, headers)
        
        assert event is not None
        assert event.event_type == GitEventType.BRANCH_CREATE
        assert event.repository_path == 'test/repo'
        assert event.branch == 'feature-branch'
        assert event.author == 'testuser'
        assert event.event_data['ref_type'] == 'branch'
    
    def test_parse_gitlab_push_webhook(self):
        """Test parsing GitLab push webhook"""
        payload = {
            'ref': 'refs/heads/main',
            'after': 'abc123',
            'before': 'def456',
            'user_name': 'testuser',
            'project': {
                'id': 123,
                'path_with_namespace': 'test/repo',
                'web_url': 'https://gitlab.com/test/repo'
            },
            'commits': [
                {
                    'modified': ['file1.py'],
                    'added': ['file2.py']
                }
            ]
        }
        headers = {'x-gitlab-event': 'Push Hook'}
        
        event = WebhookParser.parse_gitlab_webhook(payload, headers)
        
        assert event is not None
        assert event.event_type == GitEventType.PUSH
        assert event.repository_path == 'test/repo'
        assert event.branch == 'main'
        assert event.commit_hash == 'abc123'
        assert event.author == 'testuser'
        assert 'file1.py' in event.files_changed
        assert 'file2.py' in event.files_changed
    
    def test_parse_invalid_webhook(self):
        """Test parsing invalid webhook payload"""
        payload = {}  # Empty payload
        headers = {'x-github-event': 'unknown'}
        
        event = WebhookParser.parse_github_webhook(payload, headers)
        
        assert event is None


class TestWebhookHandler:
    """Test WebhookHandler class"""
    
    def test_initialization(self, mock_redis, mock_git_event_detector):
        """Test WebhookHandler initialization"""
        handler = WebhookHandler(mock_redis, mock_git_event_detector)
        
        assert handler.redis_client == mock_redis
        assert handler.git_event_detector == mock_git_event_detector
        assert len(handler.configurations) == 0
        assert len(handler.event_handlers) == len(WebhookSource)
    
    def test_add_webhook_config(self, mock_redis):
        """Test adding webhook configuration"""
        handler = WebhookHandler(mock_redis)
        config = WebhookConfig(source=WebhookSource.GITHUB, secret="test-secret")
        
        handler.add_webhook_config("/github", config)
        
        assert "/github" in handler.configurations
        assert handler.configurations["/github"] == config
    
    def test_remove_webhook_config(self, mock_redis):
        """Test removing webhook configuration"""
        handler = WebhookHandler(mock_redis)
        config = WebhookConfig(source=WebhookSource.GITHUB, secret="test-secret")
        
        handler.add_webhook_config("/github", config)
        handler.remove_webhook_config("/github")
        
        assert "/github" not in handler.configurations
    
    def test_register_webhook_handler(self, mock_redis):
        """Test registering webhook handler"""
        handler = WebhookHandler(mock_redis)
        
        def test_handler(event):
            pass
        
        handler.register_webhook_handler(WebhookSource.GITHUB, test_handler)
        
        assert test_handler in handler.event_handlers[WebhookSource.GITHUB]
    
    @pytest.mark.asyncio
    async def test_handle_webhook_success(self, mock_redis, mock_git_event_detector):
        """Test successful webhook handling"""
        handler = WebhookHandler(mock_redis, mock_git_event_detector)
        
        # Add configuration
        config = WebhookConfig(
            source=WebhookSource.GITHUB,
            secret="test-secret",
            verify_signature=False  # Disable signature verification for test
        )
        handler.add_webhook_config("/webhook", config)
        
        # Create mock request
        payload = {
            'ref': 'refs/heads/main',
            'after': 'abc123',
            'pusher': {'name': 'testuser'},
            'repository': {'full_name': 'test/repo', 'html_url': 'https://github.com/test/repo'},
            'commits': []
        }
        
        request = make_mocked_request(
            'POST', '/webhook',
            headers={'x-github-event': 'push'},
            payload=json.dumps(payload).encode()
        )
        request.read = AsyncMock(return_value=json.dumps(payload).encode())
        
        response = await handler.handle_webhook(request)
        
        assert response.status == 200
        assert response.text == "OK"
        mock_git_event_detector._emit_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_webhook_not_configured(self, mock_redis):
        """Test handling webhook for unconfigured endpoint"""
        handler = WebhookHandler(mock_redis)
        
        request = make_mocked_request('POST', '/unknown')
        request.read = AsyncMock(return_value=b'{}')
        
        response = await handler.handle_webhook(request)
        
        assert response.status == 404
        assert "not configured" in response.text
    
    @pytest.mark.asyncio
    async def test_handle_webhook_disabled(self, mock_redis):
        """Test handling webhook for disabled endpoint"""
        handler = WebhookHandler(mock_redis)
        
        config = WebhookConfig(source=WebhookSource.GITHUB, enabled=False)
        handler.add_webhook_config("/webhook", config)
        
        request = make_mocked_request('POST', '/webhook')
        request.read = AsyncMock(return_value=b'{}')
        
        response = await handler.handle_webhook(request)
        
        assert response.status == 403
        assert "disabled" in response.text
    
    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self, mock_redis):
        """Test handling webhook with invalid signature"""
        handler = WebhookHandler(mock_redis)
        
        config = WebhookConfig(
            source=WebhookSource.GITHUB,
            secret="test-secret",
            verify_signature=True
        )
        handler.add_webhook_config("/webhook", config)
        
        request = make_mocked_request(
            'POST', '/webhook',
            headers={'x-hub-signature-256': 'invalid-signature'}
        )
        request.read = AsyncMock(return_value=b'{}')
        
        response = await handler.handle_webhook(request)
        
        assert response.status == 401
        assert "Invalid signature" in response.text
    
    @pytest.mark.asyncio
    async def test_get_webhook_statistics(self, mock_redis):
        """Test getting webhook statistics"""
        handler = WebhookHandler(mock_redis)
        
        # Add some configurations
        config1 = WebhookConfig(source=WebhookSource.GITHUB)
        config2 = WebhookConfig(source=WebhookSource.GITLAB)
        handler.add_webhook_config("/github", config1)
        handler.add_webhook_config("/gitlab", config2)
        
        # Add some handlers
        handler.register_webhook_handler(WebhookSource.GITHUB, lambda x: None)
        
        stats = await handler.get_webhook_statistics()
        
        assert stats['configured_endpoints'] == 2
        assert '/github' in stats['endpoints']
        assert '/gitlab' in stats['endpoints']
        assert stats['handlers_registered']['github'] == 1
        assert stats['handlers_registered']['gitlab'] == 0
    
    @pytest.mark.asyncio
    async def test_get_recent_webhook_events(self, mock_redis):
        """Test getting recent webhook events"""
        handler = WebhookHandler(mock_redis)
        
        # Mock Redis response
        mock_redis.xrange.return_value = [
            ('event1', {
                'source': 'github',
                'event_type': 'push',
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_id': 'test-webhook-1',
                'verified': 'true',
                'payload_size': '100'
            })
        ]
        
        events = await handler.get_recent_webhook_events(WebhookSource.GITHUB)
        
        assert len(events) == 1
        assert events[0]['source'] == 'github'
        assert events[0]['event_type'] == 'push'
        assert events[0]['verified'] is True


class TestWebhookServer:
    """Test WebhookServer class"""
    
    def test_initialization(self, mock_redis):
        """Test WebhookServer initialization"""
        handler = WebhookHandler(mock_redis)
        server = WebhookServer(handler, host='localhost', port=9999)
        
        assert server.webhook_handler == handler
        assert server.host == 'localhost'
        assert server.port == 9999
        assert server.app is not None
    
    def test_get_server_info(self, mock_redis):
        """Test getting server information"""
        handler = WebhookHandler(mock_redis)
        handler.add_webhook_config("/test", WebhookConfig(source=WebhookSource.GITHUB))
        
        server = WebhookServer(handler)
        info = server.get_server_info()
        
        assert info['host'] == '0.0.0.0'
        assert info['port'] == 8080
        assert info['running'] is False
        assert '/test' in info['webhook_endpoints']
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_redis):
        """Test health check endpoint"""
        handler = WebhookHandler(mock_redis)
        server = WebhookServer(handler)
        
        request = make_mocked_request('GET', '/health')
        response = await server._health_check(request)
        
        assert response.status == 200
        assert response.text == "OK"
    
    @pytest.mark.asyncio
    async def test_status_check(self, mock_redis):
        """Test status check endpoint"""
        handler = WebhookHandler(mock_redis)
        handler.add_webhook_config("/test", WebhookConfig(source=WebhookSource.GITHUB))
        
        server = WebhookServer(handler)
        
        request = make_mocked_request('GET', '/status')
        response = await server._status_check(request)
        
        assert response.status == 200
        assert response.content_type == 'application/json'


class TestWebhookIntegration:
    """Integration tests for webhook system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_webhook_processing(self, mock_redis, mock_git_event_detector):
        """Test complete webhook processing flow"""
        handler = WebhookHandler(mock_redis, mock_git_event_detector)
        
        # Track events
        webhook_events = []
        git_events = []
        
        def webhook_handler_func(webhook_event):
            webhook_events.append(webhook_event)
        
        async def git_event_handler_func(git_event):
            git_events.append(git_event)
        
        # Register handlers
        handler.register_webhook_handler(WebhookSource.GITHUB, webhook_handler_func)
        mock_git_event_detector._emit_event.side_effect = git_event_handler_func
        
        # Configure webhook
        config = WebhookConfig(
            source=WebhookSource.GITHUB,
            secret="test-secret",
            verify_signature=False
        )
        handler.add_webhook_config("/github-webhook", config)
        
        # Create GitHub push webhook payload
        payload = {
            'ref': 'refs/heads/main',
            'after': 'abc123def456',
            'pusher': {'name': 'developer'},
            'repository': {
                'full_name': 'test/awesome-project',
                'html_url': 'https://github.com/test/awesome-project'
            },
            'commits': [
                {
                    'id': 'abc123def456',
                    'message': 'Add awesome feature',
                    'author': {'name': 'developer'},
                    'modified': ['src/main.py'],
                    'added': ['src/utils.py']
                }
            ]
        }
        
        # Create mock request
        request = make_mocked_request(
            'POST', '/github-webhook',
            headers={'x-github-event': 'push'},
            payload=json.dumps(payload).encode()
        )
        request.read = AsyncMock(return_value=json.dumps(payload).encode())
        
        # Process webhook
        response = await handler.handle_webhook(request)
        
        # Verify response
        assert response.status == 200
        
        # Verify webhook event was processed
        assert len(webhook_events) == 1
        webhook_event = webhook_events[0]
        assert webhook_event.source == WebhookSource.GITHUB
        assert webhook_event.event_type == 'push'
        assert webhook_event.payload == payload
        
        # Verify Git event was emitted
        mock_git_event_detector._emit_event.assert_called_once()
        
        # Verify Redis storage was attempted
        mock_redis.setex.assert_called()
        mock_redis.xadd.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])