"""DevOps CLI Commands

Command-line interface for DevOps orchestration functionality.
"""

import asyncio
import click
import json
from typing import Optional
from datetime import datetime

# Redis-only mode for demo - no PostgreSQL dependencies
try:
    from ..cache.redis_client import get_redis_manager
except ImportError:
    # Fallback for testing without cache module
    def get_redis_manager():
        return None


@click.group()
def devops():
    """DevOps orchestration commands"""
    pass


@devops.command()
@click.option('--check-redis', is_flag=True, help='Check Redis connectivity')
@click.option('--check-all', is_flag=True, help='Check Redis connectivity (Redis-only mode)')
def health(check_redis: bool, check_all: bool):
    """Check infrastructure health (Redis-only mode)"""
    
    async def run_health_checks():
        results = {}
        
        if check_all or check_redis or not any([check_redis, check_all]):
            click.echo("Checking Redis connectivity...")
            redis_manager = get_redis_manager()
            
            if redis_manager is None:
                click.echo("❌ Redis: Redis client not available")
                return {"redis": {"healthy": False, "error": "Redis client not available"}}
            
            try:
                await redis_manager.initialize()
                redis_health = await redis_manager.check_health()
                results['redis'] = redis_health
                
                if redis_health.get('healthy', False):
                    ping_time = redis_health.get('ping_time_seconds', 0)
                    click.echo(f"✅ Redis: Healthy (ping time: {ping_time:.3f}s)")
                else:
                    click.echo(f"❌ Redis: {redis_health.get('error', 'Unknown error')}")
                
                await redis_manager.close()
            except Exception as e:
                click.echo(f"❌ Redis: Connection failed - {str(e)}")
                results['redis'] = {"healthy": False, "error": str(e)}
        
        # Overall status
        all_healthy = all(
            result.get('healthy', False) 
            for result in results.values()
        )
        
        if all_healthy:
            click.echo("\n🎉 Redis infrastructure is healthy!")
        else:
            click.echo("\n⚠️  Redis infrastructure has issues")
        
        return results
    
    return asyncio.run(run_health_checks())


# PostgreSQL-dependent commands removed for Redis-only demo mode


@devops.command()
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'yaml']), help='Output format')
def config():
    """Show current configuration (Redis-only mode)"""
    
    config_data = {
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'mode': 'demo'
        },
        'devops': {
            'mode': 'redis_only',
            'features': [
                'git_monitoring',
                'dashboard', 
                'health_checks',
                'workflow_orchestration'
            ]
        }
    }
    
    if output_format == 'json':
        click.echo(json.dumps(config_data, indent=2))
    else:
        import yaml
        click.echo(yaml.dump(config_data, default_flow_style=False))


