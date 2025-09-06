"""
Tests for Git Event Detection System
"""

import pytest
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import git
import os

from kirolinter.devops.integrations.git_events import (
    GitEventDetector, GitOpsMonitor, GitEvent, GitEventType, GitRepositoryState
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir) / "test_repo"
    repo_path.mkdir()
    
    # Initialize git repo
    repo = git.Repo.init(str(repo_path))
    
    # Configure git user
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    yield str(repo_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.xadd = AsyncMock()
    redis_mock.xrange = AsyncMock(return_value=[])
    return redis_mock


class TestGitEvent:
    """Test GitEvent class"""
    
    def test_git_event_creation(self):
        """Test creating a GitEvent"""
        event = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path="/test/repo",
            timestamp=datetime.utcnow(),
            commit_hash="abc123",
            author="Test User",
            message="Test commit"
        )
        
        assert event.event_type == GitEventType.COMMIT
        assert event.repository_path == "/test/repo"
        assert event.commit_hash == "abc123"
        assert event.author == "Test User"
        assert event.message == "Test commit"
        assert event.event_id is not None
    
    def test_git_event_id_generation(self):
        """Test that event IDs are generated consistently"""
        timestamp = datetime.utcnow()
        
        event1 = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path="/test/repo",
            timestamp=timestamp,
            commit_hash="abc123"
        )
        
        event2 = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path="/test/repo",
            timestamp=timestamp,
            commit_hash="abc123"
        )
        
        assert event1.event_id == event2.event_id


class TestGitRepositoryState:
    """Test GitRepositoryState class"""
    
    def test_repository_state_creation(self):
        """Test creating GitRepositoryState"""
        state = GitRepositoryState(
            repository_path="/test/repo",
            last_commit_hash="abc123",
            tracked_branches=["main", "develop"]
        )
        
        assert state.repository_path == "/test/repo"
        assert state.last_commit_hash == "abc123"
        assert state.tracked_branches == ["main", "develop"]


