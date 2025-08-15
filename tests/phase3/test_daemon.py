"""
Tests for Background Analysis Daemon (Phase 3).

Tests the AnalysisDaemon with scheduling, resource management,
priority queues, and intelligent file prioritization.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from kirolinter.automation.daemon import AnalysisDaemon


class TestAnalysisDaemon:
    """Test AnalysisDaemon functionality."""
    
    @pytest.fixture
    def temp_repo_dir(self):
        """Create temporary repository directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_daemon(self, temp_repo_dir):
        """Create AnalysisDaemon instance with mocked dependencies."""
        with patch('kirolinter.automation.daemon.SCHEDULER_AVAILABLE', True), \
             patch('kirolinter.automation.daemon.PSUTIL_AVAILABLE', True), \
             patch('kirolinter.automation.daemon.GIT_AVAILABLE', True):
            
            daemon = AnalysisDaemon(
                repo_path=temp_repo_dir,
                interval_hours=1,
                verbose=False
            )
            
            # Mock components
            daemon.coordinator = Mock()
            daemon.learner = Mock()
            daemon.pattern_memory = Mock()
            
            return daemon
    
    def test_daemon_initialization(self, temp_repo_dir):
        """Test daemon initialization with proper components."""
        with patch('kirolinter.automation.daemon.SCHEDULER_AVAILABLE', True):
            daemon = AnalysisDaemon(temp_repo_dir, interval_hours=2, verbose=True)
            
            assert daemon.repo_path.name == os.path.basename(temp_repo_dir)
            assert daemon.base_interval_hours == 2
            assert daemon.current_interval_hours == 2
            assert daemon.verbose is True
            assert not daemon.is_running
            assert daemon.analysis_count == 0
            assert daemon.priority_queue == []
    
    def test_daemon_start_stop(self, mock_daemon):
        """Test daemon start and stop functionality."""
        # Mock scheduler
        mock_scheduler = Mock()
        mock_daemon.scheduler = mock_scheduler
        
        # Test start
        success = mock_daemon.start()
        assert success
        assert mock_daemon.is_running
        
        # Verify scheduler jobs were added
        assert mock_scheduler.add_job.call_count >= 3  # periodic, resource, priority
        mock_scheduler.start.assert_called_once()
        
        # Test stop
        success = mock_daemon.stop()
        assert success
        assert not mock_daemon.is_running
        mock_scheduler.shutdown.assert_called_once_with(wait=True)
    
    def test_resource_availability_checking(self, mock_daemon):
        """Test resource availability checking."""
        with patch('kirolinter.automation.daemon.psutil') as mock_psutil:
            # Test sufficient resources
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
            
            available = mock_daemon._check_resource_availability()
            assert available is True
            
            # Test insufficient CPU
            mock_psutil.cpu_percent.return_value = 80.0
            available = mock_daemon._check_resource_availability()
            assert available is False
            
            # Test insufficient memory
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value.available = 100 * 1024 * 1024  # 100MB
            available = mock_daemon._check_resource_availability()
            assert available is False
    
    def test_repository_change_detection(self, mock_daemon):
        """Test repository change detection."""
        with patch('kirolinter.automation.daemon.Repo') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Test dirty repository (uncommitted changes)
            mock_repo.is_dirty.return_value = True
            has_changes = mock_daemon._has_repository_changes()
            assert has_changes is True
            
            # Test clean repository with new commits
            mock_repo.is_dirty.return_value = False
            mock_commit = Mock()
            mock_repo.iter_commits.return_value = [mock_commit]
            mock_daemon.last_analysis_time = datetime.now() - timedelta(hours=2)
            
            has_changes = mock_daemon._has_repository_changes()
            assert has_changes is True
            
            # Test clean repository with no new commits
            mock_repo.iter_commits.return_value = []
            has_changes = mock_daemon._has_repository_changes()
            assert has_changes is False
    
    def test_analysis_job_execution(self, mock_daemon):
        """Test analysis job execution with resource checking."""
        # Mock resource availability
        mock_daemon._check_resource_availability = Mock(return_value=True)
        mock_daemon._has_repository_changes = Mock(return_value=True)
        mock_daemon._run_full_analysis = Mock(return_value=True)
        
        # Run analysis job
        mock_daemon._run_analysis_job()
        
        # Verify calls
        mock_daemon._check_resource_availability.assert_called_once()
        mock_daemon._has_repository_changes.assert_called_once()
        mock_daemon._run_full_analysis.assert_called_once()
        
        # Verify statistics updated
        assert mock_daemon.analysis_count == 1
        assert mock_daemon.last_analysis_time is not None
        assert mock_daemon.performance_stats['total_analyses'] == 1
        assert mock_daemon.performance_stats['successful_analyses'] == 1
    
    def test_analysis_job_resource_constraints(self, mock_daemon):
        """Test analysis job skipping due to resource constraints."""
        # Mock insufficient resources
        mock_daemon._check_resource_availability = Mock(return_value=False)
        mock_daemon._run_full_analysis = Mock()
        
        # Run analysis job
        mock_daemon._run_analysis_job()
        
        # Verify analysis was skipped
        mock_daemon._run_full_analysis.assert_not_called()
        assert mock_daemon.performance_stats['resource_skips'] == 1
    
    def test_interval_adjustment_based_on_activity(self, mock_daemon):
        """Test interval adjustment based on repository activity."""
        with patch('kirolinter.automation.daemon.Repo') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Mock high activity (>10 commits)
            mock_commits = [Mock() for _ in range(15)]
            mock_repo.iter_commits.return_value = mock_commits
            
            mock_daemon._set_interval = Mock()
            mock_daemon._adjust_interval_based_on_activity()
            
            # Should set to 1/4 of base interval
            expected_interval = max(1, mock_daemon.base_interval_hours // 4)
            mock_daemon._set_interval.assert_called_with(expected_interval, "High activity: 15 commits")
            
            # Mock no activity
            mock_repo.iter_commits.return_value = []
            mock_daemon._adjust_interval_based_on_activity()
            
            # Should increase interval
            expected_interval = min(72, mock_daemon.base_interval_hours * 2)
            mock_daemon._set_interval.assert_called_with(expected_interval, "No recent activity")
    
    def test_priority_queue_functionality(self, mock_daemon):
        """Test priority queue addition and processing."""
        # Add priority analysis
        success = mock_daemon.add_priority_analysis("security_issue", ["file1.py", "file2.py"])
        assert success
        assert len(mock_daemon.priority_queue) == 1
        
        priority_item = mock_daemon.priority_queue[0]
        assert priority_item["reason"] == "security_issue"
        assert priority_item["files"] == ["file1.py", "file2.py"]
        assert "timestamp" in priority_item
        
        # Test queue size limit
        for i in range(15):
            mock_daemon.add_priority_analysis(f"issue_{i}")
        
        assert len(mock_daemon.priority_queue) <= 10  # Should be capped
    
    def test_priority_queue_processing(self, mock_daemon):
        """Test priority queue processing."""
        # Add priority item
        mock_daemon.add_priority_analysis("urgent_fix", ["critical.py"])
        
        # Mock dependencies
        mock_daemon._check_resource_availability = Mock(return_value=True)
        mock_daemon._run_priority_analysis = Mock(return_value=True)
        
        # Process queue
        mock_daemon._process_priority_queue()
        
        # Verify processing
        mock_daemon._run_priority_analysis.assert_called_once()
        assert len(mock_daemon.priority_queue) == 0  # Item should be removed
    
    def test_file_prioritization(self, mock_daemon):
        """Test intelligent file prioritization."""
        files = ["main.py", "test_main.py", "config.py", "utils.py"]
        
        # Mock pattern memory
        mock_daemon.pattern_memory.get_issue_trends.return_value = {
            "trending_issues": [
                {"issue_type": "security", "frequency": 10},
                {"issue_type": "style", "frequency": 5}
            ]
        }
        
        prioritized = mock_daemon._prioritize_files(files)
        
        # Should prioritize main.py and config.py over test files
        assert "main.py" in prioritized[:2]  # Should be high priority
        assert "config.py" in prioritized[:2]  # Should be high priority
        assert prioritized.index("test_main.py") > prioritized.index("main.py")  # Test files lower priority
    
    def test_changed_files_detection(self, mock_daemon):
        """Test detection of changed Python files."""
        with patch('kirolinter.automation.daemon.Repo') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Mock diff with Python files
            mock_diff_item1 = Mock()
            mock_diff_item1.b_path = "changed_file.py"
            mock_diff_item2 = Mock()
            mock_diff_item2.b_path = "other_file.txt"
            mock_diff_item3 = Mock()
            mock_diff_item3.b_path = "another.py"
            
            mock_commit = Mock()
            mock_commit.parents = [Mock()]  # Has parent commit
            mock_repo.head.commit = mock_commit
            mock_commit.diff.return_value = [mock_diff_item1, mock_diff_item2, mock_diff_item3]
            
            changed_files = mock_daemon._get_changed_files()
            
            # Should only return Python files
            assert "changed_file.py" in changed_files
            assert "another.py" in changed_files
            assert "other_file.txt" not in changed_files
            assert len(changed_files) == 2
    
    def test_full_analysis_execution(self, mock_daemon):
        """Test full analysis workflow execution."""
        # Mock coordinator
        mock_daemon.coordinator.execute_workflow.return_value = {
            "success": True,
            "results": {
                "analysis": {
                    "total_files_analyzed": 5,
                    "total_issues_found": 3
                }
            }
        }
        
        success = mock_daemon._run_full_analysis()
        assert success
        
        # Verify coordinator was called
        mock_daemon.coordinator.execute_workflow.assert_called_once_with(
            "full_review",
            repo_path=str(mock_daemon.repo_path),
            enable_learning=True
        )
    
    def test_manual_analysis_trigger(self, mock_daemon):
        """Test manual analysis triggering."""
        # Mock scheduler
        mock_scheduler = Mock()
        mock_daemon.scheduler = mock_scheduler
        mock_daemon.is_running = True
        
        success = mock_daemon.trigger_analysis()
        assert success
        
        # Verify manual analysis job was added
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]['id'] == 'manual_analysis'
        assert call_args[1]['name'] == 'Manual Analysis'
    
    def test_daemon_status_reporting(self, mock_daemon):
        """Test comprehensive status reporting."""
        # Set up some state
        mock_daemon.is_running = True
        mock_daemon.analysis_count = 5
        mock_daemon.error_count = 1
        mock_daemon.last_analysis_time = datetime.now()
        mock_daemon.add_priority_analysis("test")
        
        status = mock_daemon.get_status()
        
        # Verify status fields
        assert status["is_running"] is True
        assert status["analysis_count"] == 5
        assert status["error_count"] == 1
        assert status["priority_queue_size"] == 1
        assert "last_analysis_time" in status
        assert "performance_stats" in status
        assert "resource_limits" in status
        
        # Verify performance stats structure
        perf_stats = status["performance_stats"]
        assert "total_analyses" in perf_stats
        assert "successful_analyses" in perf_stats
        assert "average_duration" in perf_stats
        assert "resource_skips" in perf_stats
    
    def test_error_handling_and_recovery(self, mock_daemon):
        """Test error handling and recovery mechanisms."""
        # Mock analysis failure
        mock_daemon._check_resource_availability = Mock(return_value=True)
        mock_daemon._has_repository_changes = Mock(return_value=True)
        mock_daemon._run_full_analysis = Mock(side_effect=Exception("Analysis failed"))
        
        # Run analysis job (should handle exception)
        mock_daemon._run_analysis_job()
        
        # Verify error was handled gracefully
        assert mock_daemon.error_count == 1
        # Analysis count may not be incremented on exception
        
        # Test multiple failures trigger interval increase
        mock_daemon.error_count = 3
        mock_daemon._increase_interval = Mock()
        mock_daemon._run_analysis_job()
        
        mock_daemon._increase_interval.assert_called_once()
    
    def test_resource_monitoring(self, mock_daemon):
        """Test resource monitoring and adjustment."""
        with patch('kirolinter.automation.daemon.psutil') as mock_psutil:
            # Mock high CPU usage
            mock_psutil.cpu_percent.return_value = 85.0  # Above 80% of 70% threshold
            mock_psutil.virtual_memory.return_value.percent = 50.0
            
            mock_daemon._increase_interval = Mock()
            mock_daemon._monitor_resources()
            
            # Should trigger interval increase
            mock_daemon._increase_interval.assert_called_once_with("High CPU usage detected")
    
    def test_daemon_without_optional_dependencies(self, temp_repo_dir):
        """Test daemon behavior when optional dependencies are unavailable."""
        with patch('kirolinter.automation.daemon.SCHEDULER_AVAILABLE', False):
            with pytest.raises(ImportError, match="APScheduler"):
                AnalysisDaemon(temp_repo_dir)
        
        # Test with missing psutil
        with patch('kirolinter.automation.daemon.SCHEDULER_AVAILABLE', True), \
             patch('kirolinter.automation.daemon.PSUTIL_AVAILABLE', False):
            
            daemon = AnalysisDaemon(temp_repo_dir)
            # Should assume resources are available
            assert daemon._check_resource_availability() is True
        
        # Test with missing Git
        with patch('kirolinter.automation.daemon.SCHEDULER_AVAILABLE', True), \
             patch('kirolinter.automation.daemon.GIT_AVAILABLE', False):
            
            daemon = AnalysisDaemon(temp_repo_dir)
            # Should assume changes exist
            assert daemon._has_repository_changes() is True
            assert daemon._get_changed_files() == []


if __name__ == "__main__":
    pytest.main([__file__])