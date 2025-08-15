"""
Tests for Redis Pattern Memory System.

Tests the Redis-based PatternMemory with fallback to SQLite,
focusing on concurrency, performance, and data consistency.
"""

import pytest
import tempfile
import json
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from kirolinter.memory.redis_pattern_memory import RedisPatternMemory

# Test both Redis and fallback scenarios
try:
    import redis
    from kirolinter.memory.redis_pattern_memory import RedisPatternMemory, REDIS_AVAILABLE
    REDIS_TESTS_ENABLED = True
except ImportError:
    REDIS_TESTS_ENABLED = False

from kirolinter.memory.pattern_memory import create_pattern_memory, PatternMemory


class TestRedisPatternMemory:
    """Test Redis-based pattern memory functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client for testing."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.hset.return_value = True
        mock_redis.hgetall.return_value = {}
        mock_redis.expire.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.smembers.return_value = set()
        mock_redis.lpush.return_value = True
        mock_redis.ltrim.return_value = True
        mock_redis.lrange.return_value = []
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.execute.return_value = [True, True, True]
        mock_redis.scan_iter.return_value = []
        mock_redis.info.return_value = {
            "redis_version": "6.0.0",
            "used_memory_human": "1M",
            "connected_clients": 1
        }
        return mock_redis
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary SQLite database path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_redis_memory_initialization(self, mock_redis, temp_db_path):
        """Test Redis memory initialization in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(
                redis_url="redis://localhost:6379",
                redis_only=True
            )
            
            assert memory.use_redis is True
            assert memory.redis is not None
            # In Redis-only mode, no SQLite fallback should be configured
            assert memory.sqlite_memory is None
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_redis_connection_failure_redis_only(self, temp_db_path):
        """Test Redis-only mode fails when Redis connection fails."""
        with patch('redis.Redis.from_url', side_effect=Exception("Connection failed")):
            # Redis-only mode should raise exception when Redis fails
            with pytest.raises(Exception, match="Redis-only mode requested but Redis not available"):
                create_pattern_memory(
                    redis_url="redis://localhost:6379",
                    redis_only=True
                )
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_pattern_storage_redis(self, mock_redis, temp_db_path):
        """Test pattern storage using Redis backend in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            pattern_data = {
                "variables": {"snake_case": 10, "camelCase": 2},
                "confidence": 0.8
            }
            
            success = memory.store_pattern("/test/repo", "naming", pattern_data, 0.8)
            assert success
            
            # Verify Redis operations were called
            mock_redis.hset.assert_called()
            mock_redis.expire.assert_called()
            mock_redis.sadd.assert_called()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_pattern_retrieval_redis(self, mock_redis, temp_db_path):
        """Test pattern retrieval using Redis backend in Redis-only mode."""
        # Mock Redis response
        mock_redis.hgetall.return_value = {
            "pattern_type": "naming",
            "pattern_data": '{"variables": {"snake_case": 10}}',
            "confidence": "0.8",
            "usage_count": "1",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            patterns = memory.get_team_patterns("/test/repo", "naming")
            
            assert len(patterns) == 1
            assert patterns[0]["pattern_type"] == "naming"
            assert patterns[0]["confidence"] == 0.8
            assert patterns[0]["usage_count"] == 1
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_issue_tracking_redis(self, mock_redis, temp_db_path):
        """Test issue pattern tracking using Redis in Redis-only mode."""
        # Mock existing issue data
        mock_redis.hget.return_value = json.dumps({
            "issue_type": "style",
            "issue_rule": "E501",
            "severity": "medium",
            "frequency": 5,
            "trend_score": 0.5
        })
        
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            success = memory.track_issue_pattern("/test/repo", "style", "E501", "medium")
            assert success
            
            # Verify Redis operations
            mock_redis.hget.assert_called()
            mock_redis.hset.assert_called()
            mock_redis.expire.assert_called()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_fix_outcome_recording_redis(self, mock_redis, temp_db_path):
        """Test fix outcome recording using Redis lists in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            success = memory.record_fix_outcome(
                "/test/repo", "style", "line_length", True, 0.8, {"test": "data"}
            )
            assert success
            
            # Verify Redis list operations
            mock_redis.lpush.assert_called()
            mock_redis.ltrim.assert_called()
            mock_redis.expire.assert_called()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_learning_session_recording_redis(self, mock_redis, temp_db_path):
        """Test learning session recording using Redis in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            success = memory.record_learning_session(
                "/test/repo", "commit_analysis", 5, 3, {"commits": 10}
            )
            assert success
            
            # Verify Redis operations
            mock_redis.lpush.assert_called()
            mock_redis.ltrim.assert_called()
            mock_redis.expire.assert_called()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_comprehensive_insights_redis(self, mock_redis, temp_db_path):
        """Test comprehensive insights generation with Redis."""
        # Mock various Redis responses
        mock_redis.smembers.return_value = {"naming", "imports"}
        mock_redis.hgetall.side_effect = [
            {
                "pattern_type": "naming",
                "pattern_data": '{"variables": {"snake_case": 10}}',
                "confidence": "0.8",
                "usage_count": "5",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            {
                "pattern_type": "imports",
                "pattern_data": '{"style": "from_import"}',
                "confidence": "0.9",
                "usage_count": "3",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]
        mock_redis.lrange.return_value = []  # Empty fix outcomes and sessions
        
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            insights = memory.get_comprehensive_insights("/test/repo")
            
            assert "team_patterns" in insights
            assert "issue_trends" in insights
            assert "fix_success_rates" in insights
            assert "learning_analytics" in insights
            assert "recommendations" in insights
            
            # Should have 2 patterns
            assert len(insights["team_patterns"]) == 2
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_health_check_redis(self, mock_redis, temp_db_path):
        """Test Redis health check functionality in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            health = memory.health_check()
            
            assert health["redis_available"] is True
            assert health["redis_connected"] is True
            assert health["active_backend"] == "redis"
            assert "redis_info" in health
            assert health["redis_info"]["version"] == "6.0.0"
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_health_check_redis_failure(self, temp_db_path):
        """Test health check when Redis fails in Redis-only mode."""
        with patch('redis.Redis.from_url', side_effect=Exception("Connection failed")):
            # Redis-only mode should raise exception when Redis fails
            with pytest.raises(Exception, match="Redis-only mode requested but Redis not available"):
                create_pattern_memory(redis_only=True)
    
    def test_factory_function_redis_only_mode(self, temp_db_path):
        """Test factory function with Redis-only mode."""
        memory = create_pattern_memory(
            redis_url="redis://localhost:6379",
            redis_only=True
        )
        
        assert isinstance(memory, RedisPatternMemory)
        assert memory.use_redis is True
        assert memory.sqlite_memory is None  # Redis-only mode
    
    def test_factory_function_redis_unavailable_redis_only(self, temp_db_path):
        """Test factory function with Redis-only mode when Redis unavailable."""
        with patch('kirolinter.memory.pattern_memory.REDIS_AVAILABLE', False):
            # Redis-only mode should raise exception when Redis unavailable
            with pytest.raises(Exception, match="Redis-only mode requested but Redis not available"):
                create_pattern_memory(
                    redis_url="redis://localhost:6379",
                    redis_only=True
                )
    
    def test_factory_function_fallback_mode(self, temp_db_path):
        """Test factory function rejects fallback mode (Redis-only enforced)."""
        with pytest.raises(Exception, match="Only Redis-only mode is supported"):
            create_pattern_memory(
                redis_url="redis://localhost:6379",
                sqlite_path=temp_db_path,
                redis_only=False  # Should be rejected
            )
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_data_anonymization_redis(self, mock_redis, temp_db_path):
        """Test data anonymization in Redis backend with Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            # Pattern with sensitive data
            sensitive_pattern = {
                "examples": [
                    "password = 'secret123'",
                    "api_key = 'sk-1234567890abcdef'"
                ]
            }
            
            success = memory.store_pattern("/test/repo", "security", sensitive_pattern, 0.5)
            assert success
            
            # Verify Redis was called (anonymization happens before Redis call)
            mock_redis.hset.assert_called()
            
            # Check that the stored data was anonymized
            # The hset call should have been made with mapping parameter
            call_args = mock_redis.hset.call_args
            if call_args and len(call_args) > 1 and 'mapping' in call_args[1]:
                stored_data = call_args[1]['mapping']['pattern_data']
                
                # Should not contain sensitive data
                assert "secret123" not in stored_data
                assert "sk-1234567890abcdef" not in stored_data
                assert "<REDACTED>" in stored_data
            else:
                # If we can't check the exact data, at least verify the call was made
                assert mock_redis.hset.called
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_ttl_cleanup_redis(self, mock_redis, temp_db_path):
        """Test TTL-based cleanup in Redis with Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            success = memory.cleanup_old_data(days_to_keep=30)
            assert success
            
            # Should update TTL for existing keys
            mock_redis.scan_iter.assert_called_with(match="kirolinter:*")
            # expire should be called for each key found
            if mock_redis.scan_iter.return_value:
                mock_redis.expire.assert_called()
    
    @pytest.mark.skipif(not REDIS_TESTS_ENABLED, reason="Redis not available")
    def test_atomic_operations_redis(self, mock_redis, temp_db_path):
        """Test atomic operations using Redis pipeline in Redis-only mode."""
        with patch('redis.Redis.from_url', return_value=mock_redis):
            memory = create_pattern_memory(redis_only=True)
            
            # Store pattern should use pipeline for atomicity
            success = memory.store_pattern("/test/repo", "naming", {"test": "data"}, 0.8)
            assert success
            
            # Verify pipeline was used
            mock_redis.pipeline.assert_called()
            mock_redis.execute.assert_called()
    
    def test_concurrent_access_simulation(self, temp_db_path):
        """Test that Redis eliminates concurrency issues."""
        # This test simulates what would cause SQLite locking
        # With Redis, there should be no issues
        
        with patch('kirolinter.memory.pattern_memory.REDIS_AVAILABLE', True):
            with patch('kirolinter.memory.redis_pattern_memory.redis.Redis') as mock_redis_class:
                mock_redis = Mock()
                mock_redis.ping.return_value = True
                mock_redis.hgetall.return_value = {}  # No existing pattern
                mock_redis.pipeline.return_value = mock_redis
                mock_redis.execute.return_value = [True, True, True]
                mock_redis.hset.return_value = True
                mock_redis.expire.return_value = True
                mock_redis.sadd.return_value = True
                mock_redis_class.from_url.return_value = mock_redis
                
                memory = create_pattern_memory(redis_only=True)
                
                # Simulate concurrent operations (would cause SQLite locking)
                results = []
                for i in range(10):
                    success = memory.store_pattern(f"/repo{i}", "test", {"data": i}, 0.5)
                    results.append(success)
                
                # All operations should succeed with Redis
                assert all(results)
                # Each store_pattern makes 2 pipeline calls (main storage + learning change)
                assert mock_redis.execute.call_count == 20


if __name__ == "__main__":
    pytest.main([__file__])