class TestGitEventDetector:
    """Test GitEventDetector class"""
    
    def test_initialization(self):
        """Test GitEventDetector initialization"""
        detector = GitEventDetector()
        
        assert detector.monitored_repos == {}
        assert detector.polling_interval == 30
        assert not detector.running
        assert len(detector.event_handlers) == len(GitEventType)
    
    def test_add_repository_success(self, temp_git_repo):
        """Test successfully adding a repository"""
        detector = GitEventDetector()
        
        result = detector.add_repository(temp_git_repo)
        
        assert result is True
        assert temp_git_repo in detector.monitored_repos
        
        state = detector.monitored_repos[temp_git_repo]
        assert state.repository_path == temp_git_repo
        assert state.last_commit_hash is not None
        assert state.last_check_timestamp is not None
    
    def test_add_repository_invalid_path(self):
        """Test adding an invalid repository path"""
        detector = GitEventDetector()
        
        result = detector.add_repository("/nonexistent/path")
        
        assert result is False
        assert "/nonexistent/path" not in detector.monitored_repos
    
    def test_add_repository_not_git_repo(self):
        """Test adding a path that's not a Git repository"""
        detector = GitEventDetector()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = detector.add_repository(temp_dir)
            
            assert result is False
            assert temp_dir not in detector.monitored_repos
    
    def test_remove_repository(self, temp_git_repo):
        """Test removing a repository"""
        detector = GitEventDetector()
        detector.add_repository(temp_git_repo)
        
        result = detector.remove_repository(temp_git_repo)
        
        assert result is True
        assert temp_git_repo not in detector.monitored_repos
    
    def test_remove_nonexistent_repository(self):
        """Test removing a repository that wasn't added"""
        detector = GitEventDetector()
        
        result = detector.remove_repository("/nonexistent/path")
        
        assert result is False
    
    def test_register_event_handler(self):
        """Test registering event handlers"""
        detector = GitEventDetector()
        
        def test_handler(event):
            pass
        
        detector.register_event_handler(GitEventType.COMMIT, test_handler)
        
        assert test_handler in detector.event_handlers[GitEventType.COMMIT]
    
    def test_remove_event_handler(self):
        """Test removing event handlers"""
        detector = GitEventDetector()
        
        def test_handler(event):
            pass
        
        detector.register_event_handler(GitEventType.COMMIT, test_handler)
        detector.remove_event_handler(GitEventType.COMMIT, test_handler)
        
        assert test_handler not in detector.event_handlers[GitEventType.COMMIT]
    
    def test_get_monitoring_status(self, temp_git_repo):
        """Test getting monitoring status"""
        detector = GitEventDetector()
        detector.add_repository(temp_git_repo)
        
        status = detector.get_monitoring_status()
        
        assert status['running'] is False
        assert status['monitored_repositories'] == 1
        assert status['polling_interval'] == 30
        assert len(status['repositories']) == 1
        assert status['repositories'][0]['path'] == temp_git_repo
    
    @pytest.mark.asyncio
    async def test_detect_events_new_commit(self, temp_git_repo):
        """Test detecting new commit events"""
        detector = GitEventDetector()
        detector.add_repository(temp_git_repo)
        
        # Get initial state
        state = detector.monitored_repos[temp_git_repo]
        initial_commit = state.last_commit_hash
        
        # Create a new commit
        repo = git.Repo(temp_git_repo)
        test_file = Path(temp_git_repo) / "new_file.txt"
        test_file.write_text("New content")
        repo.index.add(["new_file.txt"])
        repo.index.commit("Add new file")
        
        # Set state to simulate previous check
        state.last_check_timestamp = datetime.utcnow() - timedelta(minutes=5)
        
        # Detect events
        events = await detector._detect_events(temp_git_repo, state)
        
        assert len(events) >= 1
        commit_events = [e for e in events if e.event_type == GitEventType.COMMIT]
        assert len(commit_events) >= 1
        
        commit_event = commit_events[0]
        assert commit_event.repository_path == temp_git_repo
        assert commit_event.commit_hash != initial_commit
        assert commit_event.author is not None
        assert "new_file.txt" in commit_event.files_changed
    
    @pytest.mark.asyncio
    async def test_emit_event(self, mock_redis):
        """Test emitting events"""
        detector = GitEventDetector(mock_redis)
        
        # Create a test handler
        handler_called = False
        
        def test_handler(event):
            nonlocal handler_called
            handler_called = True
            assert event.event_type == GitEventType.COMMIT
        
        detector.register_event_handler(GitEventType.COMMIT, test_handler)
        
        # Create and emit an event
        event = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path="/test/repo",
            timestamp=datetime.utcnow(),
            commit_hash="abc123"
        )
        
        await detector._emit_event(event)
        
        assert handler_called
        mock_redis.setex.assert_called_once()
        mock_redis.xadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_event_handler(self):
        """Test async event handlers"""
        detector = GitEventDetector()
        
        # Create an async test handler
        handler_called = False
        
        async def async_test_handler(event):
            nonlocal handler_called
            handler_called = True
            assert event.event_type == GitEventType.COMMIT
        
        detector.register_event_handler(GitEventType.COMMIT, async_test_handler)
        
        # Create and emit an event
        event = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path="/test/repo",
            timestamp=datetime.utcnow(),
            commit_hash="abc123"
        )
        
        await detector._emit_event(event)
        
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_get_recent_events(self, mock_redis):
        """Test getting recent events from Redis"""
        detector = GitEventDetector(mock_redis)
        
        # Mock Redis response
        mock_redis.xrange.return_value = [
            ('event1', {
                'event_type': 'commit',
                'repository_path': '/test/repo',
                'timestamp': datetime.utcnow().isoformat(),
                'event_data': '{}',
                'commit_hash': 'abc123',
                'author': 'Test User',
                'message': 'Test commit',
                'files_changed': '[]',
                'event_id': 'test-event-1'
            })
        ]
        
        events = await detector.get_recent_events('/test/repo')
        
        assert len(events) == 1
        assert events[0].event_type == GitEventType.COMMIT
        assert events[0].repository_path == '/test/repo'
        assert events[0].commit_hash == 'abc123'
    
    def test_stop_monitoring(self):
        """Test stopping monitoring"""
        detector = GitEventDetector()
        detector.running = True
        
        detector.stop_monitoring()
        
        assert detector.running is False


