#!/usr/bin/env python3
"""
KiroLinter CLI - AI-driven code review tool
"""

import asyncio
import click
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from kirolinter.core.engine import AnalysisEngine
from kirolinter.models.config import Config
from kirolinter.utils.performance_tracker import PerformanceTracker


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """KiroLinter - AI-driven code review tool for Python projects."""
    ctx.ensure_object(dict)


@cli.command()
@click.argument('target', type=str)
@click.option('--format', '-f', 
              type=click.Choice(['json', 'summary', 'detailed', 'html']), 
              default='json',
              help='Output format for the analysis report')
@click.option('--output', '-o', 
              type=click.Path(), 
              help='Output file path (default: stdout)')
@click.option('--config', '-c', 
              type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--changed-only', 
              is_flag=True, 
              help='Analyze only files changed in the last commit')
@click.option('--severity', 
              type=click.Choice(['low', 'medium', 'high', 'critical']), 
              help='Minimum severity level to report')
@click.option('--exclude', 
              multiple=True, 
              help='Patterns to exclude from analysis')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose output')
@click.option('--github-pr', 
              type=int, 
              help='Post results as comments on GitHub PR number')
@click.option('--github-token', 
              help='GitHub token for API access (overrides config)')
@click.option('--github-repo', 
              help='GitHub repository in format owner/repo (overrides config)')
@click.option('--interactive-fixes', 
              is_flag=True, 
              help='Enable interactive batch fixes with user authorization')
@click.option('--dry-run', 
              is_flag=True, 
              help='Show what fixes would be applied without making changes')
def analyze(target: str, format: str, output: Optional[str], config: Optional[str], 
           changed_only: bool, severity: Optional[str], exclude: tuple, verbose: bool,
           github_pr: Optional[int], github_token: Optional[str], github_repo: Optional[str],
           interactive_fixes: bool, dry_run: bool):
    """
    Analyze a Git repository, local codebase, or individual Python file for code quality issues.
    
    TARGET can be:
    - A Git repository URL (https://github.com/user/repo.git)
    - A local directory path (/path/to/project)
    - A single Python file (path/to/file.py)
    - Current directory (.)
    """
    try:
        # Initialize performance tracker
        tracker = PerformanceTracker()
        tracker.start()
        
        # Load configuration
        config_obj = Config.load(config) if config else Config.default()
        
        # Apply CLI overrides
        if severity:
            config_obj.min_severity = severity
        if exclude:
            config_obj.exclude_patterns.extend(exclude)
        
        # Initialize analysis engine
        engine = AnalysisEngine(config_obj, verbose=verbose)
        
        # Validate target
        if not _validate_target(target):
            click.echo(f"Error: Invalid target '{target}'", err=True)
            sys.exit(1)
        
        # Run analysis
        click.echo(f"🔍 Analyzing {'changed files in' if changed_only else ''} {target}...")
        
        with click.progressbar(length=100, label='Analyzing code') as bar:
            results = engine.analyze_codebase(
                target=target,
                changed_only=changed_only,
                progress_callback=lambda p: bar.update(p - bar.pos)
            )
        
        # Generate and output report
        report = engine.generate_report(results, format=format)
        
        if output:
            with open(output, 'w') as f:
                f.write(report)
            click.echo(f"✅ Report saved to {output}")
        else:
            click.echo(report)
        
        # Post to GitHub PR if requested
        if github_pr:
            success = engine.post_to_github_pr(
                pr_number=github_pr,
                results=results,
                github_token=github_token or config_obj.github_token,
                github_repo=github_repo or config_obj.github_repo
            )
            if success:
                click.echo(f"✅ Results posted to GitHub PR #{github_pr}")
            else:
                click.echo(f"❌ Failed to post to GitHub PR #{github_pr}", err=True)
        
        # Interactive fixes if requested
        if interactive_fixes or dry_run:
            from kirolinter.core.interactive_fixer import InteractiveFixer
            fixer = InteractiveFixer(verbose=verbose)
            
            if dry_run:
                click.echo("\n🔍 Dry run mode - showing potential fixes without applying:")
                fixer.show_potential_fixes(results)
            else:
                click.echo("\n🔧 Interactive fixes mode:")
                fixes_applied = fixer.apply_interactive_fixes(results)
                if fixes_applied > 0:
                    click.echo(f"✅ Applied {fixes_applied} fixes successfully")
                else:
                    click.echo("ℹ️  No fixes were applied")
        
        # Performance summary
        elapsed = tracker.stop()
        if verbose:
            click.echo(f"\n⏱️  Analysis completed in {elapsed:.2f} seconds")
            
        # Exit with appropriate code
        if results.has_critical_issues():
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n❌ Analysis interrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"❌ Analysis failed: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command('init')
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
def config_init(force: bool):
    """Initialize a new configuration file."""
    config_path = Path('.kirolinter.yaml')
    
    if config_path.exists() and not force:
        click.echo(f"Configuration file already exists at {config_path}")
        click.echo("Use --force to overwrite")
        return
    
    # Create default configuration
    default_config = Config.default()
    default_config.save(config_path)
    
    click.echo(f"✅ Configuration file created at {config_path}")


