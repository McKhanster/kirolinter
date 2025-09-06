"""Database Connection Management

Provides PostgreSQL connection pooling and management for the DevOps orchestration system.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
import asyncpg
import os
from contextlib import asynccontextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""
    
    def __init__(self):
        """Initialize database manager"""
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'kirolinter_devops'),
            'user': os.getenv('POSTGRES_USER', 'kirolinter'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password'),
            'min_size': int(os.getenv('POSTGRES_MIN_POOL_SIZE', '5')),
            'max_size': int(os.getenv('POSTGRES_MAX_POOL_SIZE', '20')),
            'command_timeout': int(os.getenv('POSTGRES_COMMAND_TIMEOUT', '60')),
        }
        self.health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """
        Initialize database connection pool
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Initializing database connection pool...")
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                database=self.connection_config['database'],
                user=self.connection_config['user'],
                password=self.connection_config['password'],
                min_size=self.connection_config['min_size'],
                max_size=self.connection_config['max_size'],
                command_timeout=self.connection_config['command_timeout'],
                server_settings={
                    'application_name': 'kirolinter_devops',
                    'timezone': 'UTC'
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Database connection pool initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            return False
    
    async def close(self) -> None:
        """Close database connection pool"""
        try:
            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection pool
            if self.pool:
                await self.pool.close()
                self.pool = None
            
            logger.info("Database connection pool closed")
            
        except Exception as e:
            logger.error(f"Error closing database connection pool: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get database connection from pool
        
        Yields:
            asyncpg.Connection: Database connection
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                # Log error but let it propagate
                logger.error(f"Database operation error: {e}")
                raise
    
    @asynccontextmanager
    async def get_transaction(self):
        """
        Get database transaction
        
        Yields:
            asyncpg.Connection: Database connection with active transaction
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute_query(self, query: str, *args) -> Any:
        """
        Execute a query and return results
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Query results
        """
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def execute_command(self, command: str, *args) -> str:
        """
        Execute a command (INSERT, UPDATE, DELETE)
        
        Args:
            command: SQL command
            *args: Command parameters
            
        Returns:
            Command status
        """
        async with self.get_connection() as conn:
            return await conn.execute(command, *args)
    
    async def execute_many(self, command: str, args_list: list) -> None:
        """
        Execute a command multiple times with different parameters
        
        Args:
            command: SQL command
            args_list: List of parameter tuples
        """
        async with self.get_connection() as conn:
            await conn.executemany(command, args_list)
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check database health
        
        Returns:
            Dict containing health information
        """
        try:
            if not self.pool:
                return {
                    'healthy': False,
                    'error': 'Database pool not initialized',
                    'checked_at': datetime.utcnow().isoformat()
                }
            
            # Check pool status
            pool_size = self.pool.get_size()
            pool_idle = self.pool.get_idle_size()
            
            # Test query
            start_time = datetime.utcnow()
            async with self.get_connection() as conn:
                await conn.execute('SELECT 1')
            query_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'healthy': True,
                'pool_size': pool_size,
                'pool_idle': pool_idle,
                'pool_active': pool_size - pool_idle,
                'query_time_seconds': query_time,
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
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
                    logger.warning(f"Database health check failed: {health.get('error')}")
                else:
                    logger.debug(f"Database health check passed: {health['pool_active']} active connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def create_tables(self) -> bool:
        """
        Create database tables if they don't exist
        
        Returns:
            bool: True if successful
        """
        try:
            async with self.get_connection() as conn:
                # Read and execute schema file
                schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()
                    
                    # Execute schema in transaction
                    async with conn.transaction():
                        await conn.execute(schema_sql)
                    
                    logger.info("Database tables created successfully")
                    return True
                else:
                    logger.warning("Schema file not found, skipping table creation")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            return False
    
    async def migrate_database(self, target_version: Optional[str] = None) -> bool:
        """
        Run database migrations
        
        Args:
            target_version: Target migration version (latest if None)
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Running database migrations to version: {target_version or 'latest'}")
            
            # Import migration manager
            from .migrations.migration_manager import get_migration_manager
            
            # Get migration manager and run migrations
            migration_manager = await get_migration_manager()
            
            if target_version:
                result = await migration_manager.migrate_to_version(target_version)
            else:
                result = await migration_manager.migrate_to_latest()
            
            if result['success']:
                logger.info(f"Database migrations completed successfully: {result.get('applied_count', 0)} migrations applied")
                return True
            else:
                logger.error(f"Database migrations failed: {result.get('error', 'Unknown error')}")
                return False
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
async def init_db_pool() -> bool:
    """Initialize database connection pool"""
    return await db_manager.initialize()


async def close_db_pool() -> None:
    """Close database connection pool"""
    await db_manager.close()


def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    return db_manager


async def check_db_health() -> bool:
    """Check database health"""
    health = await db_manager.check_health()
    return health.get('healthy', False)


@asynccontextmanager
async def get_db_connection():
    """Get database connection context manager"""
    async with db_manager.get_connection() as conn:
        yield conn


@asynccontextmanager
async def get_db_transaction():
    """Get database transaction context manager"""
    async with db_manager.get_transaction() as conn:
        yield conn