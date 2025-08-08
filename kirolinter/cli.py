#!/usr/bin/env python3
"""
KiroLinter CLI - AI-driven code review tool
"""

import click
import os
import sys
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
              type=click.Choice(['json', 'summary', 'detailed']), 
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
def analyze(target: str, format: str, output: Optional[str], config: Optional[str], 
           changed_only: bool, severity: Optional[str], exclude: tuple, verbose: bool):
    """
    Analyze a Git repository or local codebase for code quality issues.
    
    TARGET can be:
    - A Git repository URL (https://github.com/user/repo.git)
    - A local directory path (/path/to/project)
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


def _validate_target(target: str) -> bool:
    """Validate the analysis target."""
    # Check if it's a URL
    if target.startswith(('http://', 'https://', 'git@')):
        return True
    
    # Check if it's a valid local path
    path = Path(target)
    if path.exists() and path.is_dir():
        return True
    
    # Check if it's current directory
    if target == '.':
        return True
    
    return False


if __name__ == '__main__':
    cli()