@config.command('validate')
@click.argument('config_file', type=click.Path(exists=True))
def config_validate(config_file: str):
    """Validate a configuration file."""
    try:
        config_obj = Config.load(config_file)
        click.echo("✅ Configuration file is valid")
        
        # Show summary
        click.echo(f"Rules enabled: {len(config_obj.enabled_rules)}")
        click.echo(f"Minimum severity: {config_obj.min_severity}")
        click.echo(f"Exclude patterns: {len(config_obj.exclude_patterns)}")
        
    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def github():
    """GitHub integration commands."""
    pass


@github.command('setup')
@click.option('--token', prompt=True, hide_input=True, help='GitHub personal access token')
def github_setup(token: str):
    """Set up GitHub integration."""
    # TODO: Implement GitHub authentication setup
    click.echo("🔧 GitHub integration setup (coming soon)")


@github.command('review')
@click.option('--pr-number', type=int, required=True, help='Pull request number')
@click.option('--repo', required=True, help='Repository in format owner/repo')
def github_review(pr_number: int, repo: str):
    """Analyze a GitHub pull request and post review comments."""
    # TODO: Implement GitHub PR review
    click.echo(f"🔍 Reviewing PR #{pr_number} in {repo} (coming soon)")


# AI Agent System Commands
@cli.group()
def agent():
    """AI Agent System commands for autonomous code quality management."""
    pass


# Background Daemon Commands
@cli.group()
def daemon():
    """Background daemon commands for continuous monitoring."""
    pass


# DevOps Orchestration Commands (Redis-only demo mode)
@cli.group()
def devops():
    """DevOps orchestration and workflow management commands."""
    pass


@devops.command()
@click.option('--check-redis', is_flag=True, help='Check Redis connectivity')
@click.option('--check-all', is_flag=True, help='Check Redis connectivity (Redis-only mode)')
def health(check_redis: bool, check_all: bool):
    """Check DevOps infrastructure health (Redis-only mode)"""
    
    async def run_health_checks():
        results = {}
        
        if check_all or check_redis or not any([check_redis, check_all]):
            click.echo("Checking Redis connectivity...")
            try:
                from kirolinter.cache.redis_client import get_redis_manager
                redis_manager = get_redis_manager()
            except ImportError:
                click.echo("❌ Redis: Redis client not available")
                return {"redis": {"healthy": False, "error": "Redis client not available"}}
            
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


