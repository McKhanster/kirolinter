"""
Pytest configuration and fixtures for KiroLinter tests.

Provides both real and mocked Redis for comprehensive testing.
"""

import pytest
import redis
import json
from unittest.mock import Mock, patch
from kirolinter.memory.pattern_memory import create_pattern_memory


class MockRedis:
    """Mock Redis implementation for testing."""
    
    def __init__(self):
        self.data = {}
        self.lists = {}
        self.sets = {}
        self.expires = {}
    
    def ping(self):
        return True
    
    def hset(self, key, field=None, value=None, mapping=None):
        if key not in self.data:
            self.data[key] = {}
        if mapping:
            self.data[key].update(mapping)
        elif field and value:
            self.data[key][field] = value
        return True
    
    def hgetall(self, key):
        return self.data.get(key, {})
    
    def hget(self, key, field):
        return self.data.get(key, {}).get(field)
    
    def expire(self, key, seconds):
        self.expires[key] = seconds
        return True
    
    def sadd(self, key, *values):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].update(values)
        return len(values)
    
    def smembers(self, key):
        return self.sets.get(key, set())
    
    def lpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        for value in reversed(values):
            self.lists[key].insert(0, value)
        return len(self.lists[key])
    
    def ltrim(self, key, start, end):
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end+1 if end >= 0 else None]
        return True
    
    def lrange(self, key, start, end):
        if key not in self.lists:
            return []
        return self.lists[key][start:end+1 if end >= 0 else None]
    
    def scan_iter(self, match=None):
        keys = list(self.data.keys()) + list(self.lists.keys()) + list(self.sets.keys())
        if match:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        return keys
    
    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                count += 1
            if key in self.lists:
                del self.lists[key]
                count += 1
            if key in self.sets:
                del self.sets[key]
                count += 1
        return count
    
    def pipeline(self):
        return MockRedisPipeline(self)
    
    def info(self):
        return {
            "redis_version": "6.0.0",
            "used_memory_human": "1M",
            "connected_clients": 1
        }


class MockRedisPipeline:
    """Mock Redis pipeline for batch operations."""
    
    def __init__(self, redis_mock):
        self.redis = redis_mock
        self.commands = []
    
    def hset(self, key, field=None, value=None, mapping=None):
        self.commands.append(('hset', key, field, value, mapping))
        return self
    
    def expire(self, key, seconds):
        self.commands.append(('expire', key, seconds))
        return self
    
    def lpush(self, key, *values):
        self.commands.append(('lpush', key, values))
        return self
    
    def ltrim(self, key, start, end):
        self.commands.append(('ltrim', key, start, end))
        return self
    
    def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'hset':
                results.append(self.redis.hset(cmd[1], cmd[2], cmd[3], cmd[4]))
            elif cmd[0] == 'expire':
                results.append(self.redis.expire(cmd[1], cmd[2]))
            elif cmd[0] == 'lpush':
                results.append(self.redis.lpush(cmd[1], *cmd[2]))
            elif cmd[0] == 'ltrim':
                results.append(self.redis.ltrim(cmd[1], cmd[2], cmd[3]))
        self.commands = []
        return results


@pytest.fixture(scope="session")
def redis_server():
    """Try real Redis first, fall back to mock."""
    try:
        # Try to connect to real Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        return r
    except Exception:
        # Fall back to mock Redis
        return MockRedis()


@pytest.fixture(autouse=True)
def cleanup_redis(redis_server):
    """Clean up Redis data before and after each test."""
    # Clean up any test data from previous runs
    try:
        for key in redis_server.scan_iter(match="kirolinter:*"):
            redis_server.delete(key)
    except Exception:
        pass  # Mock Redis might not have all methods
    
    yield
    
    # Clean up after test
    try:
        for key in redis_server.scan_iter(match="kirolinter:*"):
            redis_server.delete(key)
    except Exception:
        pass


@pytest.fixture
def pattern_memory_redis_only():
    """Create a Redis-only pattern memory for testing."""
    return create_pattern_memory(
        redis_url="redis://localhost:6379",
        redis_only=True
    )


@pytest.fixture
def mock_redis_unavailable():
    """Mock Redis as unavailable for testing error conditions."""
    with patch('kirolinter.memory.redis_pattern_memory.REDIS_AVAILABLE', False):
        with patch('kirolinter.memory.redis_pattern_memory.redis.Redis.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            yield


@pytest.fixture
def temp_repo_dir():
    """Create a temporary repository directory for testing."""
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test Python files
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
def unused_function():
    pass

def main():
    x = 1  # unused variable
    print("Hello World")
""")
        
        # Create a simple git repo
        import subprocess
        try:
            subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, capture_output=True, check=True)
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, capture_output=True, check=True)
        except:
            pass  # Git operations are optional
        
        yield temp_dir


@pytest.fixture(autouse=True)
def mock_llm_dependencies():
    """Mock LLM dependencies automatically for all tests."""
    # Mock the LITELLM_AVAILABLE flag first
    with patch('kirolinter.agents.llm_config.LITELLM_AVAILABLE', True), \
         patch('kirolinter.agents.llm_provider.create_llm_provider') as mock_provider, \
         patch('kirolinter.agents.llm_config.get_chat_model') as mock_chat_model, \
         patch('kirolinter.agents.llm_config.LLMConfig.create_chat_model') as mock_create_model:
        
        # Create mock LLM objects
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Mock LLM response")
        mock_llm.batch.return_value = [Mock(content="Mock batch response")]
        
        # Configure all mocks to return the same mock LLM
        mock_provider.return_value = mock_llm
        mock_chat_model.return_value = mock_llm
        mock_create_model.return_value = mock_llm
        
        yield {
            'provider': mock_provider,
            'chat_model': mock_chat_model,
            'llm': mock_llm
        }