"""Database Migration Manager

Handles database schema evolution and data migrations for KiroLinter DevOps orchestration.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import hashlib
import os
from dataclasses import dataclass

from ..connection import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Database migration definition"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: Optional[str] = None
    up_function: Optional[Callable] = None
    down_function: Optional[Callable] = None
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Calculate checksum after initialization"""
        if self.checksum is None:
            content = f"{self.version}{self.name}{self.up_sql}{self.down_sql or ''}"
            self.checksum = hashlib.md5(content.encode()).hexdigest()


class MigrationManager:
    """Manages database migrations and schema evolution"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize migration manager
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager or get_db_manager()
        self.migrations: List[Migration] = []
        self.migrations_dir = Path(__file__).parent / "versions"
        self.migrations_dir.mkdir(exist_ok=True)
    
    async def initialize(self) -> bool:
        """
        Initialize migration system
        
        Returns:
            bool: True if successful
        """
        try:
            # Create migrations table if it doesn't exist
            await self._create_migrations_table()
            
            # Load migrations from files
            await self._load_migrations()
            
            logger.info("Migration manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize migration manager: {e}")
            return False
    
    async def _create_migrations_table(self) -> None:
        """Create migrations tracking table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            checksum VARCHAR(32) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            execution_time_seconds NUMERIC(10,3),
            applied_by VARCHAR(255) DEFAULT 'system'
        );
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version);
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at ON schema_migrations(applied_at);
        """
        
        async with self.db_manager.get_connection() as conn:
            await conn.execute(create_table_sql)
    
    async def _load_migrations(self) -> None:
        """Load migrations from files"""
        self.migrations.clear()
        
        # Add built-in migrations
        self._add_builtin_migrations()
        
        # Load migrations from files
        if self.migrations_dir.exists():
            for migration_file in sorted(self.migrations_dir.glob("*.py")):
                try:
                    await self._load_migration_file(migration_file)
                except Exception as e:
                    logger.warning(f"Failed to load migration file {migration_file}: {e}")
        
        # Sort migrations by version
        self.migrations.sort(key=lambda m: m.version)
    
    def _add_builtin_migrations(self) -> None:
        """Add built-in migrations"""
        
        # Initial schema migration
        initial_schema_sql = """
        -- Enable UUID extension
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "btree_gin";
        
        -- Create initial tables (from schema.sql)
        -- This would include the full schema from schema.sql
        """
        
        self.migrations.append(Migration(
            version="001",
            name="initial_schema",
            description="Create initial database schema",
            up_sql=initial_schema_sql,
            down_sql="-- Drop all tables (implement if needed)"
        ))
        
        # Data retention policies migration
        retention_sql = """
        -- Create data retention configuration
        INSERT INTO system_configuration (config_key, config_value, description) VALUES
        ('data_retention_workflow_executions_days', '30', 'Days to retain completed workflow executions'),
        ('data_retention_metrics_days', '90', 'Days to retain metrics data'),
        ('data_retention_audit_logs_days', '365', 'Days to retain audit logs'),
        ('data_retention_notifications_days', '7', 'Days to retain sent notifications')
        ON CONFLICT (config_key) DO NOTHING;
        
        -- Create cleanup function
        CREATE OR REPLACE FUNCTION cleanup_old_data()
        RETURNS void AS $$
        DECLARE
            workflow_retention_days INTEGER;
            metrics_retention_days INTEGER;
            audit_retention_days INTEGER;
            notification_retention_days INTEGER;
        BEGIN
            -- Get retention policies
            SELECT (config_value->>'data_retention_workflow_executions_days')::INTEGER INTO workflow_retention_days
            FROM system_configuration WHERE config_key = 'data_retention_workflow_executions_days';
            
            SELECT (config_value->>'data_retention_metrics_days')::INTEGER INTO metrics_retention_days
            FROM system_configuration WHERE config_key = 'data_retention_metrics_days';
            
            SELECT (config_value->>'data_retention_audit_logs_days')::INTEGER INTO audit_retention_days
            FROM system_configuration WHERE config_key = 'data_retention_audit_logs_days';
            
            SELECT (config_value->>'data_retention_notifications_days')::INTEGER INTO notification_retention_days
            FROM system_configuration WHERE config_key = 'data_retention_notifications_days';
            
            -- Cleanup old workflow executions
            DELETE FROM workflow_executions 
            WHERE completed_at < NOW() - INTERVAL '1 day' * COALESCE(workflow_retention_days, 30)
            AND status IN ('completed', 'failed', 'cancelled');
            
            -- Cleanup old metrics
            DELETE FROM devops_metrics 
            WHERE created_at < NOW() - INTERVAL '1 day' * COALESCE(metrics_retention_days, 90);
            
            -- Cleanup old audit logs
            DELETE FROM audit_logs 
            WHERE timestamp < NOW() - INTERVAL '1 day' * COALESCE(audit_retention_days, 365);
            
            -- Cleanup old notifications
            DELETE FROM notifications 
            WHERE sent_at < NOW() - INTERVAL '1 day' * COALESCE(notification_retention_days, 7)
            AND status = 'sent';
            
            RAISE NOTICE 'Data cleanup completed';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        self.migrations.append(Migration(
            version="002",
            name="data_retention_policies",
            description="Add data retention policies and cleanup procedures",
            up_sql=retention_sql,
            down_sql="DROP FUNCTION IF EXISTS cleanup_old_data();"
        ))
        
        # Performance optimization migration
        optimization_sql = """
        -- Additional indexes for performance
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_executions_completed_status 
        ON workflow_executions(completed_at, status) 
        WHERE status IN ('completed', 'failed', 'cancelled');
        
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_devops_metrics_created_type 
        ON devops_metrics(created_at, metric_type);
        
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_sent_status 
        ON notifications(sent_at, status) 
        WHERE status = 'sent';
        
        -- Partitioning for large tables (example for metrics)
        -- This would be implemented based on actual data volume needs
        """
        
        self.migrations.append(Migration(
            version="003", 
            name="performance_optimization",
            description="Add performance optimizations and indexes",
            up_sql=optimization_sql,
            down_sql="-- Drop performance indexes if needed"
        ))
    
    async def _load_migration_file(self, migration_file: Path) -> None:
        """Load migration from Python file"""
        # This would implement loading migrations from Python files
        # For now, we'll focus on SQL-based migrations
        pass
    
    async def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """
        Get list of applied migrations
        
        Returns:
            List of applied migration records
        """
        query = """
        SELECT version, name, description, checksum, applied_at, execution_time_seconds
        FROM schema_migrations
        ORDER BY version
        """
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations
        
        Returns:
            List of migrations that haven't been applied
        """
        applied_migrations = await self.get_applied_migrations()
        applied_versions = {m['version'] for m in applied_migrations}
        
        return [m for m in self.migrations if m.version not in applied_versions]
    
    async def validate_migrations(self) -> Dict[str, Any]:
        """
        Validate applied migrations against current definitions
        
        Returns:
            Dict with validation results
        """
        applied_migrations = await self.get_applied_migrations()
        validation_results = {
            'valid': True,
            'issues': [],
            'applied_count': len(applied_migrations),
            'available_count': len(self.migrations)
        }
        
        # Check for checksum mismatches
        migration_map = {m.version: m for m in self.migrations}
        
        for applied in applied_migrations:
            version = applied['version']
            if version in migration_map:
                current_migration = migration_map[version]
                if current_migration.checksum != applied['checksum']:
                    validation_results['valid'] = False
                    validation_results['issues'].append({
                        'type': 'checksum_mismatch',
                        'version': version,
                        'message': f"Migration {version} checksum mismatch"
                    })
        
        # Check for missing migrations
        applied_versions = {m['version'] for m in applied_migrations}
        for migration in self.migrations:
            if migration.version not in applied_versions:
                # Check if there are applied migrations with higher versions
                higher_versions = [v for v in applied_versions if v > migration.version]
                if higher_versions:
                    validation_results['valid'] = False
                    validation_results['issues'].append({
                        'type': 'missing_migration',
                        'version': migration.version,
                        'message': f"Migration {migration.version} not applied but higher versions exist"
                    })
        
        return validation_results
    
    async def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration
        
        Args:
            migration: Migration to apply
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            start_time = datetime.utcnow()
            
            async with self.db_manager.get_transaction() as conn:
                # Execute migration SQL
                if migration.up_sql:
                    await conn.execute(migration.up_sql)
                
                # Execute migration function if provided
                if migration.up_function:
                    if asyncio.iscoroutinefunction(migration.up_function):
                        await migration.up_function(conn)
                    else:
                        migration.up_function(conn)
                
                # Record migration as applied
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                await conn.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, description, checksum, execution_time_seconds)
                    VALUES ($1, $2, $3, $4, $5)
                """, migration.version, migration.name, migration.description, 
                migration.checksum, execution_time)
            
            logger.info(f"Migration {migration.version} applied successfully in {execution_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False
    
    async def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a migration
        
        Args:
            migration: Migration to rollback
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Rolling back migration {migration.version}: {migration.name}")
            
            async with self.db_manager.get_transaction() as conn:
                # Execute rollback SQL
                if migration.down_sql:
                    await conn.execute(migration.down_sql)
                
                # Execute rollback function if provided
                if migration.down_function:
                    if asyncio.iscoroutinefunction(migration.down_function):
                        await migration.down_function(conn)
                    else:
                        migration.down_function(conn)
                
                # Remove migration record
                await conn.execute("""
                    DELETE FROM schema_migrations WHERE version = $1
                """, migration.version)
            
            logger.info(f"Migration {migration.version} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            return False
    
    async def migrate_to_latest(self) -> Dict[str, Any]:
        """
        Apply all pending migrations
        
        Returns:
            Dict with migration results
        """
        pending_migrations = await self.get_pending_migrations()
        
        results = {
            'success': True,
            'applied_count': 0,
            'failed_migrations': [],
            'total_pending': len(pending_migrations)
        }
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return results
        
        logger.info(f"Applying {len(pending_migrations)} pending migrations")
        
        for migration in pending_migrations:
            success = await self.apply_migration(migration)
            if success:
                results['applied_count'] += 1
            else:
                results['success'] = False
                results['failed_migrations'].append(migration.version)
                # Stop on first failure to maintain consistency
                break
        
        logger.info(f"Migration completed: {results['applied_count']}/{results['total_pending']} applied")
        return results
    
    async def migrate_to_version(self, target_version: str) -> Dict[str, Any]:
        """
        Migrate to specific version
        
        Args:
            target_version: Target migration version
            
        Returns:
            Dict with migration results
        """
        applied_migrations = await self.get_applied_migrations()
        current_versions = {m['version'] for m in applied_migrations}
        
        # Find target migration
        target_migration = None
        for migration in self.migrations:
            if migration.version == target_version:
                target_migration = migration
                break
        
        if not target_migration:
            return {
                'success': False,
                'error': f"Migration version {target_version} not found"
            }
        
        # Determine if we need to migrate up or down
        if target_version in current_versions:
            return {
                'success': True,
                'message': f"Already at version {target_version}",
                'applied_count': 0
            }
        
        # For now, only support migrating up to target version
        pending_migrations = []
        for migration in self.migrations:
            if migration.version <= target_version and migration.version not in current_versions:
                pending_migrations.append(migration)
        
        results = {
            'success': True,
            'applied_count': 0,
            'failed_migrations': [],
            'target_version': target_version
        }
        
        for migration in pending_migrations:
            success = await self.apply_migration(migration)
            if success:
                results['applied_count'] += 1
            else:
                results['success'] = False
                results['failed_migrations'].append(migration.version)
                break
        
        return results
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status
        
        Returns:
            Dict with migration status information
        """
        applied_migrations = await self.get_applied_migrations()
        pending_migrations = await self.get_pending_migrations()
        validation_results = await self.validate_migrations()
        
        current_version = None
        if applied_migrations:
            current_version = max(m['version'] for m in applied_migrations)
        
        latest_version = None
        if self.migrations:
            latest_version = max(m.version for m in self.migrations)
        
        return {
            'current_version': current_version,
            'latest_version': latest_version,
            'applied_count': len(applied_migrations),
            'pending_count': len(pending_migrations),
            'total_migrations': len(self.migrations),
            'is_up_to_date': len(pending_migrations) == 0,
            'validation': validation_results,
            'applied_migrations': applied_migrations,
            'pending_migrations': [
                {
                    'version': m.version,
                    'name': m.name,
                    'description': m.description
                } for m in pending_migrations
            ]
        }


# Convenience functions
async def get_migration_manager() -> MigrationManager:
    """Get initialized migration manager"""
    manager = MigrationManager()
    await manager.initialize()
    return manager


async def migrate_database(target_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Run database migrations
    
    Args:
        target_version: Target version (latest if None)
        
    Returns:
        Migration results
    """
    manager = await get_migration_manager()
    
    if target_version:
        return await manager.migrate_to_version(target_version)
    else:
        return await manager.migrate_to_latest()


async def get_database_migration_status() -> Dict[str, Any]:
    """Get database migration status"""
    manager = await get_migration_manager()
    return await manager.get_migration_status()