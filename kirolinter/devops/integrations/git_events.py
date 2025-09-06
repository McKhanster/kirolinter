"""
Git Event Detection System

Monitors Git repositories for events like commits, pushes, merges, and branches
to trigger appropriate DevOps workflows automatically.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import git
import hashlib
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class GitEventType(Enum):
    """Git event types"""
    COMMIT = "commit"
    PUSH = "push"
    BRANCH_CREATE = "branch_create"
    BRANCH_DELETE = "branch_delete"
    MERGE = "merge"
    TAG_CREATE = "tag_create"
    TAG_DELETE = "tag_delete"
    PULL_REQUEST = "pull_request"
    FORK = "fork"


@dataclass
class GitEvent:
    """Represents a Git event"""
    event_type: GitEventType
    repository_path: str
    timestamp: datetime
    event_data: Dict[str, Any] = field(default_factory=dict)
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    event_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate event ID if not provided"""
        if not self.event_id:
            data_str = f"{self.event_type.value}-{self.repository_path}-{self.timestamp}-{self.commit_hash}"
            self.event_id = hashlib.md5(data_str.encode()).hexdigest()[:16]


@dataclass
class GitRepositoryState:
    """Tracks the current state of a Git repository"""
    repository_path: str
    last_commit_hash: Optional[str] = None
    last_check_timestamp: Optional[datetime] = None
    tracked_branches: List[str] = field(default_factory=list)
    last_event_id: Optional[str] = None


