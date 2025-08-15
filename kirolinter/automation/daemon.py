"""
Background Daemon for KiroLinter Proactive Automation.

Provides continuous monitoring, intelligent scheduling, and resource-aware
analysis execution for autonomous code quality management.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from threading import Lock

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from git import Repo, InvalidGitRepositoryError
    from git.exc import GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from ..agents.coordinator import CoordinatorAgent
from ..agents.learner import LearnerAgent
from ..memory.pattern_memory import PatternMemory, create_pattern_memory


class AnalysisDaemon:
    """
    Background daemon for continuous code quality monitoring and analysis.
    
    Features:
    - Resource-aware scheduling with CPU and memory monitoring
    - Intelligent interval adjustment based on repository activity
    - Git change detection for targeted analysis
    - Safe execution with error recovery and logging
    - Integration with existing agent system
    """
    
    def __init__(self, repo_path: str, interval_hours: int = 24, 
                 max_cpu_percent: float = 50.0, max_memory_mb: int = 500,
                 verbose: bool = False):
        """
        Initialize the analysis daemon.
        
        Args:
            repo_path: Path to Git repository to monitor
            interval_hours: Base interval between analyses (hours)
            max_cpu_percent: Maximum CPU usage threshold
            max_memory_mb: Maximum memory usage threshold (MB)
            verbose: Enable verbose logging
        """
        self.repo_path = Path(repo_path).resolve()
        self.base_interval_hours = interval_hours
        self.current_interval_hours = interval_hours
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_mb = max_memory_mb
        self.verbose = verbose
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.scheduler = None
        self.coordinator = None
        self.learner = None
        self.pattern_memory = None
        
        # State tracking
        self.is_running = False
        self.last_analysis_time = None
        self.analysis_count = 0
        self.error_count = 0
        self.state_lock = Lock()
        
        # Performance tracking
        self.performance_stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'average_duration': 0.0,
            'last_duration': 0.0,
            'resource_skips': 0
        }
        
        # Priority queue for urgent analyses
        self.priority_queue = []
        
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize daemon components."""
        try:
            if not SCHEDULER_AVAILABLE:
                raise ImportError("APScheduler not available")
            
            # Initialize scheduler
            self.scheduler = BackgroundScheduler(
                job_defaults={'max_instances': 1, 'coalesce': True}
            )
            
            # Initialize agents
            self.coordinator = CoordinatorAgent(verbose=self.verbose)
            self.learner = LearnerAgent(verbose=self.verbose)
            self.pattern_memory = create_pattern_memory()
            
            if self.verbose:
                print(f"🤖 Daemon: Initialized for repository {self.repo_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize daemon components: {e}")
            raise
    
    def start(self) -> bool:
        """
        Start the background daemon.
        
        Returns:
            True if started successfully
        """
        try:
            with self.state_lock:
                if self.is_running:
                    self.logger.warning("Daemon is already running")
                    return True
                
                if not self.scheduler:
                    self.logger.error("Scheduler not initialized")
                    return False
                
                # Schedule periodic analysis
                self.scheduler.add_job(
                    func=self._run_analysis_job,
                    trigger=IntervalTrigger(hours=self.current_interval_hours),
                    id='periodic_analysis',
                    name=f'Periodic Analysis ({self.repo_path})',
                    replace_existing=True
                )
                
                # Schedule resource monitoring
                self.scheduler.add_job(
                    func=self._monitor_resources,
                    trigger=IntervalTrigger(minutes=5),
                    id='resource_monitor',
                    name='Resource Monitor',
                    replace_existing=True
                )
                
                # Schedule activity-based interval adjustment
                self.scheduler.add_job(
                    func=self._adjust_interval_based_on_activity,
                    trigger=CronTrigger(hour=0, minute=0),  # Daily at midnight
                    id='interval_adjustment',
                    name='Interval Adjustment',
                    replace_existing=True
                )
                
                # Schedule priority queue processing
                self.scheduler.add_job(
                    func=self._process_priority_queue,
                    trigger=IntervalTrigger(minutes=10),
                    id='priority_processor',
                    name='Priority Queue Processor',
                    replace_existing=True
                )
                
                # Start scheduler
                self.scheduler.start()
                self.is_running = True
                
                if self.verbose:
                    print(f"🚀 Daemon: Started with {self.current_interval_hours}h interval")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the background daemon.
        
        Returns:
            True if stopped successfully
        """
        try:
            with self.state_lock:
                if not self.is_running:
                    return True
                
                if self.scheduler and self.scheduler.running:
                    self.scheduler.shutdown(wait=True)
                
                self.is_running = False
                
                if self.verbose:
                    print(f"🛑 Daemon: Stopped after {self.analysis_count} analyses")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to stop daemon: {e}")
            return False
    
    def _run_analysis_job(self) -> None:
        """Execute scheduled analysis job."""
        try:
            # Check resource constraints
            if not self._check_resource_availability():
                self.performance_stats['resource_skips'] += 1
                if self.verbose:
                    print("⏸️  Daemon: Skipping analysis due to resource constraints")
                return
            
            # Check if repository has changes
            if not self._has_repository_changes():
                if self.verbose:
                    print("⏸️  Daemon: No changes detected, skipping analysis")
                return
            
            # Run analysis
            start_time = time.time()
            success = self._run_full_analysis()
            duration = time.time() - start_time
            
            # Update statistics
            with self.state_lock:
                self.analysis_count += 1
                self.last_analysis_time = datetime.now()
                self.performance_stats['total_analyses'] += 1
                self.performance_stats['last_duration'] = duration
                
                if success:
                    self.performance_stats['successful_analyses'] += 1
                    self.error_count = 0  # Reset error count on success
                else:
                    self.error_count += 1
                
                # Update average duration
                total_successful = self.performance_stats['successful_analyses']
                if total_successful > 0:
                    current_avg = self.performance_stats['average_duration']
                    self.performance_stats['average_duration'] = (
                        (current_avg * (total_successful - 1) + duration) / total_successful
                    )
            
            if self.verbose:
                status = "✅" if success else "❌"
                print(f"{status} Daemon: Analysis completed in {duration:.2f}s")
            
            # Adjust interval based on success/failure
            if self.error_count >= 3:
                self._increase_interval("Multiple failures detected")
            elif success and duration < 2.0:
                self._consider_decreasing_interval("Fast successful analysis")
                
        except Exception as e:
            self.logger.error(f"Analysis job failed: {e}")
            with self.state_lock:
                self.error_count += 1
                
            # Check if we need to increase interval due to repeated failures
            if self.error_count >= 3:
                self._increase_interval("Multiple failures detected")
    
    def _check_resource_availability(self) -> bool:
        """Check if system resources are available for analysis."""
        if not PSUTIL_AVAILABLE:
            return True  # Assume resources are available if psutil not installed
        
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.max_cpu_percent:
                return False
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.available < (self.max_memory_mb * 1024 * 1024):
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Resource check failed: {e}")
            return True  # Assume available on error
    
    def _has_repository_changes(self) -> bool:
        """Check if repository has changes since last analysis."""
        if not GIT_AVAILABLE:
            return True  # Assume changes if Git not available
        
        try:
            repo = Repo(self.repo_path)
            
            # Check for uncommitted changes
            if repo.is_dirty():
                return True
            
            # Check for new commits since last analysis
            if self.last_analysis_time:
                since_time = self.last_analysis_time - timedelta(hours=1)  # Buffer
                commits = list(repo.iter_commits(since=since_time.isoformat()))
                return len(commits) > 0
            
            return True  # First run, assume changes
            
        except (InvalidGitRepositoryError, GitCommandError) as e:
            self.logger.warning(f"Git check failed: {e}")
            return True  # Assume changes on error
    
    def _run_full_analysis(self) -> bool:
        """Run full analysis workflow."""
        try:
            if not self.coordinator:
                return False
            
            # Execute full review workflow
            result = self.coordinator.execute_workflow(
                "full_review",
                repo_path=str(self.repo_path),
                enable_learning=True
            )
            
            success = result.get("success", False)
            
            if success and self.verbose:
                analysis = result.get("results", {}).get("analysis", {})
                files_analyzed = analysis.get("total_files_analyzed", 0)
                issues_found = analysis.get("total_issues_found", 0)
                print(f"📊 Daemon: Analyzed {files_analyzed} files, found {issues_found} issues")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Full analysis failed: {e}")
            return False
    
    def _monitor_resources(self) -> None:
        """Monitor system resources and adjust behavior."""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Log resource usage if verbose
            if self.verbose and self.analysis_count % 12 == 0:  # Every hour
                print(f"📊 Daemon: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%")
            
            # Adjust interval if resources are consistently high
            if cpu_percent > self.max_cpu_percent * 0.8:  # 80% of threshold
                self._increase_interval("High CPU usage detected")
            
        except Exception as e:
            self.logger.warning(f"Resource monitoring failed: {e}")
    
    def _adjust_interval_based_on_activity(self) -> None:
        """Adjust analysis interval based on repository activity."""
        if not GIT_AVAILABLE:
            return
        
        try:
            repo = Repo(self.repo_path)
            
            # Count commits in the last 24 hours
            since_time = datetime.now() - timedelta(hours=24)
            commits = list(repo.iter_commits(since=since_time.isoformat()))
            commit_count = len(commits)
            
            # Adjust interval based on activity
            if commit_count > 10:
                # High activity - increase frequency
                new_interval = max(1, self.base_interval_hours // 4)
                self._set_interval(new_interval, f"High activity: {commit_count} commits")
            elif commit_count > 5:
                # Medium activity - moderate frequency
                new_interval = max(2, self.base_interval_hours // 2)
                self._set_interval(new_interval, f"Medium activity: {commit_count} commits")
            elif commit_count == 0:
                # No activity - decrease frequency
                new_interval = min(72, self.base_interval_hours * 2)
                self._set_interval(new_interval, "No recent activity")
            else:
                # Normal activity - use base interval
                self._set_interval(self.base_interval_hours, f"Normal activity: {commit_count} commits")
                
        except Exception as e:
            self.logger.warning(f"Activity-based adjustment failed: {e}")
    
    def _increase_interval(self, reason: str) -> None:
        """Increase analysis interval."""
        new_interval = min(72, self.current_interval_hours * 2)
        self._set_interval(new_interval, reason)
    
    def _consider_decreasing_interval(self, reason: str) -> None:
        """Consider decreasing analysis interval."""
        if self.current_interval_hours > self.base_interval_hours:
            new_interval = max(self.base_interval_hours, self.current_interval_hours // 2)
            self._set_interval(new_interval, reason)
    
    def _set_interval(self, new_interval: int, reason: str) -> None:
        """Set new analysis interval."""
        if new_interval == self.current_interval_hours:
            return
        
        try:
            with self.state_lock:
                self.current_interval_hours = new_interval
                
                if self.scheduler and self.is_running:
                    # Reschedule the job
                    self.scheduler.reschedule_job(
                        'periodic_analysis',
                        trigger=IntervalTrigger(hours=new_interval)
                    )
            
            if self.verbose:
                print(f"⏰ Daemon: Interval adjusted to {new_interval}h ({reason})")
                
        except Exception as e:
            self.logger.error(f"Failed to set interval: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get daemon status and statistics."""
        with self.state_lock:
            return {
                "is_running": self.is_running,
                "repo_path": str(self.repo_path),
                "current_interval_hours": self.current_interval_hours,
                "base_interval_hours": self.base_interval_hours,
                "analysis_count": self.analysis_count,
                "error_count": self.error_count,
                "last_analysis_time": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
                "priority_queue_size": len(self.priority_queue),
                "performance_stats": self.performance_stats.copy(),
                "resource_limits": {
                    "max_cpu_percent": self.max_cpu_percent,
                    "max_memory_mb": self.max_memory_mb
                }
            }
    
    def trigger_analysis(self) -> bool:
        """Manually trigger an analysis."""
        if not self.is_running:
            return False
        
        try:
            # Run analysis in background
            if self.scheduler:
                self.scheduler.add_job(
                    func=self._run_analysis_job,
                    id='manual_analysis',
                    name='Manual Analysis',
                    replace_existing=True
                )
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger analysis: {e}")
        
        return False
    
    def _process_priority_queue(self) -> None:
        """Process high-priority analysis requests."""
        try:
            if not self.priority_queue or not self._check_resource_availability():
                return
            
            # Process highest priority item
            priority_item = self.priority_queue.pop(0)
            
            if self.verbose:
                print(f"🔥 Daemon: Processing priority analysis for {priority_item.get('reason', 'unknown')}")
            
            # Run focused analysis
            success = self._run_priority_analysis(priority_item)
            
            if self.verbose:
                status = "✅" if success else "❌"
                print(f"{status} Daemon: Priority analysis complete")
                
        except Exception as e:
            self.logger.error(f"Priority queue processing failed: {e}")
    
    def _run_priority_analysis(self, priority_item: Dict[str, Any]) -> bool:
        """Run priority analysis for specific files or reason."""
        try:
            if not self.coordinator:
                return False
            
            # Get files to focus on
            focus_files = priority_item.get('files', [])
            if not focus_files:
                focus_files = self._get_changed_files()
            
            # Prioritize files based on patterns
            prioritized_files = self._prioritize_files(focus_files)
            
            # Execute targeted analysis
            result = self.coordinator.execute_workflow(
                "priority_analysis",
                repo_path=str(self.repo_path),
                focus_files=prioritized_files[:5],  # Limit to top 5 files
                enable_learning=True
            )
            
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Priority analysis failed: {e}")
            return False
    
    def _get_changed_files(self) -> List[str]:
        """Get list of recently changed Python files."""
        if not GIT_AVAILABLE:
            return []
        
        try:
            repo = Repo(self.repo_path)
            
            # Get files changed in last commit
            if repo.head.commit.parents:
                diff = repo.head.commit.diff(repo.head.commit.parents[0])
                changed_files = [
                    item.b_path for item in diff 
                    if item.b_path and item.b_path.endswith('.py')
                ]
                return changed_files
            
            return []
            
        except Exception as e:
            self.logger.debug(f"Failed to get changed files: {e}")
            return []
    
    def _prioritize_files(self, files: List[str]) -> List[str]:
        """Prioritize files based on historical issue patterns."""
        if not files:
            return []
        
        try:
            # Get issue patterns from memory
            issue_trends = self.pattern_memory.get_issue_trends(str(self.repo_path))
            trending_issues = issue_trends.get('trending_issues', [])
            
            # Create priority scores for files
            file_scores = {}
            for file_path in files:
                score = 0
                
                # Score based on historical issues
                for issue in trending_issues:
                    # Simple heuristic: if file path contains issue context
                    if any(keyword in file_path.lower() for keyword in ['test', 'config', 'main', 'init']):
                        if issue.get('issue_type') in ['security', 'performance']:
                            score += issue.get('frequency', 0) * 2
                        else:
                            score += issue.get('frequency', 0)
                
                # Boost score for certain file types
                if 'test' in file_path.lower():
                    score *= 0.5  # Lower priority for test files
                elif any(pattern in file_path for pattern in ['__init__', 'config', 'settings']):
                    score *= 1.5  # Higher priority for config files
                elif 'main' in file_path.lower() or 'app' in file_path.lower():
                    score *= 2.0  # Highest priority for main application files
                
                file_scores[file_path] = score
            
            # Sort by score (highest first)
            prioritized = sorted(files, key=lambda f: file_scores.get(f, 0), reverse=True)
            
            if self.verbose and prioritized:
                print(f"📊 Daemon: Prioritized {len(prioritized)} files for analysis")
            
            return prioritized
            
        except Exception as e:
            self.logger.error(f"Failed to prioritize files: {e}")
            return files
    
    def add_priority_analysis(self, reason: str, files: Optional[List[str]] = None) -> bool:
        """
        Add a high-priority analysis request to the queue.
        
        Args:
            reason: Reason for priority analysis
            files: Optional list of specific files to analyze
            
        Returns:
            True if added successfully
        """
        try:
            priority_item = {
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "files": files or []
            }
            
            self.priority_queue.append(priority_item)
            
            # Keep queue size manageable
            if len(self.priority_queue) > 10:
                self.priority_queue = self.priority_queue[-10:]
            
            if self.verbose:
                print(f"🔥 Daemon: Added priority analysis: {reason}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add priority analysis: {e}")
            return False