@devops.command()
def init():
    """Initialize DevOps infrastructure (Redis-only mode)"""
    
    async def initialize():
        click.echo("🚀 Initializing DevOps infrastructure (Redis-only mode)...")
        
        # Initialize Redis
        click.echo("1. Initializing Redis connection...")
        redis_manager = get_redis_manager()
        
        if redis_manager is None:
            click.echo("❌ Redis client not available")
            return False
        
        try:
            redis_success = await redis_manager.initialize()
            
            if not redis_success:
                click.echo("❌ Redis initialization failed")
                return False
            
            # Test connectivity
            click.echo("2. Testing Redis connectivity...")
            redis_health = await redis_manager.check_health()
            
            if redis_health.get('healthy', False):
                click.echo("✅ DevOps infrastructure initialized successfully!")
                click.echo(f"   Redis: Connected (version {redis_health.get('redis_version', 'unknown')})")
                click.echo("   Mode: Demo (Redis-only)")
                click.echo("   Features: git-monitor, dashboard, health-checks")
            else:
                click.echo("⚠️  Redis connection has issues")
                click.echo(f"   Error: {redis_health.get('error', 'Unknown error')}")
            
            # Cleanup
            await redis_manager.close()
            return redis_health.get('healthy', False)
            
        except Exception as e:
            click.echo(f"❌ Initialization failed: {str(e)}")
            return False
    
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
        try:
            from .integrations.git_events import GitEventDetector
        except ImportError:
            click.echo("❌ Git event detector not available")
            return
        
        click.echo(f"🔍 Starting Git monitoring for {repo}")
        click.echo(f"📊 Monitoring events: {events}")
        click.echo(f"⏱️  Check interval: {interval}s")
        click.echo("Press Ctrl+C to stop monitoring...")
        
        # Get Redis manager for event storage
        redis_manager = get_redis_manager()
        redis_client = None
        
        if redis_manager:
            try:
                await redis_manager.initialize()
                redis_client = redis_manager
                click.echo("✅ Redis connected for event storage")
            except Exception as e:
                click.echo(f"⚠️  Redis unavailable, using memory-only mode: {e}")
        
        detector = GitEventDetector(redis_client=redis_client)
        
        # Add the repository to monitor
        if not detector.add_repository(repo):
            click.echo("❌ Failed to add repository for monitoring")
            return
        
        # Get the actual key used by add_repository (resolved path)
        from pathlib import Path
        repo_key = str(Path(repo).resolve())
        
        click.echo("✅ Repository added to monitoring")
        
        try:
            event_count = 0
            while True:
                # Check for events manually since we're not using the automatic polling
                repo_state = detector.monitored_repos.get(repo_key)
                if repo_state:
                    events_found = await detector._detect_events(repo_key, repo_state)
                    if events_found:
                        click.echo(f"📋 Found {len(events_found)} new events")
                        for event in events_found:
                            event_count += 1
                            click.echo(f"   • {event.event_type.value}: {event.message or event.branch or 'N/A'}")
                            # Emit event to handlers
                            await detector._emit_event(event)
                    elif event_count == 0:
                        # First run, show status
                        click.echo("📊 Monitoring active, waiting for Git events...")
                        event_count = -1  # Mark as initialized
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping Git monitor...")
        finally:
            if redis_client:
                await redis_client.close()
    
    asyncio.run(run_monitor())


@devops.command()
@click.option('--host', default='0.0.0.0', help='Dashboard host')
@click.option('--port', default=8000, help='Dashboard port')
def dashboard(host: str, port: int):
    """Launch monitoring dashboard"""
    async def run_dashboard():
        try:
            from .analytics.dashboard import DashboardMetricsCollector, GitOpsDashboard
            from .integrations.git_events import GitEventDetector
        except ImportError as e:
            click.echo(f"❌ Dashboard components not available: {e}")
            return
        
        click.echo(f"🚀 Starting GitOps Dashboard on http://{host}:{port}")
        click.echo("📊 Dashboard features:")
        click.echo("   • Real-time Git events")
        click.echo("   • System health metrics")
        click.echo("   • Workflow monitoring")
        click.echo("   • API endpoints")
        click.echo("Press Ctrl+C to stop dashboard...")
        
        # Initialize Redis connection
        redis_manager = get_redis_manager()
        redis_client = None
        
        if redis_manager:
            try:
                await redis_manager.initialize()
                redis_client = redis_manager
                click.echo("✅ Redis connected for dashboard data")
            except Exception as e:
                click.echo(f"⚠️  Redis unavailable, using demo mode: {e}")
        
        # Initialize components
        git_detector = GitEventDetector(redis_client=redis_client)
        metrics_collector = DashboardMetricsCollector(
            redis_client=redis_client,
            git_event_detector=git_detector
        )
        dashboard = GitOpsDashboard(metrics_collector, host=host, port=port)
        
        try:
            await dashboard.start()
            click.echo(f"✅ Dashboard running at http://{host}:{port}")
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            click.echo("\n🛑 Stopping dashboard...")
        except Exception as e:
            click.echo(f"❌ Dashboard error: {e}")
        finally:
            try:
                await dashboard.stop()
                if redis_client:
                    await redis_client.close()
            except:
                pass
    
    asyncio.run(run_dashboard())


if __name__ == '__main__':
    devops()