class GitEventDetector:
    """Detects Git events by monitoring repository state changes"""
    
    def __init__(self, redis_client=None):
        """Initialize Git event detector"""
        self.redis_client = redis_client
        self.monitored_repos: Dict[str, GitRepositoryState] = {}
        self.event_handlers: Dict[GitEventType, List[Callable]] = {
            event_type: [] for event_type in GitEventType
        }
        self.polling_interval = 30  # seconds
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def add_repository(self, repository_path: str, branches: Optional[List[str]] = None) -> bool:
        """Add a repository to monitor"""
        try:
            repo_path = Path(repository_path).resolve()
            if not repo_path.exists() or not (repo_path / '.git').exists():
                self.logger.error(f"Invalid Git repository: {repository_path}")
                return False
            
            repo = git.Repo(str(repo_path))
            current_commit = repo.head.commit.hexsha if repo.head.is_valid() else None
            
            # Default to tracking all branches if none specified
            if branches is None:
                branches = [branch.name for branch in repo.branches]
            
            state = GitRepositoryState(
                repository_path=str(repo_path),
                last_commit_hash=current_commit,
                last_check_timestamp=datetime.utcnow(),
                tracked_branches=branches
            )
            
            self.monitored_repos[str(repo_path)] = state
            self.logger.info(f"Added repository for monitoring: {repository_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add repository {repository_path}: {e}")
            return False
    
    def remove_repository(self, repository_path: str) -> bool:
        """Remove a repository from monitoring"""
        repo_path = str(Path(repository_path).resolve())
        if repo_path in self.monitored_repos:
            del self.monitored_repos[repo_path]
            self.logger.info(f"Removed repository from monitoring: {repository_path}")
            return True
        return False
    
    def register_event_handler(self, event_type: GitEventType, handler: Callable[[GitEvent], None]):
        """Register a handler for specific Git events"""
        self.event_handlers[event_type].append(handler)
        self.logger.info(f"Registered handler for {event_type.value} events")
    
    def remove_event_handler(self, event_type: GitEventType, handler: Callable[[GitEvent], None]):
        """Remove an event handler"""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    async def start_monitoring(self):
        """Start monitoring repositories for Git events"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Started Git event monitoring")
        
        while self.running:
            try:
                await self._check_repositories()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                self.logger.error(f"Error during monitoring: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    def stop_monitoring(self):
        """Stop monitoring repositories"""
        self.running = False
        self.logger.info("Stopped Git event monitoring")
    
    async def _check_repositories(self):
        """Check all monitored repositories for changes"""
        for repo_path, state in self.monitored_repos.items():
            try:
                events = await self._detect_events(repo_path, state)
                for event in events:
                    await self._emit_event(event)
            except Exception as e:
                self.logger.error(f"Error checking repository {repo_path}: {e}")
    
    async def _detect_events(self, repository_path: str, state: GitRepositoryState) -> List[GitEvent]:
        """Detect events in a specific repository"""
        events = []
        
        try:
            repo = git.Repo(repository_path)
            current_time = datetime.utcnow()
            
            # Check for new commits
            for branch_name in state.tracked_branches:
                try:
                    branch = repo.heads[branch_name]
                    current_commit = branch.commit
                    
                    # If there are new commits (different from last known)
                    if state.last_commit_hash != current_commit.hexsha:
                        
                        # For testing, just detect the latest commit
                        # In production, you might want to get all commits since last check
                        new_commits = [current_commit]
                        
                        for commit in new_commits:
                            # Get changed files
                            files_changed = []
                            try:
                                if commit.parents:
                                    diff = commit.parents[0].diff(commit)
                                    files_changed = [item.a_path or item.b_path for item in diff]
                            except:
                                pass  # Handle commits with no parents (initial commit)
                            
                            event = GitEvent(
                                event_type=GitEventType.COMMIT,
                                repository_path=repository_path,
                                timestamp=datetime.fromtimestamp(commit.committed_date),
                                branch=branch_name,
                                commit_hash=commit.hexsha,
                                author=str(commit.author),
                                message=commit.message.strip(),
                                files_changed=files_changed,
                                event_data={
                                    'stats': commit.stats.total,
                                    'parent_count': len(commit.parents)
                                }
                            )
                            events.append(event)
                    
                except git.exc.GitCommandError as e:
                    if "does not exist" not in str(e):
                        self.logger.warning(f"Error accessing branch {branch_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing branch {branch_name}: {e}")
            
            # Check for new branches
            current_branches = set(branch.name for branch in repo.branches)
            previous_branches = set(state.tracked_branches)
            
            new_branches = current_branches - previous_branches
            for branch_name in new_branches:
                event = GitEvent(
                    event_type=GitEventType.BRANCH_CREATE,
                    repository_path=repository_path,
                    timestamp=current_time,
                    branch=branch_name,
                    event_data={'branch_name': branch_name}
                )
                events.append(event)
            
            deleted_branches = previous_branches - current_branches
            for branch_name in deleted_branches:
                event = GitEvent(
                    event_type=GitEventType.BRANCH_DELETE,
                    repository_path=repository_path,
                    timestamp=current_time,
                    branch=branch_name,
                    event_data={'branch_name': branch_name}
                )
                events.append(event)
            
            # Check for new tags
            try:
                current_tags = set(tag.name for tag in repo.tags)
                # Simple tag detection (could be enhanced with stored state)
                if hasattr(state, 'tracked_tags'):
                    previous_tags = set(state.tracked_tags)
                    new_tags = current_tags - previous_tags
                    
                    for tag_name in new_tags:
                        tag = repo.tags[tag_name]
                        event = GitEvent(
                            event_type=GitEventType.TAG_CREATE,
                            repository_path=repository_path,
                            timestamp=current_time,
                            commit_hash=tag.commit.hexsha,
                            event_data={
                                'tag_name': tag_name,
                                'tag_message': getattr(tag.tag, 'message', '') if hasattr(tag, 'tag') else ''
                            }
                        )
                        events.append(event)
                
                # Store current tags for next check
                state.tracked_tags = list(current_tags)
            except Exception as e:
                self.logger.debug(f"Error checking tags: {e}")
            
            # Update repository state
            if repo.head.is_valid():
                state.last_commit_hash = repo.head.commit.hexsha
            state.last_check_timestamp = current_time
            state.tracked_branches = list(current_branches)
            
        except Exception as e:
            self.logger.error(f"Error detecting events in {repository_path}: {e}")
        
        return events
    
    async def _emit_event(self, event: GitEvent):
        """Emit a Git event to registered handlers"""
        try:
            # Store event in Redis if available
            if self.redis_client:
                await self._store_event_in_redis(event)
            
            # Call registered handlers
            handlers = self.event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
            
            self.logger.info(f"Emitted {event.event_type.value} event for {event.repository_path}")
            
        except Exception as e:
            self.logger.error(f"Error emitting event: {e}")
    
    async def _store_event_in_redis(self, event: GitEvent):
        """Store Git event in Redis for persistence"""
        try:
            if not self.redis_client:
                return
            
            event_data = {
                'event_type': event.event_type.value,
                'repository_path': event.repository_path,
                'timestamp': event.timestamp.isoformat(),
                'event_data': event.event_data,
                'branch': event.branch,
                'commit_hash': event.commit_hash,
                'author': event.author,
                'message': event.message,
                'files_changed': event.files_changed,
                'event_id': event.event_id
            }
            
            # Store in Redis with expiration
            key = f"git_events:{event.event_id}"
            await self.redis_client.setex(key, 86400 * 30, json.dumps(event_data))  # 30 days
            
            # Add to event stream
            stream_key = f"git_events:stream:{event.repository_path}"
            await self.redis_client.xadd(stream_key, event_data, maxlen=1000)
            
        except Exception as e:
            self.logger.error(f"Error storing event in Redis: {e}")
    
    async def get_recent_events(self, repository_path: Optional[str] = None, 
                              event_type: Optional[GitEventType] = None,
                              limit: int = 50) -> List[GitEvent]:
        """Get recent Git events"""
        events = []
        
        try:
            if not self.redis_client:
                return events
            
            if repository_path:
                stream_key = f"git_events:stream:{repository_path}"
                stream_events = await self.redis_client.xrange(stream_key, count=limit)
                
                for event_id, event_data in stream_events:
                    if event_type and event_data.get('event_type') != event_type.value:
                        continue
                    
                    event = GitEvent(
                        event_type=GitEventType(event_data['event_type']),
                        repository_path=event_data['repository_path'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        event_data=json.loads(event_data.get('event_data', '{}')),
                        branch=event_data.get('branch'),
                        commit_hash=event_data.get('commit_hash'),
                        author=event_data.get('author'),
                        message=event_data.get('message'),
                        files_changed=json.loads(event_data.get('files_changed', '[]')),
                        event_id=event_data.get('event_id')
                    )
                    events.append(event)
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
        
        return events[:limit]
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            'running': self.running,
            'monitored_repositories': len(self.monitored_repos),
            'repositories': [
                {
                    'path': state.repository_path,
                    'last_commit': state.last_commit_hash,
                    'last_check': state.last_check_timestamp.isoformat() if state.last_check_timestamp else None,
                    'tracked_branches': state.tracked_branches
                }
                for state in self.monitored_repos.values()
            ],
            'polling_interval': self.polling_interval,
            'registered_handlers': {
                event_type.value: len(handlers) 
                for event_type, handlers in self.event_handlers.items()
            }
        }


class GitOpsMonitor:
    """High-level GitOps monitoring system"""
    
    def __init__(self, redis_client=None, workflow_engine=None):
        """Initialize GitOps monitor"""
        self.event_detector = GitEventDetector(redis_client)
        self.workflow_engine = workflow_engine
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Register default event handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers for GitOps workflows"""
        
        async def handle_commit_event(event: GitEvent):
            """Handle commit events"""
            self.logger.info(f"Commit detected: {event.commit_hash[:8]} by {event.author}")
            
            # Trigger appropriate workflow based on branch and files changed
            if self.workflow_engine:
                workflow_context = {
                    'trigger': 'git_commit',
                    'repository': event.repository_path,
                    'branch': event.branch,
                    'commit': event.commit_hash,
                    'files_changed': event.files_changed,
                    'author': event.author
                }
                
                # Create workflow based on context
                workflow_def = await self.workflow_engine.generate_dynamic_workflow(
                    code_changes={
                        'files_modified': len(event.files_changed),
                        'test_files_modified': sum(1 for f in event.files_changed if 'test' in f.lower())
                    },
                    context=workflow_context
                )
                
                # Execute workflow
                workflow_id = await self.workflow_engine.create_workflow(workflow_def)
                await self.workflow_engine.execute_workflow(workflow_id, workflow_context)
        
        async def handle_branch_event(event: GitEvent):
            """Handle branch creation/deletion events"""
            self.logger.info(f"Branch {event.event_type.value}: {event.branch}")
            
            # You could trigger branch-specific workflows here
            # For example, create deployment environments for new feature branches
        
        async def handle_merge_event(event: GitEvent):
            """Handle merge events"""
            self.logger.info(f"Merge detected: {event.commit_hash[:8]}")
            
            # Trigger deployment workflows for merges to main branches
            if event.branch in ['main', 'master', 'production']:
                self.logger.info(f"Production merge detected - triggering deployment workflow")
                # Trigger deployment workflow
        
        # Register handlers
        self.event_detector.register_event_handler(GitEventType.COMMIT, handle_commit_event)
        self.event_detector.register_event_handler(GitEventType.BRANCH_CREATE, handle_branch_event)
        self.event_detector.register_event_handler(GitEventType.BRANCH_DELETE, handle_branch_event)
        self.event_detector.register_event_handler(GitEventType.MERGE, handle_merge_event)
    
    async def add_repository(self, repository_path: str, branches: Optional[List[str]] = None) -> bool:
        """Add repository to GitOps monitoring"""
        return self.event_detector.add_repository(repository_path, branches)
    
    async def start_monitoring(self):
        """Start GitOps monitoring"""
        await self.event_detector.start_monitoring()
    
    def stop_monitoring(self):
        """Stop GitOps monitoring"""
        self.event_detector.stop_monitoring()
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get GitOps monitoring status"""
        base_status = self.event_detector.get_monitoring_status()
        
        # Add GitOps-specific information
        base_status.update({
            'gitops_enabled': True,
            'workflow_engine_connected': self.workflow_engine is not None,
            'redis_connected': self.redis_client is not None
        })
        
        return base_status