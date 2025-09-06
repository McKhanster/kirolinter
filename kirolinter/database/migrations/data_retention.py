"""Data Retention Manager

Handles data retention policies and cleanup for KiroLinter DevOps orchestration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..connection import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Data retention policy definition"""
    table_name: str
    retention_days: int
    date_column: str = 'created_at'
    condition: Optional[str] = None
    description: Optional[str] = None


class DataRetentionManager:
    """Manages data retention policies and cleanup operations"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize data retention manager
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager or get_db_manager()
        self.policies: List[RetentionPolicy] = []
        self._load_default_policies()
    
    def _load_default_policies(self) -> None:
        """Load default retention policies"""
        self.policies = [
            RetentionPolicy(
                table_name="workflow_executions",
                retention_days=30,
                date_column="completed_at",
                condition="status IN ('completed', 'failed', 'cancelled')",
                description="Completed workflow executions"
            ),
            RetentionPolicy(
                table_name="workflow_stage_results",
                retention_days=30,
                date_column="created_at",
                condition="workflow_execution_id IN (SELECT id FROM workflow_executions WHERE completed_at < NOW() - INTERVAL '%d days' AND status IN ('completed', 'failed', 'cancelled'))",
                description="Stage results for completed workflows"
            ),
            RetentionPolicy(
                table_name="devops_metrics",
                retention_days=90,
                date_column="created_at",
                description="DevOps metrics data"
            ),
            RetentionPolicy(
                table_name="quality_gate_executions",
                retention_days=60,
                date_column="created_at",
                condition="workflow_execution_id IN (SELECT id FROM workflow_executions WHERE completed_at < NOW() - INTERVAL '%d days' AND status IN ('completed', 'failed', 'cancelled'))",
                description="Quality gate executions for completed workflows"
            ),
            RetentionPolicy(
                table_name="pipeline_executions",
                retention_days=90,
                date_column="completed_at",
                condition="status IN ('success', 'failed', 'cancelled')",
                description="Completed pipeline executions"
            ),
            RetentionPolicy(
                table_name="risk_assessments",
                retention_days=180,
                date_column="assessed_at",
                condition="expires_at IS NOT NULL AND expires_at < NOW()",
                description="Expired risk assessments"
            ),
            RetentionPolicy(
                table_name="deployments",
                retention_days=365,
                date_column="completed_at",
                condition="status IN ('success', 'failed', 'rolled_back')",
                description="Completed deployments"
            ),
            RetentionPolicy(
                table_name="notifications",
                retention_days=7,
                date_column="sent_at",
                condition="status = 'sent'",
                description="Sent notifications"
            ),
            RetentionPolicy(
                table_name="audit_logs",
                retention_days=365,
                date_column="timestamp",
                description="Audit log entries"
            ),
            RetentionPolicy(
                table_name="analytics_aggregations",
                retention_days=730,  # 2 years
                date_column="created_at",
                description="Analytics aggregation data"
            )
        ]
    
    async def get_retention_configuration(self) -> Dict[str, int]:
        """
        Get retention configuration from database
        
        Returns:
            Dict mapping table names to retention days
        """
        try:
            query = """
            SELECT config_key, config_value
            FROM system_configuration
            WHERE config_key LIKE 'data_retention_%_days'
            """
            
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(query)
                
                config = {}
                for row in rows:
                    key = row['config_key']
                    # Extract table name from config key
                    # e.g., 'data_retention_workflow_executions_days' -> 'workflow_executions'
                    if key.startswith('data_retention_') and key.endswith('_days'):
                        table_name = key[15:-5]  # Remove prefix and suffix
                        try:
                            config[table_name] = int(row['config_value'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid retention value for {key}: {row['config_value']}")
                
                return config
                
        except Exception as e:
            logger.error(f"Failed to get retention configuration: {e}")
            return {}
    
    async def update_retention_policy(self, table_name: str, retention_days: int) -> bool:
        """
        Update retention policy for a table
        
        Args:
            table_name: Name of the table
            retention_days: Number of days to retain data
            
        Returns:
            bool: True if successful
        """
        try:
            config_key = f"data_retention_{table_name}_days"
            
            query = """
            INSERT INTO system_configuration (config_key, config_value, description, updated_by)
            VALUES ($1, $2, $3, 'data_retention_manager')
            ON CONFLICT (config_key) 
            DO UPDATE SET 
                config_value = EXCLUDED.config_value,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """
            
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    query,
                    config_key,
                    str(retention_days),
                    f"Data retention policy for {table_name} table"
                )
            
            # Update local policy
            for policy in self.policies:
                if policy.table_name == table_name:
                    policy.retention_days = retention_days
                    break
            
            logger.info(f"Updated retention policy for {table_name}: {retention_days} days")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update retention policy for {table_name}: {e}")
            return False
    
    async def get_data_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get data statistics for all tables with retention policies
        
        Returns:
            Dict with statistics for each table
        """
        statistics = {}
        
        for policy in self.policies:
            try:
                # Get total record count
                count_query = f"SELECT COUNT(*) as total_count FROM {policy.table_name}"
                
                # Get old record count (beyond retention period)
                cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
                old_count_query = f"""
                SELECT COUNT(*) as old_count 
                FROM {policy.table_name} 
                WHERE {policy.date_column} < $1
                """
                
                if policy.condition:
                    # Handle parameterized conditions
                    if '%d' in policy.condition:
                        condition = policy.condition % policy.retention_days
                    else:
                        condition = policy.condition
                    old_count_query += f" AND ({condition})"
                
                # Get size estimate (PostgreSQL specific)
                size_query = f"""
                SELECT pg_total_relation_size('{policy.table_name}') as table_size_bytes
                """
                
                async with self.db_manager.get_connection() as conn:
                    # Get counts
                    total_result = await conn.fetchrow(count_query)
                    old_result = await conn.fetchrow(old_count_query, cutoff_date)
                    size_result = await conn.fetchrow(size_query)
                    
                    # Get oldest record date
                    oldest_query = f"""
                    SELECT MIN({policy.date_column}) as oldest_date 
                    FROM {policy.table_name}
                    WHERE {policy.date_column} IS NOT NULL
                    """
                    oldest_result = await conn.fetchrow(oldest_query)
                    
                    statistics[policy.table_name] = {
                        'total_records': total_result['total_count'],
                        'old_records': old_result['old_count'],
                        'retention_days': policy.retention_days,
                        'cutoff_date': cutoff_date.isoformat(),
                        'oldest_record': oldest_result['oldest_date'].isoformat() if oldest_result['oldest_date'] else None,
                        'table_size_bytes': size_result['table_size_bytes'],
                        'table_size_mb': round(size_result['table_size_bytes'] / (1024 * 1024), 2),
                        'description': policy.description
                    }
                    
            except Exception as e:
                logger.error(f"Failed to get statistics for {policy.table_name}: {e}")
                statistics[policy.table_name] = {
                    'error': str(e),
                    'retention_days': policy.retention_days,
                    'description': policy.description
                }
        
        return statistics
    
    async def cleanup_old_data(self, dry_run: bool = False, 
                              table_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Clean up old data according to retention policies
        
        Args:
            dry_run: If True, only simulate cleanup without deleting
            table_names: Specific tables to clean up (all if None)
            
        Returns:
            Dict with cleanup results
        """
        results = {
            'success': True,
            'dry_run': dry_run,
            'tables_processed': 0,
            'total_deleted': 0,
            'table_results': {},
            'errors': []
        }
        
        # Get current retention configuration
        retention_config = await self.get_retention_configuration()
        
        # Filter policies if specific tables requested
        policies_to_process = self.policies
        if table_names:
            policies_to_process = [p for p in self.policies if p.table_name in table_names]
        
        logger.info(f"Starting data cleanup ({'DRY RUN' if dry_run else 'LIVE'}) for {len(policies_to_process)} tables")
        
        for policy in policies_to_process:
            try:
                # Use configured retention days if available
                retention_days = retention_config.get(policy.table_name, policy.retention_days)
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Build delete query
                delete_query = f"""
                DELETE FROM {policy.table_name} 
                WHERE {policy.date_column} < $1
                """
                
                if policy.condition:
                    # Handle parameterized conditions
                    if '%d' in policy.condition:
                        condition = policy.condition % retention_days
                    else:
                        condition = policy.condition
                    delete_query += f" AND ({condition})"
                
                if dry_run:
                    # For dry run, just count records that would be deleted
                    count_query = delete_query.replace("DELETE FROM", "SELECT COUNT(*) as count FROM")
                    
                    async with self.db_manager.get_connection() as conn:
                        result = await conn.fetchrow(count_query, cutoff_date)
                        deleted_count = result['count']
                else:
                    # Actually delete the records
                    async with self.db_manager.get_connection() as conn:
                        result = await conn.execute(delete_query, cutoff_date)
                        # Parse result string like "DELETE 123"
                        deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                
                results['table_results'][policy.table_name] = {
                    'deleted_count': deleted_count,
                    'retention_days': retention_days,
                    'cutoff_date': cutoff_date.isoformat(),
                    'success': True
                }
                
                results['total_deleted'] += deleted_count
                results['tables_processed'] += 1
                
                logger.info(f"{'Would delete' if dry_run else 'Deleted'} {deleted_count} records from {policy.table_name}")
                
            except Exception as e:
                error_msg = f"Failed to cleanup {policy.table_name}: {e}"
                logger.error(error_msg)
                
                results['success'] = False
                results['errors'].append(error_msg)
                results['table_results'][policy.table_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        logger.info(f"Data cleanup completed: {results['total_deleted']} records {'would be' if dry_run else ''} deleted from {results['tables_processed']} tables")
        return results
    
    async def schedule_cleanup_task(self) -> bool:
        """
        Schedule automatic cleanup task
        
        Returns:
            bool: True if successful
        """
        try:
            # This would integrate with Celery to schedule periodic cleanup
            from kirolinter.workers.celery_app import app
            
            # Schedule daily cleanup at 2 AM
            app.conf.beat_schedule = app.conf.beat_schedule or {}
            app.conf.beat_schedule['data-retention-cleanup'] = {
                'task': 'kirolinter.workers.analytics_worker.cleanup_old_data',
                'schedule': 60 * 60 * 24,  # Daily
                'options': {'queue': 'analytics'}
            }
            
            logger.info("Scheduled automatic data cleanup task")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule cleanup task: {e}")
            return False
    
    async def get_cleanup_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for data cleanup
        
        Returns:
            Dict with cleanup recommendations
        """
        statistics = await self.get_data_statistics()
        recommendations = {
            'total_old_records': 0,
            'total_size_savings_mb': 0,
            'tables_needing_cleanup': [],
            'recommendations': []
        }
        
        for table_name, stats in statistics.items():
            if 'error' in stats:
                continue
                
            old_records = stats.get('old_records', 0)
            total_records = stats.get('total_records', 0)
            table_size_mb = stats.get('table_size_mb', 0)
            
            if old_records > 0:
                recommendations['total_old_records'] += old_records
                
                # Estimate size savings (proportional to record count)
                if total_records > 0:
                    size_savings = (old_records / total_records) * table_size_mb
                    recommendations['total_size_savings_mb'] += size_savings
                
                recommendations['tables_needing_cleanup'].append({
                    'table_name': table_name,
                    'old_records': old_records,
                    'total_records': total_records,
                    'percentage_old': round((old_records / total_records) * 100, 1) if total_records > 0 else 0,
                    'estimated_size_savings_mb': round(size_savings, 2) if total_records > 0 else 0,
                    'retention_days': stats['retention_days'],
                    'description': stats.get('description', '')
                })
        
        # Generate recommendations
        if recommendations['total_old_records'] > 1000:
            recommendations['recommendations'].append({
                'priority': 'high',
                'message': f"Consider running data cleanup - {recommendations['total_old_records']} old records found"
            })
        
        if recommendations['total_size_savings_mb'] > 100:
            recommendations['recommendations'].append({
                'priority': 'medium',
                'message': f"Cleanup could free up ~{recommendations['total_size_savings_mb']:.1f} MB of storage"
            })
        
        # Sort tables by number of old records
        recommendations['tables_needing_cleanup'].sort(key=lambda x: x['old_records'], reverse=True)
        
        return recommendations


# Convenience functions
async def get_data_retention_manager() -> DataRetentionManager:
    """Get data retention manager instance"""
    return DataRetentionManager()


async def cleanup_old_data(dry_run: bool = False, table_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Clean up old data according to retention policies
    
    Args:
        dry_run: If True, only simulate cleanup
        table_names: Specific tables to clean up
        
    Returns:
        Cleanup results
    """
    manager = await get_data_retention_manager()
    return await manager.cleanup_old_data(dry_run=dry_run, table_names=table_names)


async def get_data_statistics() -> Dict[str, Dict[str, Any]]:
    """Get data statistics for all tables"""
    manager = await get_data_retention_manager()
    return await manager.get_data_statistics()


async def get_cleanup_recommendations() -> Dict[str, Any]:
    """Get cleanup recommendations"""
    manager = await get_data_retention_manager()
    return await manager.get_cleanup_recommendations()