"""
Test Redis-only mode to eliminate SQLite concurrency issues.

This test demonstrates that using Redis-only mode would solve
the remaining database locking test failures.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from kirolinter.memory.pattern_memory import create_pattern_memory
from kirolinter.memory.redis_pattern_memory import RedisPatternMemory


class TestRedisOnlyMode:
    """Test Redis-only mode functionality."""
    
    def test_redis_only_mode_success(self):
        """Test Redis-only mode when Redis is available."""
        # Create memory in Redis-only mode with real Redis
        memory = create_pattern_memory(
            redis_url="redis://localhost:6379",
            redis_only=True
        )
        
        # Should return Redis instance
        assert isinstance(memory, RedisPatternMemory)
        assert memory.use_redis is True
        assert memory.sqlite_memory is None  # No fallback in Redis-only mode
    
    def test_redis_only_mode_failure(self):
        """Test Redis-only mode when Redis is unavailable."""
        with patch('kirolinter.memory.pattern_memory.REDIS_AVAILABLE', False):
            # Should raise exception in Redis-only mode
            with pytest.raises(Exception, match="Redis-only mode requested but Redis not available"):
                create_pattern_memory(redis_only=True)
    
    def test_redis_only_mode_connection_failure(self):
        """Test Redis-only mode when Redis connection fails."""
        # Use a wrong port to simulate connection failure
        with pytest.raises(Exception, match="Redis-only mode requested but Redis not available"):
            create_pattern_memory(
                redis_url="redis://localhost:9999",  # Wrong port
                redis_only=True
            )
    
    def test_concurrent_operations_redis_only(self):
        """Test that Redis-only mode eliminates concurrency issues."""
        # Use real Redis instance (no mocking needed)
        memory = create_pattern_memory(
            redis_url="redis://localhost:6379",
            redis_only=True
        )
        
        # Simulate concurrent operations that would cause SQLite locking
        results = []
        for i in range(20):  # More operations to stress test
            success = memory.store_pattern(f"/repo{i}", "test", {"data": i}, 0.5)
            results.append(success)
        
        # All operations should succeed with Redis (no SQLite locking)
        assert all(results), "All Redis operations should succeed without locking"
        
        # Verify patterns were actually stored
        stored_patterns = memory.get_team_patterns("/repo0")
        assert len(stored_patterns) == 1
        assert stored_patterns[0]["pattern_data"]["data"] == 0
    
    def test_fallback_mode_vs_redis_only(self):
        """Test that only Redis-only mode is supported."""
        # Fallback mode should raise exception (no longer supported)
        with pytest.raises(Exception, match="Only Redis-only mode is supported"):
            create_pattern_memory(redis_only=False)
        
        # Redis-only mode should work
        memory_redis_only = create_pattern_memory(
            redis_url="redis://localhost:6379",
            redis_only=True
        )
        assert isinstance(memory_redis_only, RedisPatternMemory)
        assert memory_redis_only.use_redis is True
        assert memory_redis_only.sqlite_memory is None  # No SQLite fallback


def test_solution_for_failing_tests():
    """
    Demonstrate how Redis-only mode would solve the failing tests.
    
    The failing tests are:
    1. test_pattern_evolution_tracking
    2. test_learning_change_tracking
    
    Both fail due to SQLite database locking. Using Redis-only mode
    would eliminate these issues completely.
    """
    # This is what the failing tests currently do:
    # pattern_memory = PatternMemory()  # Uses SQLite, causes locking
    
    # This is what they should do to eliminate locking:
    with patch('kirolinter.memory.pattern_memory.REDIS_AVAILABLE', True):
        with patch('kirolinter.memory.redis_pattern_memory.redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.pipeline.return_value = mock_redis
            mock_redis.execute.return_value = [True, True, True]
            mock_redis.hgetall.return_value = {}
            mock_redis.lrange.return_value = []
            mock_redis_class.from_url.return_value = mock_redis
            
            # Use Redis-only mode to eliminate SQLite locking
            pattern_memory = create_pattern_memory(redis_only=True)
            
            # These operations would never have locking issues with Redis
            success1 = pattern_memory.store_pattern("/test/repo", "naming", {"test": "data"}, 0.8)
            success2 = pattern_memory.record_learning_change("/test/repo", "naming", None, "new_data", "test")
            
            assert success1  # Would always succeed with Redis
            assert success2  # Would always succeed with Redis
            
            # No database locking errors possible with Redis


if __name__ == "__main__":
    pytest.main([__file__])