class TestGitOpsMonitor:
    """Test GitOpsMonitor class"""
    
    def test_initialization(self):
        """Test GitOpsMonitor initialization"""
        workflow_engine = Mock()
        redis_client = Mock()
        
        monitor = GitOpsMonitor(redis_client, workflow_engine)
        
        assert monitor.event_detector is not None
        assert monitor.workflow_engine == workflow_engine
        assert monitor.redis_client == redis_client
    
    @pytest.mark.asyncio
    async def test_add_repository(self, temp_git_repo):
        """Test adding repository to GitOps monitor"""
        monitor = GitOpsMonitor()
        
        result = await monitor.add_repository(temp_git_repo)
        
        assert result is True
        assert temp_git_repo in monitor.event_detector.monitored_repos
    
    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, temp_git_repo):
        """Test getting GitOps monitoring status"""
        workflow_engine = Mock()
        redis_client = Mock()
        monitor = GitOpsMonitor(redis_client, workflow_engine)
        
        await monitor.add_repository(temp_git_repo)
        status = await monitor.get_monitoring_status()
        
        assert status['gitops_enabled'] is True
        assert status['workflow_engine_connected'] is True
        assert status['redis_connected'] is True
        assert status['monitored_repositories'] == 1
    
    def test_stop_monitoring(self):
        """Test stopping GitOps monitoring"""
        monitor = GitOpsMonitor()
        monitor.event_detector.running = True
        
        monitor.stop_monitoring()
        
        assert monitor.event_detector.running is False


class TestGitEventDetectorIntegration:
    """Integration tests for GitEventDetector"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self, temp_git_repo, mock_redis):
        """Test complete monitoring cycle with real Git operations"""
        detector = GitEventDetector(mock_redis)
        detector.add_repository(temp_git_repo)
        
        # Track events
        events_detected = []
        
        def event_handler(event):
            events_detected.append(event)
        
        detector.register_event_handler(GitEventType.COMMIT, event_handler)
        detector.register_event_handler(GitEventType.BRANCH_CREATE, event_handler)
        
        # Create new branch
        repo = git.Repo(temp_git_repo)
        new_branch = repo.create_head("feature-branch")
        new_branch.checkout()
        
        # Create new commit
        test_file = Path(temp_git_repo) / "feature.py"
        test_file.write_text("def feature(): pass")
        repo.index.add(["feature.py"])
        repo.index.commit("Add feature")
        
        # Set last check timestamp to capture events
        state = detector.monitored_repos[temp_git_repo]
        state.last_check_timestamp = datetime.utcnow() - timedelta(minutes=5)
        
        # Check for events
        await detector._check_repositories()
        
        # Should have detected branch creation and commit
        assert len(events_detected) >= 1
        
        # Check event types
        event_types = {event.event_type for event in events_detected}
        assert GitEventType.COMMIT in event_types or GitEventType.BRANCH_CREATE in event_types
    
    @pytest.mark.asyncio
    async def test_monitoring_with_workflow_engine(self, temp_git_repo):
        """Test GitOps monitoring with workflow engine integration"""
        workflow_engine = AsyncMock()
        workflow_engine.generate_dynamic_workflow = AsyncMock()
        workflow_engine.create_workflow = AsyncMock(return_value="workflow-123")
        workflow_engine.execute_workflow = AsyncMock()
        
        monitor = GitOpsMonitor(workflow_engine=workflow_engine)
        await monitor.add_repository(temp_git_repo)
        
        # Create a commit to trigger workflow
        repo = git.Repo(temp_git_repo)
        test_file = Path(temp_git_repo) / "trigger.py"
        test_file.write_text("# Trigger workflow")
        repo.index.add(["trigger.py"])
        commit = repo.index.commit("Trigger workflow")
        
        # Simulate event detection
        event = GitEvent(
            event_type=GitEventType.COMMIT,
            repository_path=temp_git_repo,
            timestamp=datetime.utcnow(),
            commit_hash=commit.hexsha,
            author="Test User",
            files_changed=["trigger.py"]
        )
        
        # Process event through the default handler
        handlers = monitor.event_detector.event_handlers[GitEventType.COMMIT]
        if handlers:
            await handlers[0](event)
        
        # Verify workflow was triggered
        workflow_engine.generate_dynamic_workflow.assert_called_once()
        workflow_engine.create_workflow.assert_called_once()
        workflow_engine.execute_workflow.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])