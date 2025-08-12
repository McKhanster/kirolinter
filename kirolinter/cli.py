#!/usr/bin/env python3
"""
KiroLinter CLI - AI-driven code review tool
"""

import click
import json
import os
import sys
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
def agent_workflow(repo: str, mode: str, auto_apply: bool, create_pr: bool, 
                  learn_patterns: bool, max_fixes: int, dry_run: bool, 
                  model: str, verbose: bool):
    """Execute full autonomous improvement workflow."""
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        
        if dry_run:
            click.echo("🔍 DRY RUN MODE - No changes will be applied")
        
        click.echo(f"🚀 Starting AI Agent Workflow ({mode} mode)...")
        
        provider_name = None if model == 'auto' else model
        coordinator = CoordinatorAgent(model=None, provider=provider_name, verbose=verbose)
        
        # Execute autonomous improvement workflow
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
            
            # Display comprehensive summary
            if "review" in result["results"]:
                review = result["results"]["review"]["results"]["analysis"]
                click.echo(f"📊 Analysis: {review.get('total_issues_found', 0)} issues in {review.get('total_files_analyzed', 0)} files")
            
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