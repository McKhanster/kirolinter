"""DevOps CLI Commands

Command-line interface for DevOps orchestration functionality.
"""

import asyncio
import click
import json
from typing import Optional
from datetime import datetime

from ..database.connection import get_db_manager
from ..cache.redis_client import get_redis_manager
from ..database.migrations.migration_manager import get_migration_manager
from ..database.migrations.data_retention import get_data_retention_manager


@click.group()
def devops():
    """DevOps orchestration commands"""
    pass


@devops.command()
@click.option('--check-db', is_flag=True, help='Check database connectivity')
@click.option('--check-redis', is_flag=True, help='Check Redis connectivity')
@click.option('--check-all', is_flag=True, help='Check all infrastructure')
def health(check_db: bool, check_redis: bool, check_all: bool):
    """Check infrastructure health"""
    
    async def run_health_checks():
        results = {}
        
        if check_all or check_db:
            click.echo("Checking database connectivity...")
            db_manager = get_db_manager()
            await db_manager.initialize()
            db_health = await db_manager.check_health()
            results['database'] = db_health
            
            if db_health['healthy']:
                click.echo(f"✅ Database: Healthy (query time: {db_health['query_time_seconds']:.3f}s)")
            else:
                click.echo(f"❌ Database: {db_health['error']}")
            
            await db_manager.close()
        
        if check_all or check_redis:
            click.echo("Checking Redis connectivity...")
            redis_manager = get_redis_manager()
            await redis_manager.initialize()
            redis_health = await redis_manager.check_health()
            results['redis'] = redis_health
            
            if redis_health['healthy']:
                click.echo(f"✅ Redis: Healthy (ping time: {redis_health['ping_time_seconds']:.3f}s)")
            else:
                click.echo(f"❌ Redis: {redis_health['error']}")
            
            await redis_manager.close()
        
        if not any([check_db, check_redis, check_all]):
            click.echo("Please specify --check-db, --check-redis, or --check-all")
            return
        
        # Overall status
        all_healthy = all(
            result.get('healthy', False) 
            for result in results.values()
        )
        
        if all_healthy:
            click.echo("\n🎉 All infrastructure components are healthy!")
        else:
            click.echo("\n⚠️  Some infrastructure components have issues")
        
        return results
    
    return asyncio.run(run_health_checks())


@devops.command()
@click.option('--target-version', help='Target migration version (latest if not specified)')
def migrate(target_version: Optional[str]):
    """Run database migrations"""
    
    async def run_migrations():
        click.echo("Running database migrations...")
        
        migration_manager = await get_migration_manager()
        
        if target_version:
            result = await migration_manager.migrate_to_version(target_version)
        else:
            result = await migration_manager.migrate_to_latest()
        
        if result['success']:
            click.echo(f"✅ Migrations completed: {result['applied_count']} migrations applied")
        else:
            click.echo(f"❌ Migration failed: {result.get('error', 'Unknown error')}")
            if result.get('failed_migrations'):
                click.echo(f"Failed migrations: {', '.join(result['failed_migrations'])}")
        
        return result
    
    return asyncio.run(run_migrations())


@devops.command()
def migration_status():
    """Show migration status"""
    
    async def show_status():
        migration_manager = await get_migration_manager()
        status = await migration_manager.get_migration_status()
        
        click.echo(f"Current version: {status['current_version'] or 'None'}")
        click.echo(f"Latest version: {status['latest_version'] or 'None'}")
        click.echo(f"Applied migrations: {status['applied_count']}")
        click.echo(f"Pending migrations: {status['pending_count']}")
        click.echo(f"Up to date: {'Yes' if status['is_up_to_date'] else 'No'}")
        
        if status['validation']['valid']:
            click.echo("✅ Migration validation: Passed")
        else:
            click.echo("❌ Migration validation: Failed")
            for issue in status['validation']['issues']:
                click.echo(f"  - {issue['message']}")
        
        if status['pending_migrations']:
            click.echo("\nPending migrations:")
            for migration in status['pending_migrations']:
                click.echo(f"  - {migration['version']}: {migration['name']}")
        
        return status
    
    return asyncio.run(show_status())


@devops.command()
@click.option('--dry-run', is_flag=True, help='Simulate cleanup without deleting data')
@click.option('--tables', help='Comma-separated list of tables to clean up')
def cleanup(dry_run: bool, tables: Optional[str]):
    """Clean up old data according to retention policies"""
    
    async def run_cleanup():
        table_list = tables.split(',') if tables else None
        
        click.echo(f"Running data cleanup ({'dry run' if dry_run else 'live'})...")
        
        retention_manager = await get_data_retention_manager()
        result = await retention_manager.cleanup_old_data(
            dry_run=dry_run, 
            table_names=table_list
        )
        
        if result['success']:
            click.echo(f"✅ Cleanup completed: {result['total_deleted']} records {'would be' if dry_run else ''} deleted")
            
            for table_name, table_result in result['table_results'].items():
                if table_result.get('success'):
                    count = table_result['deleted_count']
                    click.echo(f"  - {table_name}: {count} records")
                else:
                    click.echo(f"  - {table_name}: Error - {table_result.get('error')}")
        else:
            click.echo(f"❌ Cleanup failed")
            for error in result['errors']:
                click.echo(f"  - {error}")
        
        return result
    
    return asyncio.run(run_cleanup())


