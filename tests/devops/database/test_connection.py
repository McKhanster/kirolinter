"""
Tests for Database Connection Management

Comprehensive tests for PostgreSQL connection pooling and management.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import asyncpg

from kirolinter.database.connection import (
    DatabaseManager, init_db_pool, close_db_pool, get_db_manager,
    check_db_health, get_db_connection, get_db_transaction
)


class TestDatabaseManager:
    """Test cases for DatabaseManager"""
    
    @pytest.fixture
    def db_manager(self):
        """Create a database manager instance for testing"""
        return DatabaseManager()
    
    @pytest.fixture
    def mock_asyncpg_pool(self):
        """Create a mock asyncpg pool"""
        pool = AsyncMock()
        # Set up acquire to return an async context manager
        mock_conn_context = AsyncMock()
        mock_conn_context.__aenter__ = AsyncMock()
        mock_conn_context.__aexit__ = AsyncMock(return_value=None)
        pool.acquire.return_value = mock_conn_context
        pool.close = AsyncMock(return_value=None)
        pool.get_size.return_value = 10
        pool.get_idle_size.return_value = 5
        return pool
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection"""
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetch = AsyncMock()
        conn.fetchval = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.transaction = AsyncMock()
        return conn
    
    def test_initialization(self, db_manager):
        """Test database manager initialization"""
        assert db_manager.pool is None
        assert db_manager.connection_config["host"] == "localhost"
        assert db_manager.connection_config["port"] == 5432
        assert db_manager.connection_config["database"] == "kirolinter_devops"
        assert db_manager.connection_config["min_size"] == 5
        assert db_manager.connection_config["max_size"] == 20
        assert db_manager.health_check_interval == 30
    
    @pytest.mark.asyncio
    @patch('asyncpg.create_pool')
    async def test_initialize_success(self, mock_create_pool, db_manager, mock_asyncpg_pool, mock_connection):
        """Test successful database initialization"""
        # Setup mock - asyncpg.create_pool is an async function
        mock_create_pool.side_effect = AsyncMock(return_value=mock_asyncpg_pool)
        # Configure the connection returned by the context manager
        # Note: mock_asyncpg_pool fixture already sets up acquire correctly
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Initialize database
        success = await db_manager.initialize()
        
        assert success is True
        assert db_manager.pool == mock_asyncpg_pool
        
        # Verify pool creation was called with correct parameters
        mock_create_pool.assert_called_once()
        call_kwargs = mock_create_pool.call_args.kwargs
        assert call_kwargs["host"] == "localhost"
        assert call_kwargs["port"] == 5432
        assert call_kwargs["database"] == "kirolinter_devops"
        assert call_kwargs["min_size"] == 5
        assert call_kwargs["max_size"] == 20
        
        # Verify test connection was made
        mock_connection.execute.assert_called_once_with('SELECT 1')
    
    @pytest.mark.asyncio
    @patch('asyncpg.create_pool')
    async def test_initialize_failure(self, mock_create_pool, db_manager):
        """Test database initialization failure"""
        # Setup mock to raise exception - asyncpg.create_pool is async
        mock_create_pool.side_effect = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Initialize database
        success = await db_manager.initialize()
        
        assert success is False
        assert db_manager.pool is None
    
    @pytest.mark.asyncio
    async def test_close(self, db_manager, mock_asyncpg_pool):
        """Test database connection pool closure"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        # Create a mock task that behaves like an asyncio Task
        mock_task = Mock()
        mock_task.cancel = Mock()
        db_manager._health_check_task = mock_task
        
        # Close database
        await db_manager.close()
        
        # Verify cleanup
        mock_asyncpg_pool.close.assert_called_once()
        assert db_manager.pool is None
        mock_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_connection_success(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test getting database connection successfully"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Get connection
        async with db_manager.get_connection() as conn:
            assert conn == mock_connection
        
        # Verify pool acquire was called
        mock_asyncpg_pool.acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_connection_no_pool(self, db_manager):
        """Test getting connection when pool is not initialized"""
        # Pool is None by default
        assert db_manager.pool is None
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            async with db_manager.get_connection():
                pass
    
    @pytest.mark.asyncio
    async def test_get_transaction(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test getting database transaction"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock transaction context manager
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = None
        mock_transaction.__aexit__.return_value = None
        
        # Get transaction
        async with db_manager.get_transaction() as conn:
            assert conn == mock_connection
        
        # Verify transaction was created
        mock_connection.transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_query(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test executing a query"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock query result
        expected_result = [{"id": 1, "name": "test"}]
        mock_connection.fetch.return_value = expected_result
        
        # Execute query
        result = await db_manager.execute_query("SELECT * FROM test WHERE id = $1", 1)
        
        assert result == expected_result
        mock_connection.fetch.assert_called_once_with("SELECT * FROM test WHERE id = $1", 1)
    
    @pytest.mark.asyncio
    async def test_execute_command(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test executing a command"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock command result
        expected_result = "INSERT 0 1"
        mock_connection.execute.return_value = expected_result
        
        # Execute command
        result = await db_manager.execute_command("INSERT INTO test (name) VALUES ($1)", "test_name")
        
        assert result == expected_result
        mock_connection.execute.assert_called_once_with("INSERT INTO test (name) VALUES ($1)", "test_name")
    
    @pytest.mark.asyncio
    async def test_execute_many(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test executing multiple commands"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Execute many
        args_list = [("name1",), ("name2",), ("name3",)]
        await db_manager.execute_many("INSERT INTO test (name) VALUES ($1)", args_list)
        
        mock_connection.executemany.assert_called_once_with(
            "INSERT INTO test (name) VALUES ($1)", 
            args_list
        )
    
    @pytest.mark.asyncio
    async def test_check_health_success(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test successful health check"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        mock_asyncpg_pool.get_size.return_value = 10
        mock_asyncpg_pool.get_idle_size.return_value = 6
        
        # Mock successful query
        mock_connection.execute.return_value = None
        
        # Check health
        health = await db_manager.check_health()
        
        assert health["healthy"] is True
        assert health["pool_size"] == 10
        assert health["pool_idle"] == 6
        assert health["pool_active"] == 4
        assert "query_time_seconds" in health
        assert "checked_at" in health
        
        mock_connection.execute.assert_called_once_with('SELECT 1')
    
    @pytest.mark.asyncio
    async def test_check_health_no_pool(self, db_manager):
        """Test health check when pool is not initialized"""
        # Pool is None by default
        health = await db_manager.check_health()
        
        assert health["healthy"] is False
        assert "Database pool not initialized" in health["error"]
        assert "checked_at" in health
    
    @pytest.mark.asyncio
    async def test_check_health_failure(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test health check failure"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock query failure
        mock_connection.execute.side_effect = Exception("Query failed")
        
        # Check health
        health = await db_manager.check_health()
        
        assert health["healthy"] is False
        assert "Query failed" in health["error"]
        assert "checked_at" in health
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    async def test_create_tables_success(self, mock_open, mock_exists, db_manager, 
                                       mock_asyncpg_pool, mock_connection):
        """Test successful table creation"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock transaction
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = None
        mock_transaction.__aexit__.return_value = None
        
        # Mock file operations
        mock_exists.return_value = True
        mock_schema_content = "CREATE TABLE test (id SERIAL PRIMARY KEY);"
        mock_file = Mock()
        mock_file.read.return_value = mock_schema_content
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Create tables
        success = await db_manager.create_tables()
        
        assert success is True
        mock_connection.execute.assert_called_once_with(mock_schema_content)
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_create_tables_no_schema_file(self, mock_exists, db_manager, 
                                              mock_asyncpg_pool, mock_connection):
        """Test table creation when schema file doesn't exist"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Create tables
        success = await db_manager.create_tables()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_migrate_database(self, db_manager):
        """Test database migration"""
        # Mock create_tables method
        with patch.object(db_manager, 'create_tables', return_value=True) as mock_create_tables:
            success = await db_manager.migrate_database("v1.0.0")
            
            assert success is True
            mock_create_tables.assert_called_once()


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager"""
    
    @pytest.mark.asyncio
    @patch('asyncpg.create_pool')
    async def test_full_lifecycle(self, mock_create_pool):
        """Test complete database manager lifecycle"""
        # Setup mocks
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_create_pool.side_effect = AsyncMock(return_value=mock_pool)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_pool.acquire.return_value.__aexit__.return_value = None
        mock_pool.get_size.return_value = 5
        mock_pool.get_idle_size.return_value = 3
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Initialize
        success = await db_manager.initialize()
        assert success is True
        assert db_manager.pool == mock_pool
        
        # Execute query
        mock_connection.fetch.return_value = [{"count": 1}]
        result = await db_manager.execute_query("SELECT COUNT(*) as count FROM test")
        assert result == [{"count": 1}]
        
        # Execute command
        mock_connection.execute.return_value = "INSERT 0 1"
        result = await db_manager.execute_command("INSERT INTO test (name) VALUES ($1)", "test")
        assert result == "INSERT 0 1"
        
        # Check health
        mock_connection.execute.return_value = None  # For health check query
        health = await db_manager.check_health()
        assert health["healthy"] is True
        assert health["pool_size"] == 5
        assert health["pool_idle"] == 3
        assert health["pool_active"] == 2
        
        # Close
        await db_manager.close()
        mock_pool.close.assert_called_once()
        assert db_manager.pool is None