@devops.command()
def init():
    """Initialize DevOps infrastructure (Redis-only mode)"""
    
    async def initialize():
        click.echo("🚀 Initializing DevOps infrastructure (Redis-only mode)...")
        
        # Initialize Redis
        click.echo("1. Initializing Redis connection...")
        try:
            from kirolinter.cache.redis_client import get_redis_manager
            redis_manager = get_redis_manager()
        except ImportError:
            click.echo("❌ Redis client not available")
            return False
        
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
            from kirolinter.devops.integrations.git_events import GitEventDetector
        except ImportError as e:
            click.echo(f"❌ Git event detector not available: {e}")
            return
        except Exception as e:
            click.echo(f"❌ Unexpected import error: {e}")
            return
        
        click.echo(f"🔍 Starting Git monitoring for {repo}")
        click.echo(f"📊 Monitoring events: {events}")
        click.echo(f"⏱️  Check interval: {interval}s")
        click.echo("Press Ctrl+C to stop monitoring...")
        
        # Get Redis manager for event storage
        try:
            from kirolinter.cache.redis_client import get_redis_manager
            redis_manager = get_redis_manager()
            redis_client = None
            
            if redis_manager:
                try:
                    await redis_manager.initialize()
                    redis_client = redis_manager
                    click.echo("✅ Redis connected for event storage")
                except Exception as e:
                    click.echo(f"⚠️  Redis unavailable, using memory-only mode: {e}")
        except ImportError:
            click.echo("⚠️  Redis client not available, using memory-only mode")
            redis_client = None
        
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
            from kirolinter.devops.analytics.dashboard import DashboardMetricsCollector, GitOpsDashboard
            from kirolinter.devops.integrations.git_events import GitEventDetector
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
        try:
            from kirolinter.cache.redis_client import get_redis_manager
            redis_manager = get_redis_manager()
            redis_client = None
            
            if redis_manager:
                try:
                    await redis_manager.initialize()
                    redis_client = redis_manager
                    click.echo("✅ Redis connected for dashboard data")
                except Exception as e:
                    click.echo(f"⚠️  Redis unavailable, using demo mode: {e}")
        except ImportError:
            click.echo("⚠️  Redis client not available, using demo mode")
            redis_client = None
        
        # Initialize components
        git_detector = GitEventDetector(redis_client=redis_client)
        
        # Add the current repository to the detector so it knows what to check
        # This doesn't start monitoring, just registers the repo for status checks
        import os
        repo_path = os.getcwd()
        if os.path.exists(os.path.join(repo_path, '.git')):
            git_detector.add_repository(repo_path)
        
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