@devops.command()
def data_stats():
    """Show data statistics and cleanup recommendations"""
    
    async def show_stats():
        retention_manager = await get_data_retention_manager()
        
        click.echo("Getting data statistics...")
        statistics = await retention_manager.get_data_statistics()
        
        click.echo("Getting cleanup recommendations...")
        recommendations = await retention_manager.get_cleanup_recommendations()
        
        # Show statistics
        click.echo("\n📊 Data Statistics:")
        for table_name, stats in statistics.items():
            if 'error' in stats:
                click.echo(f"  {table_name}: Error - {stats['error']}")
                continue
                
            total = stats['total_records']
            old = stats['old_records']
            size_mb = stats['table_size_mb']
            retention_days = stats['retention_days']
            
            click.echo(f"  {table_name}:")
            click.echo(f"    Total records: {total:,}")
            click.echo(f"    Old records: {old:,}")
            click.echo(f"    Size: {size_mb:.1f} MB")
            click.echo(f"    Retention: {retention_days} days")
        
        # Show recommendations
        click.echo(f"\n💡 Cleanup Recommendations:")
        click.echo(f"  Total old records: {recommendations['total_old_records']:,}")
        click.echo(f"  Potential space savings: {recommendations['total_size_savings_mb']:.1f} MB")
        
        if recommendations['recommendations']:
            for rec in recommendations['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                click.echo(f"  {priority_icon} {rec['message']}")
        
        if recommendations['tables_needing_cleanup']:
            click.echo("\n  Tables needing cleanup:")
            for table in recommendations['tables_needing_cleanup'][:5]:  # Top 5
                click.echo(f"    - {table['table_name']}: {table['old_records']:,} old records ({table['percentage_old']:.1f}%)")
        
        return {'statistics': statistics, 'recommendations': recommendations}
    
    return asyncio.run(show_stats())


@devops.command()
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'yaml']), help='Output format')
def config():
    """Show current configuration"""
    
    config_data = {
        'database': {
            'host': 'localhost',
            'port': 5432,
            'database': 'kirolinter_devops',
            'user': 'kirolinter'
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        },
        'celery': {
            'broker_url': 'redis://localhost:6379/0',
            'result_backend': 'redis://localhost:6379/0'
        }
    }
    
    if output_format == 'json':
        click.echo(json.dumps(config_data, indent=2))
    else:
        import yaml
        click.echo(yaml.dump(config_data, default_flow_style=False))


@devops.command()
def init():
    """Initialize DevOps infrastructure"""
    
    async def initialize():
        click.echo("🚀 Initializing DevOps infrastructure...")
        
        # Initialize database
        click.echo("1. Initializing database connection...")
        db_manager = get_db_manager()
        db_success = await db_manager.initialize()
        
        if not db_success:
            click.echo("❌ Database initialization failed")
            return False
        
        # Run migrations
        click.echo("2. Running database migrations...")
        migration_manager = await get_migration_manager()
        migration_result = await migration_manager.migrate_to_latest()
        
        if not migration_result['success']:
            click.echo("❌ Database migration failed")
            await db_manager.close()
            return False
        
        # Initialize Redis
        click.echo("3. Initializing Redis connection...")
        redis_manager = get_redis_manager()
        redis_success = await redis_manager.initialize()
        
        if not redis_success:
            click.echo("❌ Redis initialization failed")
            await db_manager.close()
            return False
        
        # Test connectivity
        click.echo("4. Testing connectivity...")
        db_health = await db_manager.check_health()
        redis_health = await redis_manager.check_health()
        
        if db_health['healthy'] and redis_health['healthy']:
            click.echo("✅ DevOps infrastructure initialized successfully!")
            click.echo(f"   Database: {db_health['pool_size']} connections")
            click.echo(f"   Redis: {redis_health['redis_version']}")
            click.echo(f"   Migrations: {migration_result['applied_count']} applied")
        else:
            click.echo("⚠️  Infrastructure initialized but some components have issues")
        
        # Cleanup
        await db_manager.close()
        await redis_manager.close()
        
        return True
    
    return asyncio.run(initialize())


@devops.group()
def git_monitor():
    """Git monitoring commands"""
    pass


@git_monitor.command()
@click.option('--repo', default='.', help='Repository path to monitor')
@click.option('--events', default='all', help='Events to monitor (all, commits, branches, tags)')
@click.option('--interval', default=30, help='Monitoring interval in seconds')
def start(repo: str, events: str, interval: int):
    """Start Git repository monitoring"""
    async def run_monitor():
        from .integrations.git_events import GitEventDetector
        from .analytics.dashboard import GitOpsMonitoringDashboard
        
        click.echo(f"🔍 Starting Git monitoring for {repo}")
        click.echo(f"📊 Monitoring events: {events}")
        click.echo(f"⏱️  Check interval: {interval}s")
        
        detector = GitEventDetector()
        dashboard = GitOpsMonitoringDashboard()
        
        try:
            while True:
                events_found = await detector.detect_events(repo)
                if events_found:
                    click.echo(f"📋 Found {len(events_found)} new events")
                    for event in events_found:
                        click.echo(f"   • {event.event_type.value}: {event.message or event.branch or 'N/A'}")
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping Git monitor...")
    
    asyncio.run(run_monitor())


@devops.command()
@click.option('--host', default='0.0.0.0', help='Dashboard host')
@click.option('--port', default=8000, help='Dashboard port')
def dashboard(host: str, port: int):
    """Launch monitoring dashboard"""
    async def run_dashboard():
        from .analytics.dashboard import GitOpsMonitoringDashboard
        
        click.echo(f"🚀 Starting GitOps Dashboard on http://{host}:{port}")
        click.echo("📊 Dashboard features:")
        click.echo("   • Real-time Git events")
        click.echo("   • System health metrics")
        click.echo("   • Workflow monitoring")
        click.echo("   • API endpoints")
        
        dashboard = GitOpsMonitoringDashboard()
        
        try:
            await dashboard.start_server(host=host, port=port)
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping dashboard...")
        except Exception as e:
            click.echo(f"❌ Dashboard error: {e}")
    
    asyncio.run(run_dashboard())


if __name__ == '__main__':
    devops()