class TestConvenienceFunctions:
    """Test cases for convenience functions"""
    
    @pytest.mark.asyncio
    @patch('kirolinter.database.connection.db_manager')
    async def test_init_db_pool(self, mock_db_manager):
        """Test init_db_pool convenience function"""
        mock_db_manager.initialize.return_value = True
        
        success = await init_db_pool()
        
        assert success is True
        mock_db_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('kirolinter.database.connection.db_manager')
    async def test_close_db_pool(self, mock_db_manager):
        """Test close_db_pool convenience function"""
        await close_db_pool()
        
        mock_db_manager.close.assert_called_once()
    
    @patch('kirolinter.database.connection.db_manager')
    def test_get_db_manager(self, mock_db_manager):
        """Test get_db_manager convenience function"""
        manager = get_db_manager()
        
        assert manager == mock_db_manager
    
    @pytest.mark.asyncio
    @patch('kirolinter.database.connection.db_manager')
    async def test_check_db_health(self, mock_db_manager):
        """Test check_db_health convenience function"""
        mock_db_manager.check_health.return_value = {"healthy": True}
        
        healthy = await check_db_health()
        
        assert healthy is True
        mock_db_manager.check_health.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('kirolinter.database.connection.db_manager')
    async def test_get_db_connection_context_manager(self, mock_db_manager):
        """Test get_db_connection context manager"""
        mock_connection = AsyncMock()
        mock_db_manager.get_connection.return_value.__aenter__.return_value = mock_connection
        mock_db_manager.get_connection.return_value.__aexit__.return_value = None
        
        async with get_db_connection() as conn:
            assert conn == mock_connection
        
        mock_db_manager.get_connection.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('kirolinter.database.connection.db_manager')
    async def test_get_db_transaction_context_manager(self, mock_db_manager):
        """Test get_db_transaction context manager"""
        mock_connection = AsyncMock()
        mock_db_manager.get_transaction.return_value.__aenter__.return_value = mock_connection
        mock_db_manager.get_transaction.return_value.__aexit__.return_value = None
        
        async with get_db_transaction() as conn:
            assert conn == mock_connection
        
        mock_db_manager.get_transaction.assert_called_once()