@agent.command('review')
@click.option('--repo', required=True, help='Repository path or URL to analyze')
@click.option('--config', type=click.Path(exists=True), help='Configuration file path')
@click.option('--model', type=click.Choice(['xai', 'ollama', 'openai', 'auto']), default='auto', 
              help='LLM provider to use (auto-selects best available)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def agent_review(repo: str, config: Optional[str], model: str, verbose: bool):
    """Use Reviewer Agent for autonomous code analysis."""
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        
        click.echo("🤖 Starting AI Agent Review...")
        
        # Initialize coordinator
        provider_name = None if model == 'auto' else model
        coordinator = CoordinatorAgent(model=None, provider=provider_name, verbose=verbose)
        
        # Execute review workflow
        result = coordinator.execute_workflow(
            "full_review",
            repo_path=repo,
            enable_learning=True
        )
        
        if result.get("success", False):
            click.echo("✅ AI Agent Review completed successfully!")
            
            # Save report to file
            report_path = _save_report_to_file(result, repo)
            if report_path:
                click.echo(f"💾 Report saved to: {report_path}")
            
            # Display summary
            analysis = result["results"]["analysis"]
            click.echo(f"📊 Files analyzed: {analysis.get('total_files_analyzed', 0)}")
            click.echo(f"🔍 Issues found: {analysis.get('total_issues_found', 0)}")
            
            if "report" in result["results"]:
                report = result["results"]["report"]
                click.echo("\n📝 AI Review Summary:")
                
                # Check if ai_summary exists and handle gracefully
                if "ai_summary" in report:
                    click.echo(report["ai_summary"])
                elif "error" in report:
                    click.echo(f"⚠️  Report generation error: {report['error']}")
                else:
                    click.echo("⚠️  AI summary not available")
                    if verbose:
                        click.echo(f"Available report fields: {list(report.keys())}")
            else:
                click.echo("\n⚠️  No detailed report generated")
        else:
            click.echo(f"❌ AI Agent Review failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ AI Agent System not available. Install with: pip install langchain litellm python-dotenv", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Agent review failed: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@agent.command('fix')
@click.option('--repo', required=True, help='Repository path to fix')
@click.option('--auto-apply', is_flag=True, help='Automatically apply safe fixes')
@click.option('--create-pr', is_flag=True, help='Create pull request with fixes')
@click.option('--model', type=click.Choice(['xai', 'ollama', 'openai', 'auto']), default='auto', 
              help='LLM provider to use (auto-selects best available)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def agent_fix(repo: str, auto_apply: bool, create_pr: bool, model: str, verbose: bool):
    """Use Fixer Agent for AI-powered code fixes."""
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        
        click.echo("🔧 Starting AI Agent Fix...")
        
        provider_name = None if model == 'auto' else model
        coordinator = CoordinatorAgent(model=None, provider=provider_name, verbose=verbose)
        
        result = coordinator.execute_workflow(
            "fix_and_integrate",
            repo_path=repo,
            auto_apply=auto_apply,
            create_pr=create_pr
        )
        
        if result.get("success", False):
            click.echo("✅ AI Agent Fix completed successfully!")
            
            if "application" in result["results"]:
                fixes_applied = result["results"]["application"].get("fixes_applied", 0)
                click.echo(f"🔧 Fixes applied: {fixes_applied}")
                
            if "pr" in result["results"]:
                pr_url = result["results"]["pr"].get("pr_url", "")
                click.echo(f"🔗 Pull request created: {pr_url}")
        else:
            click.echo(f"❌ AI Agent Fix failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ AI Agent System not available. Install with: pip install langchain litellm python-dotenv", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Agent fix failed: {str(e)}", err=True)
        sys.exit(1)


@agent.command('workflow')
@click.option('--repo', required=True, help='Repository path or URL')
@click.option('--mode', type=click.Choice(['autonomous', 'interactive']), default='interactive', 
              help='Workflow execution mode')
@click.option('--auto-apply', is_flag=True, help='Automatically apply safe fixes')
@click.option('--create-pr', is_flag=True, help='Create pull request with improvements')
@click.option('--learn-patterns', is_flag=True, help='Enable continuous learning')
@click.option('--max-fixes', type=int, default=50, help='Maximum number of fixes to apply')
@click.option('--dry-run', is_flag=True, help='Show what would be done without applying changes')
@click.option('--model', type=click.Choice(['xai', 'ollama', 'openai', 'auto']), default='auto', 
              help='LLM provider to use (auto-selects best available)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--save-report', type=str, help='Save AI analysis report to specified file path')
def agent_workflow(repo: str, mode: str, auto_apply: bool, create_pr: bool, 
                  learn_patterns: bool, max_fixes: int, dry_run: bool, 
                  model: str, verbose: bool, save_report: Optional[str]):
    """Execute full autonomous improvement workflow."""
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        
        if dry_run:
            click.echo("🔍 DRY RUN MODE - No changes will be applied")
        
        click.echo(f"🚀 Starting AI Agent Workflow ({mode} mode)...")
        
        provider_name = None if model == 'auto' else model
        coordinator = CoordinatorAgent(model=None, provider=provider_name, verbose=verbose)
        
        # Execute AI workflow with progress indication
        if not verbose:
            click.echo("📊 Step 1: Analyzing code patterns...")
            click.echo("🤖 Step 2: Generating AI insights (this may take 10-30 seconds)...")
        
        result = coordinator.execute_workflow(
            "autonomous_improvement",
            repo_path=repo,
            auto_apply=auto_apply and not dry_run,
            create_pr=create_pr and not dry_run,
            continuous_learning=learn_patterns,
            max_fixes=max_fixes
        )
        
        if result.get("success", False):
            click.echo("🎉 AI Agent Workflow completed successfully!")
            
            # Debug: Show result structure
            if verbose:
                click.echo(f"\n🔍 Debug - Result keys: {list(result.keys())}")
                if "results" in result:
                    click.echo(f"🔍 Debug - Results keys: {list(result['results'].keys())}")
            
            # Display analysis results and AI insights
            if "results" in result:
                results = result["results"]
                
                # Display review results (this contains the AI analysis)
                if "review" in results:
                    review = results["review"]
                    if verbose:
                        click.echo(f"🔍 Debug - Review keys: {list(review.keys())}")
                    
                    # Check for results within review
                    if "results" in review:
                        review_results = review["results"]
                        
                        # Show basic stats
                        if "analysis" in review_results:
                            analysis = review_results["analysis"]
                            click.echo(f"📊 Analysis: {analysis.get('total_issues_found', 0)} issues in {analysis.get('total_files_analyzed', 0)} files")
                        
                        # Display AI report
                        if "report" in review_results and "ai_summary" in review_results["report"]:
                            ai_report = review_results["report"]["ai_summary"]
                            click.echo("\n🤖 AI-Powered Code Review:")
                            click.echo("=" * 70)
                            click.echo(ai_report)
                            click.echo("=" * 70)
                            
                            # Save report if requested
                            if save_report:
                                _save_ai_report_to_file(ai_report, save_report, repo)
                    
                    # Also check if AI summary is directly in review
                    elif "ai_summary" in review:
                        ai_report = review["ai_summary"]
                        click.echo("\n🤖 AI-Powered Code Review:")
                        click.echo("=" * 70)
                        click.echo(ai_report)
                        click.echo("=" * 70)
                        
                        # Save report if requested
                        if save_report:
                            _save_ai_report_to_file(ai_report, save_report, repo)
            
            if "fixes" in result["results"]:
                fixes = result["results"]["fixes"]["results"]
                if "application" in fixes:
                    click.echo(f"🔧 Fixes: {fixes['application'].get('fixes_applied', 0)} applied")
                if "pr" in fixes:
                    click.echo(f"🔗 PR: {fixes['pr'].get('pr_url', 'Created')}")
            
            if "learning" in result["results"]:
                click.echo("🧠 Learning: Patterns updated and rules refined")
                
        else:
            click.echo(f"❌ AI Agent Workflow failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ AI Agent System not available. Install with: pip install langchain litellm python-dotenv", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Agent workflow failed: {str(e)}", err=True)
        sys.exit(1)


@agent.command('test-model')
@click.option('--model', type=click.Choice(['xai', 'ollama', 'openai', 'auto']), default='auto',
              help='Model provider to test')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def agent_test_model(model: str, verbose: bool):
    """Test LLM model connection and configuration."""
    try:
        from kirolinter.agents.llm_config import test_model_connection, get_model_info
        
        click.echo("🧪 Testing LLM Model Connection...")
        
        # Show available models first
        if verbose:
            model_info = get_model_info()
            click.echo("\n📋 Available Models:")
            for provider, details in model_info["model_details"].items():
                status = "✅" if provider in model_info["available_models"] else "❌"
                click.echo(f"   {status} {provider}: {details['description']}")
        
        # Test connection
        test_provider = None if model == 'auto' else model
        result = test_model_connection(provider=test_provider)
        
        if result["success"]:
            click.echo(f"✅ Model connection successful!")
            click.echo(f"🤖 Provider: {result['provider']}")
            if verbose:
                click.echo(f"📝 Response: {result['response']}")
        else:
            click.echo(f"❌ Model connection failed!")
            click.echo(f"🤖 Provider: {result['provider']}")
            click.echo(f"💥 Error: {result['error']}")
            
            if verbose:
                click.echo("\n🔧 Troubleshooting:")
                click.echo("   • Check your .env file for API keys")
                click.echo("   • Ensure Ollama is running (if using local models)")
                click.echo("   • Verify network connectivity")
        
    except ImportError:
        click.echo("❌ LiteLLM not available. Install with: pip install litellm python-dotenv", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Model test failed: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@agent.command('learn')
@click.option('--repo', required=True, help='Repository path to learn from')
@click.option('--interval', type=int, default=24, help='Periodic learning interval (hours)')
@click.option('--show-anonymization', is_flag=True, help='Show anonymization process')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def agent_learn(repo: str, interval: int, show_anonymization: bool, verbose: bool):
    """Enable continuous learning with pattern extraction and team adaptation."""
    try:
        from kirolinter.agents.learner import LearnerAgent
        from kirolinter.models.config import Config
        
        click.echo(f"🧠 Starting learning process for {repo}")
        
        # Initialize learner
        learner = LearnerAgent(verbose=verbose)
        config = Config()
        
        # Perform initial learning
        click.echo("📚 Analyzing commit history...")
        result = learner.learn_from_commits(repo, config)
        
        if result.get("success", True):
            commits_analyzed = result.get("commits_analyzed", 0)
            patterns_stored = result.get("patterns_stored", 0)
            
            click.echo(f"✅ Learning completed!")
            click.echo(f"📊 Commits analyzed: {commits_analyzed}")
            click.echo(f"🎯 Patterns stored: {patterns_stored}")
            
            # Show anonymization demo if requested
            if show_anonymization:
                click.echo("\n🔒 Anonymization Demo:")
                click.echo("KiroLinter ensures security by anonymizing sensitive data before storing patterns.")
                
                # Example anonymization
                from kirolinter.memory.pattern_memory import DataAnonymizer
                anonymizer = DataAnonymizer()
                
                example_code = 'API_KEY = "sk-1234567890abcdef"'
                anonymized = anonymizer.anonymize_code_snippet(example_code)
                
                click.echo(f"Before: {example_code}")
                click.echo(f"After:  {anonymized}")
                click.echo("See how API keys are redacted in the memory system!")
            
            # Start periodic learning if requested
            if interval > 0:
                click.echo(f"\n⏰ Starting periodic learning (every {interval} hours)...")
                success = learner.start_periodic_learning(repo, interval)
                
                if success:
                    click.echo("✅ Periodic learning started!")
                    click.echo("   The system will continuously learn from your team's coding patterns")
                else:
                    click.echo("⚠️  Periodic learning not available (APScheduler required)")
        else:
            error = result.get("error", "Unknown error")
            click.echo(f"❌ Learning failed: {error}")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ Learning system not available. Install with: pip install apscheduler gitpython", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Learning failed: {str(e)}", err=True)
        sys.exit(1)


@agent.command('status')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed status')
def agent_status(verbose: bool):
    """Show AI Agent System status."""
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        status = coordinator.get_agent_status()
        
        click.echo("🤖 AI Agent System Status:")
        click.echo("=" * 40)
        
        for agent_name, agent_status in status.items():
            status_icon = "✅" if agent_status["status"] == "active" else "❌"
            click.echo(f"{status_icon} {agent_name.title()}: {agent_status['status']}")
            
            if verbose and "memory_size" in agent_status:
                click.echo(f"   Memory: {agent_status['memory_size']} interactions")
        
        click.echo(f"\n📋 Available workflows: {', '.join(coordinator.list_available_workflows())}")
        
    except ImportError:
        click.echo("❌ AI Agent System not available. Install with: pip install langchain litellm python-dotenv", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Status check failed: {str(e)}", err=True)
        sys.exit(1)


def _validate_target(target: str) -> bool:
    """Validate the analysis target."""
    # Check if it's a URL
    if target.startswith(('http://', 'https://', 'git@')):
        return True
    
    # Check if it's current directory
    if target == '.':
        return True
    
    # Check if it's a valid local path (directory or file)
    path = Path(target)
    if path.exists():
        if path.is_dir():
            return True
        elif path.is_file() and path.suffix == '.py':
            return True
    
    return False


if __name__ == '__main__':
    cli()


def _save_report_to_file(result: dict, repo_path: str) -> Optional[str]:
    """
    Save the analysis report to a JSON file in tests/logs directory.
    
    Args:
        result: The analysis result dictionary
        repo_path: Path to the repository that was analyzed
        
    Returns:
        Path to the saved report file, or None if saving failed
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with current date (MMDD format)
        current_date = datetime.now().strftime("%m%d")
        report_filename = f"report-{current_date}.json"
        report_path = logs_dir / report_filename
        
        # Prepare report data
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "repository_path": repo_path,
            "analysis_results": result.get("results", {}),
            "workflow_info": {
                "workflow": result.get("workflow", "unknown"),
                "steps_completed": result.get("steps_completed", []),
                "success": result.get("success", False)
            },
            "metadata": {
                "kirolinter_version": "1.0.0",  # You can make this dynamic
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_files": result.get("results", {}).get("analysis", {}).get("total_files_analyzed", 0),
                "total_issues": result.get("results", {}).get("analysis", {}).get("total_issues_found", 0)
            }
        }
        
        # If file exists, load existing data and append
        if report_path.exists():
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # If existing data is a list, append to it
                if isinstance(existing_data, list):
                    existing_data.append(report_data)
                    report_data = existing_data
                # If existing data is a dict, convert to list
                else:
                    report_data = [existing_data, report_data]
                    
            except (json.JSONDecodeError, Exception):
                # If file is corrupted, create a new list
                report_data = [report_data]
        else:
            # First report of the day, create as single entry
            pass
        
        # Save the report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return str(report_path)
        
    except Exception as e:
        click.echo(f"⚠️  Failed to save report: {str(e)}", err=True)
        return None


def _save_ai_report_to_file(ai_report: str, file_path: str, repo_path: str) -> None:
    """
    Save the AI analysis report to a specified file.
    
    Args:
        ai_report: The AI analysis report content
        file_path: Path where to save the report
        repo_path: Path to the repository that was analyzed
    """
    try:
        from datetime import datetime
        import os
        
        # Ensure the directory exists
        report_path = Path(file_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a formatted report with metadata
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        repo_name = os.path.basename(os.path.abspath(repo_path))
        
        formatted_report = f"""# KiroLinter AI Code Analysis Report

**Repository:** {repo_name}  
**Analysis Date:** {current_time}  
**Generated by:** KiroLinter AI-Powered Workflow  

---

{ai_report}

---

*Report generated by KiroLinter v1.0.0*
"""
        
        # Save the report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(formatted_report)
        
        click.echo(f"💾 Report saved to: {report_path}")
        
    except Exception as e:
        click.echo(f"⚠️  Failed to save report: {str(e)}", err=True)


@daemon.command('start')
@click.option('--repo', required=True, help='Repository path to monitor')
@click.option('--interval', type=int, default=24, help='Analysis interval in hours')
@click.option('--max-cpu', type=float, default=50.0, help='Maximum CPU usage threshold (%)')
@click.option('--max-memory', type=int, default=500, help='Maximum memory usage (MB)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def daemon_start(repo: str, interval: int, max_cpu: float, max_memory: int, verbose: bool):
    """Start background daemon for continuous monitoring."""
    try:
        from kirolinter.automation.daemon import AnalysisDaemon
        
        click.echo(f"🚀 Starting KiroLinter daemon for {repo}")
        click.echo(f"   Interval: {interval} hours")
        click.echo(f"   Resource limits: {max_cpu}% CPU, {max_memory}MB memory")
        
        # Create and start daemon
        daemon = AnalysisDaemon(
            repo_path=repo,
            interval_hours=interval,
            max_cpu_percent=max_cpu,
            max_memory_mb=max_memory,
            verbose=verbose
        )
        
        success = daemon.start()
        
        if success:
            click.echo("✅ Daemon started successfully!")
            click.echo("   Use 'kirolinter daemon status' to check status")
            click.echo("   Use 'kirolinter daemon stop' to stop the daemon")
            
            # Keep the daemon running
            try:
                while daemon.is_running:
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                click.echo("\n🛑 Stopping daemon...")
                daemon.stop()
                click.echo("✅ Daemon stopped")
        else:
            click.echo("❌ Failed to start daemon")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ Daemon system not available. Install with: pip install apscheduler psutil", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Daemon start failed: {str(e)}", err=True)
        sys.exit(1)


@daemon.command('status')
@click.option('--repo', help='Repository path to check (optional)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed status')
def daemon_status(repo: Optional[str], verbose: bool):
    """Show daemon status and statistics."""
    try:
        from kirolinter.automation.daemon import AnalysisDaemon
        
        if repo:
            # Check specific repository daemon
            daemon = AnalysisDaemon(repo_path=repo, verbose=False)
            status = daemon.get_status()
            
            click.echo(f"📊 Daemon Status for {repo}")
            click.echo("=" * 50)
            
            if status["is_running"]:
                click.echo("✅ Status: Running")
                click.echo(f"⏰ Interval: {status['current_interval_hours']} hours")
                click.echo(f"📈 Analyses: {status['analysis_count']} completed")
                
                if status["last_analysis_time"]:
                    click.echo(f"🕐 Last analysis: {status['last_analysis_time']}")
                
                if verbose:
                    perf = status["performance_stats"]
                    click.echo(f"📊 Success rate: {perf['successful_analyses']}/{perf['total_analyses']}")
                    click.echo(f"⚡ Average duration: {perf['average_duration']:.2f}s")
                    click.echo(f"🚫 Resource skips: {perf['resource_skips']}")
            else:
                click.echo("❌ Status: Not running")
        else:
            click.echo("📊 KiroLinter Daemon System Status")
            click.echo("=" * 40)
            click.echo("Use --repo to check specific repository daemon")
            
    except ImportError:
        click.echo("❌ Daemon system not available. Install with: pip install apscheduler psutil", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Status check failed: {str(e)}", err=True)
        sys.exit(1)


@daemon.command('trigger')
@click.option('--repo', required=True, help='Repository path to analyze')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def daemon_trigger(repo: str, verbose: bool):
    """Manually trigger daemon analysis."""
    try:
        from kirolinter.automation.daemon import AnalysisDaemon
        
        click.echo(f"🔄 Triggering analysis for {repo}")
        
        daemon = AnalysisDaemon(repo_path=repo, verbose=verbose)
        success = daemon.trigger_analysis()
        
        if success:
            click.echo("✅ Analysis triggered successfully!")
        else:
            click.echo("❌ Failed to trigger analysis (daemon may not be running)")
            sys.exit(1)
            
    except ImportError:
        click.echo("❌ Daemon system not available. Install with: pip install apscheduler psutil", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Trigger failed: {str(e)}", err=True)
        sys.exit(1)