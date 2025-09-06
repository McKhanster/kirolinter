"""Redis Client Management

Provides Redis connection pooling and management for caching and message broker functionality.
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any, Union, List
import redis.asyncio as redis
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connections and operations"""
    
    def __init__(self):
        """Initialize Redis manager"""
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self.connection_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD'),
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '20')),
            'retry_on_timeout': True,
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            'socket_connect_timeout': int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),
            'health_check_interval': int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30')),
        }
        self.health_check_interval = self.connection_config['health_check_interval']
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection pool
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Initializing Redis connection pool...")
            
            # Create connection pool
            self.pool = redis.ConnectionPool(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                db=self.connection_config['db'],
                password=self.connection_config['password'],
                max_connections=self.connection_config['max_connections'],
                retry_on_timeout=self.connection_config['retry_on_timeout'],
                socket_timeout=self.connection_config['socket_timeout'],
                socket_connect_timeout=self.connection_config['socket_connect_timeout'],
                decode_responses=True
            )
            
            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._is_initialized = True
            logger.info("Redis connection pool initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection pool"""
        try:
            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close Redis client and pool
            if self.client:
                await self.client.aclose()
                self.client = None
            
            if self.pool:
                await self.pool.aclose()
                self.pool = None
            
            self._is_initialized = False
            logger.info("Redis connection pool closed")
            
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client
        
        Returns:
            redis.Redis: Redis client instance
            
        Raises:
            RuntimeError: If Redis is not initialized
        """
        if not self._is_initialized or not self.client:
            raise RuntimeError("Redis client not initialized")
        return self.client
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None, 
                  px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """
        Set a key-value pair
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            ex: Expiration in seconds
            px: Expiration in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            bool: True if successful
        """
        try:
            client = self.get_client()
            
            # Serialize value if not string
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            result = await client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis SET operation failed for key '{key}': {e}")
            return False
    
    async def get(self, key: str, decode_json: bool = True) -> Optional[Any]:
        """
        Get value by key
        
        Args:
            key: Redis key
            decode_json: Whether to attempt JSON decoding
            
        Returns:
            Value or None if not found
        """
        try:
            client = self.get_client()
            value = await client.get(key)
            
            if value is None:
                return None
            
            # Attempt JSON decoding if requested
            if decode_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Return as string if JSON decoding fails
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis GET operation failed for key '{key}': {e}")
            return None
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys
        
        Args:
            *keys: Keys to delete
            
        Returns:
            int: Number of keys deleted
        """
        try:
            client = self.get_client()
            return await client.delete(*keys)
            
        except Exception as e:
            logger.error(f"Redis DELETE operation failed for keys {keys}: {e}")
            return 0
    
    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist
        
        Args:
            *keys: Keys to check
            
        Returns:
            int: Number of existing keys
        """
        try:
            client = self.get_client()
            return await client.exists(*keys)
            
        except Exception as e:
            logger.error(f"Redis EXISTS operation failed for keys {keys}: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration for a key
        
        Args:
            key: Redis key
            seconds: Expiration in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            client = self.get_client()
            return await client.expire(key, seconds)
            
        except Exception as e:
            logger.error(f"Redis EXPIRE operation failed for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get time to live for a key
        
        Args:
            key: Redis key
            
        Returns:
            int: TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        try:
            client = self.get_client()
            return await client.ttl(key)
            
        except Exception as e:
            logger.error(f"Redis TTL operation failed for key '{key}': {e}")
            return -2
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a key's value
        
        Args:
            key: Redis key
            amount: Amount to increment by
            
        Returns:
            int: New value after increment
        """
        try:
            client = self.get_client()
            return await client.incr(key, amount)
            
        except Exception as e:
            logger.error(f"Redis INCR operation failed for key '{key}': {e}")
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a key's value
        
        Args:
            key: Redis key
            amount: Amount to decrement by
            
        Returns:
            int: New value after decrement
        """
        try:
            client = self.get_client()
            return await client.decr(key, amount)
            
        except Exception as e:
            logger.error(f"Redis DECR operation failed for key '{key}': {e}")
            return 0
    
    async def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list
        
        Args:
            key: Redis key
            *values: Values to push
            
        Returns:
            int: Length of list after push
        """
        try:
            client = self.get_client()
            # Serialize non-string values
            serialized_values = []
            for value in values:
                if isinstance(value, str):
                    serialized_values.append(value)
                else:
                    serialized_values.append(json.dumps(value, default=str))
            
            return await client.lpush(key, *serialized_values)
            
        except Exception as e:
            logger.error(f"Redis LPUSH operation failed for key '{key}': {e}")
            return 0
    
    async def rpop(self, key: str, decode_json: bool = True) -> Optional[Any]:
        """
        Pop value from the right of a list
        
        Args:
            key: Redis key
            decode_json: Whether to attempt JSON decoding
            
        Returns:
            Popped value or None if list is empty
        """
        try:
            client = self.get_client()
            value = await client.rpop(key)
            
            if value is None:
                return None
            
            # Attempt JSON decoding if requested
            if decode_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis RPOP operation failed for key '{key}': {e}")
            return None
    
    async def lrange(self, key: str, start: int = 0, end: int = -1, 
                     decode_json: bool = True) -> List[Any]:
        """
        Get range of values from a list
        
        Args:
            key: Redis key
            start: Start index
            end: End index
            decode_json: Whether to attempt JSON decoding
            
        Returns:
            List of values
        """
        try:
            client = self.get_client()
            values = await client.lrange(key, start, end)
            
            if not decode_json:
                return values
            
            # Attempt JSON decoding for each value
            decoded_values = []
            for value in values:
                try:
                    decoded_values.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    decoded_values.append(value)
            
            return decoded_values
            
        except Exception as e:
            logger.error(f"Redis LRANGE operation failed for key '{key}': {e}")
            return []
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """
        Trim a list to specified range
        
        Args:
            key: Redis key
            start: Start index
            end: End index
            
        Returns:
            bool: True if successful
        """
        try:
            client = self.get_client()
            await client.ltrim(key, start, end)
            return True
            
        except Exception as e:
            logger.error(f"Redis LTRIM operation failed for key '{key}': {e}")
            return False
    
    async def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        """
        Set hash fields
        
        Args:
            key: Redis key
            mapping: Field-value mapping
            
        Returns:
            int: Number of fields added
        """
        try:
            client = self.get_client()
            
            # Serialize non-string values
            serialized_mapping = {}
            for field, value in mapping.items():
                if isinstance(value, str):
                    serialized_mapping[field] = value
                else:
                    serialized_mapping[field] = json.dumps(value, default=str)
            
            return await client.hset(key, mapping=serialized_mapping)
            
        except Exception as e:
            logger.error(f"Redis HSET operation failed for key '{key}': {e}")
            return 0
    
    async def hget(self, key: str, field: str, decode_json: bool = True) -> Optional[Any]:
        """
        Get hash field value
        
        Args:
            key: Redis key
            field: Hash field
            decode_json: Whether to attempt JSON decoding
            
        Returns:
            Field value or None if not found
        """
        try:
            client = self.get_client()
            value = await client.hget(key, field)
            
            if value is None:
                return None
            
            # Attempt JSON decoding if requested
            if decode_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis HGET operation failed for key '{key}', field '{field}': {e}")
            return None
    
    async def hgetall(self, key: str, decode_json: bool = True) -> Dict[str, Any]:
        """
        Get all hash fields and values
        
        Args:
            key: Redis key
            decode_json: Whether to attempt JSON decoding
            
        Returns:
            Dict of field-value pairs
        """
        try:
            client = self.get_client()
            hash_data = await client.hgetall(key)
            
            if not decode_json:
                return hash_data
            
            # Attempt JSON decoding for each value
            decoded_data = {}
            for field, value in hash_data.items():
                try:
                    decoded_data[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    decoded_data[field] = value
            
            return decoded_data
            
        except Exception as e:
            logger.error(f"Redis HGETALL operation failed for key '{key}': {e}")
            return {}
    
    async def hdel(self, key: str, *fields: str) -> int:
        """
        Delete hash fields
        
        Args:
            key: Redis key
            *fields: Fields to delete
            
        Returns:
            int: Number of fields deleted
        """
        try:
            client = self.get_client()
            return await client.hdel(key, *fields)
            
        except Exception as e:
            logger.error(f"Redis HDEL operation failed for key '{key}': {e}")
            return 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern
        
        Args:
            pattern: Key pattern (default: all keys)
            
        Returns:
            List of matching keys
        """
        try:
            client = self.get_client()
            return await client.keys(pattern)
            
        except Exception as e:
            logger.error(f"Redis KEYS operation failed for pattern '{pattern}': {e}")
            return []
    
    async def flushdb(self) -> bool:
        """
        Flush current database
        
        Returns:
            bool: True if successful
        """
        try:
            client = self.get_client()
            await client.flushdb()
            return True
            
        except Exception as e:
            logger.error(f"Redis FLUSHDB operation failed: {e}")
            return False
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check Redis health
        
        Returns:
            Dict containing health information
        """
        try:
            if not self._is_initialized or not self.client:
                return {
                    'healthy': False,
                    'error': 'Redis client not initialized',
                    'checked_at': datetime.utcnow().isoformat()
                }
            
            # Test ping
            start_time = datetime.utcnow()
            await self.client.ping()
            ping_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get info
            info = await self.client.info()
            
            return {
                'healthy': True,
                'ping_time_seconds': ping_time,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'redis_version': info.get('redis_version', 'unknown'),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0),
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }
    
    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                health = await self.check_health()
                
                if not health['healthy']:
                    logger.warning(f"Redis health check failed: {health.get('error')}")
                else:
                    logger.debug(f"Redis health check passed: {health['connected_clients']} clients")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis health check loop error: {e}")
    
    # Cache-specific convenience methods
    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """
        Set cache value with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        return await self.set(key, value, ex=ttl_seconds)
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Get cache value
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        return await self.get(key, decode_json=True)
    
    async def cache_delete(self, key: str) -> bool:
        """
        Delete cache value
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted
        """
        return await self.delete(key) > 0
    
    async def cache_get_or_set(self, key: str, factory_func, ttl_seconds: int = 3600) -> Any:
        """
        Get cached value or set it using factory function
        
        Args:
            key: Cache key
            factory_func: Function to generate value if not cached
            ttl_seconds: Time to live in seconds
            
        Returns:
            Cached or generated value
        """
        # Try to get cached value
        value = await self.cache_get(key)
        if value is not None:
            return value
        
        # Generate new value
        if asyncio.iscoroutinefunction(factory_func):
            value = await factory_func()
        else:
            value = factory_func()
        
        # Cache the new value
        await self.cache_set(key, value, ttl_seconds)
        return value


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions
async def init_redis_pool() -> bool:
    """Initialize Redis connection pool"""
    return await redis_manager.initialize()


async def close_redis_pool() -> None:
    """Close Redis connection pool"""
    await redis_manager.close()


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return redis_manager.get_client()


def get_redis_manager() -> RedisManager:
    """Get Redis manager instance"""
    return redis_manager


async def check_redis_health() -> bool:
    """Check Redis health"""
    health = await redis_manager.check_health()
    return health.get('healthy', False)


# Cache convenience functions
async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Set cache value with TTL"""
    return await redis_manager.cache_set(key, value, ttl_seconds)


async def cache_get(key: str) -> Optional[Any]:
    """Get cache value"""
    return await redis_manager.cache_get(key)


async def cache_delete(key: str) -> bool:
    """Delete cache value"""
    return await redis_manager.cache_delete(key)


async def cache_get_or_set(key: str, factory_func, ttl_seconds: int = 3600) -> Any:
    """Get cached value or set it using factory function"""
    return await redis_manager.cache_get_or_set(key, factory_func, ttl_seconds)