class TestDatabaseManagerErrorHandling:
    """Test cases for error handling in DatabaseManager"""
    
    @pytest.fixture
    def db_manager(self):
        """Create a database manager instance for testing"""
        return DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, db_manager, mock_asyncpg_pool):
        """Test connection error handling"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        
        # Mock connection acquisition failure
        mock_asyncpg_pool.acquire.side_effect = Exception("Connection failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Connection failed"):
            async with db_manager.get_connection():
                pass
    
    @pytest.mark.asyncio
    async def test_query_error_handling(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test query error handling"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock query failure
        mock_connection.fetch.side_effect = Exception("Query failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Query failed"):
            await db_manager.execute_query("SELECT * FROM test")
    
    @pytest.mark.asyncio
    async def test_transaction_error_handling(self, db_manager, mock_asyncpg_pool, mock_connection):
        """Test transaction error handling"""
        # Setup database manager with pool
        db_manager.pool = mock_asyncpg_pool
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_asyncpg_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock transaction failure
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.side_effect = Exception("Transaction failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Transaction failed"):
            async with db_manager.get_transaction():
                pass


class TestDatabaseManagerConfiguration:
    """Test cases for database manager configuration"""
    
    @patch.dict('os.environ', {
        'POSTGRES_HOST': 'custom-host',
        'POSTGRES_PORT': '5433',
        'POSTGRES_DB': 'custom_db',
        'POSTGRES_USER': 'custom_user',
        'POSTGRES_PASSWORD': 'custom_pass',
        'POSTGRES_MIN_POOL_SIZE': '10',
        'POSTGRES_MAX_POOL_SIZE': '50',
        'POSTGRES_COMMAND_TIMEOUT': '120'
    })
    def test_configuration_from_environment(self):
        """Test configuration loading from environment variables"""
        db_manager = DatabaseManager()
        
        assert db_manager.connection_config["host"] == "custom-host"
        assert db_manager.connection_config["port"] == 5433
        assert db_manager.connection_config["database"] == "custom_db"
        assert db_manager.connection_config["user"] == "custom_user"
        assert db_manager.connection_config["password"] == "custom_pass"
        assert db_manager.connection_config["min_size"] == 10
        assert db_manager.connection_config["max_size"] == 50
        assert db_manager.connection_config["command_timeout"] == 120
    
    def test_default_configuration(self):
        """Test default configuration values"""
        db_manager = DatabaseManager()
        
        assert db_manager.connection_config["host"] == "localhost"
        assert db_manager.connection_config["port"] == 5432
        assert db_manager.connection_config["database"] == "kirolinter_devops"
        assert db_manager.connection_config["user"] == "kirolinter"
        assert db_manager.connection_config["password"] == "password"
        assert db_manager.connection_config["min_size"] == 5
        assert db_manager.connection_config["max_size"] == 20
        assert db_manager.connection_config["command_timeout"] == 60


if __name__ == "__main__":
    pytest.main([__file__])