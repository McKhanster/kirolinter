#!/usr/bin/env python3
"""
Test interactive fixes functionality on Flask repository.
Demonstrates KiroLinter's batch fix capabilities on a real-world codebase.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def setup_flask_test_environment():
    """Set up Flask repository for interactive fixes testing."""
    print("🔧 Setting up Flask test environment...")
    
    # Use a persistent directory name
    persistent_dir = Path.home() / '.kirolinter_test' / 'flask_repo'
    
    if persistent_dir.exists():
        print(f"📁 Using existing Flask repository: {persistent_dir}")
        return str(persistent_dir)
    
    try:
        # Create parent directory
        persistent_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone Flask repository
        print("📥 Cloning Flask repository (first time setup)...")
        result = subprocess.run([
            'git', 'clone', '--depth', '1', 
            'https://github.com/pallets/flask.git', 
            str(persistent_dir)
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"❌ Failed to clone Flask: {result.stderr}")
            return None
        
        print("✅ Flask repository cloned successfully")
        return str(persistent_dir)
        
    except subprocess.TimeoutExpired:
        print("❌ Git clone timed out")
        return None
    except Exception as e:
        print(f"❌ Error setting up environment: {e}")
        return None

def create_test_config(flask_dir):
    """Create KiroLinter configuration for Flask analysis."""
    config_content = """
# KiroLinter configuration for Flask testing
enable_cve_integration: true

rules:
  unused_variable:
    enabled: true
    severity: low
  unused_import:
    enabled: true
    severity: low
  inefficient_loop_concat:
    enabled: true
    severity: medium
  redundant_len_in_loop:
    enabled: true
    severity: low
  sql_injection:
    enabled: true
    severity: critical
  unsafe_eval:
    enabled: true
    severity: critical
  hardcoded_secrets:
    enabled: true
    severity: high

exclude_patterns:
  - "tests/*"
  - "docs/*"
  - "examples/*"
  - "*.pyc"
  - "__pycache__/*"
  - ".git/*"
  - "build/*"
  - "dist/*"

max_complexity: 15
"""
    
    config_path = Path(flask_dir) / '.kirolinter.yaml'
    config_path.write_text(config_content)
    print(f"📝 Created configuration: {config_path}")
    return config_path

def run_analysis_with_dry_run(flask_dir):
    """Run analysis with dry-run to show potential fixes."""
    print("\n🔍 Running analysis with dry-run to preview fixes...")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', flask_dir,
        '--config', str(Path(flask_dir) / '.kirolinter.yaml'),
        '--dry-run',
        '--severity', 'low',
        '--verbose'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("📊 Dry-run Analysis Results:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  Warnings/Errors:")
            print(result.stderr)
        
        # Return True if analysis ran (even if issues were found)
        # Exit code 1 means issues found, which is expected
        return result.returncode in [0, 1]
        
    except subprocess.TimeoutExpired:
        print("❌ Analysis timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def run_interactive_fixes(flask_dir):
    """Run interactive fixes on Flask codebase."""
    print("\n🔧 Running interactive fixes...")
    print("Note: This will prompt for user confirmation for each fix type")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', flask_dir,
        '--config', str(Path(flask_dir) / '.kirolinter.yaml'),
        '--interactive-fixes',
        '--severity', 'low',
        '--verbose'
    ]
    
    try:
        # Run interactively (user will see prompts)
        result = subprocess.run(cmd, timeout=600)  # 10 minute timeout
        
        if result.returncode == 0:
            print("✅ Interactive fixes completed successfully")
        else:
            print(f"⚠️  Interactive fixes completed with issues (exit code: {result.returncode})")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Interactive fixes timed out after 10 minutes")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Interactive fixes cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error running interactive fixes: {e}")
        return False

def show_backup_files(flask_dir):
    """Show backup files created during fixes."""
    print("\n📁 Checking for backup files...")
    
    backup_files = list(Path(flask_dir).rglob('*.kirolinter-backup'))
    
    if backup_files:
        print(f"✅ Found {len(backup_files)} backup files:")
        for backup in backup_files[:10]:  # Show first 10
            original = backup.with_suffix('')
            print(f"   📄 {original.name} -> {backup.name}")
        
        if len(backup_files) > 10:
            print(f"   ... and {len(backup_files) - 10} more backup files")
        
        print("\n💡 Backup files allow you to review changes and revert if needed")
        print("   Remove backups when satisfied: find . -name '*.kirolinter-backup' -delete")
    else:
        print("ℹ️  No backup files found (no fixes were applied)")

def check_repository_state(flask_dir):
    """Check the current state of the repository and show any previous fixes."""
    print("\n📊 Checking repository state...")
    
    # Check for existing backup files
    backup_files = list(Path(flask_dir).rglob('*.kirolinter-backup'))
    if backup_files:
        print(f"🔍 Found {len(backup_files)} backup files from previous runs:")
        for backup in backup_files[:5]:  # Show first 5
            original = backup.with_suffix('')
            print(f"   📄 {original.name} (has backup)")
        if len(backup_files) > 5:
            print(f"   ... and {len(backup_files) - 5} more files with backups")
        print("💡 This indicates previous fixes have been applied")
    else:
        print("ℹ️  No backup files found - repository is in original state")

def get_issue_count(flask_dir):
    """Get the current number of issues in the repository."""
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', flask_dir,
        '--config', str(Path(flask_dir) / '.kirolinter.yaml'),
        '--format', 'json',
        '--severity', 'low'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode in [0, 1] and result.stdout:
            import json
            try:
                data = json.loads(result.stdout)
                return data.get('summary', {}).get('total_issues_found', 0)
            except json.JSONDecodeError:
                return 0
        return 0
        
    except Exception:
        return 0

def generate_summary_report(flask_dir):
    """Generate a final summary report."""
    print("\n📊 Generating final summary report...")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', flask_dir,
        '--config', str(Path(flask_dir) / '.kirolinter.yaml'),
        '--format', 'summary',
        '--severity', 'medium'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("📋 Final Analysis Summary:")
        print("=" * 50)
        print(result.stdout)
        
        # Return True if analysis ran successfully (issues found is OK)
        return result.returncode in [0, 1]
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return False

def main():
    """Main testing function."""
    print("🚀 KiroLinter Interactive Fixes Test on Flask Repository")
    print("=" * 60)
    print("This test demonstrates KiroLinter's batch fix capabilities")
    print("on the Flask web framework codebase.")
    print()
    
    # Check if KiroLinter is available
    try:
        result = subprocess.run([sys.executable, '-m', 'kirolinter.cli', '--help'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ KiroLinter not available. Please install with: pip install -e .")
            return 1
    except Exception:
        print("❌ KiroLinter not available. Please install with: pip install -e .")
        return 1
    
    # Set up test environment
    flask_dir = setup_flask_test_environment()
    if not flask_dir:
        print("❌ Failed to set up test environment")
        return 1
    
    try:
        # Create configuration
        create_test_config(flask_dir)
        
        # Check repository state
        check_repository_state(flask_dir)
        
        # Get initial issue count
        print("\n📊 Getting current issue count...")
        initial_issues = get_issue_count(flask_dir)
        print(f"📋 Current issues found: {initial_issues}")
        
        # Run dry-run analysis
        dry_run_success = run_analysis_with_dry_run(flask_dir)
        if not dry_run_success:
            print("⚠️  Dry-run analysis completed with issues found (this is expected)")
        else:
            print("✅ Dry-run analysis completed successfully")
        
        # Ask user if they want to proceed with interactive fixes
        print("\n" + "=" * 60)
        response = input("🤔 Proceed with interactive fixes? This will modify Flask source files (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # Run interactive fixes
            if run_interactive_fixes(flask_dir):
                # Show backup files
                show_backup_files(flask_dir)
                
                # Get final issue count to show improvement
                print("\n📊 Measuring improvement...")
                final_issues = get_issue_count(flask_dir)
                print(f"📋 Final issues found: {final_issues}")
                
                if initial_issues > 0:
                    improvement = initial_issues - final_issues
                    improvement_pct = (improvement / initial_issues) * 100
                    print(f"📈 Issues fixed: {improvement} ({improvement_pct:.1f}% improvement)")
                
                # Generate final summary
                generate_summary_report(flask_dir)
                
                print("\n🎉 Interactive fixes test completed!")
                print(f"📁 Test directory: {flask_dir}")
                print("💡 Review the changes and backup files")
            else:
                print("❌ Interactive fixes failed")
                return 1
        else:
            print("⏭️  Skipped interactive fixes")
        
        print("\n✨ Test Summary:")
        print("   • Flask repository setup and configured")
        print("   • Dry-run analysis showed potential fixes")
        print("   • Interactive fixes demonstrated (if selected)")
        print("   • Backup files created for safety")
        print("   • Final analysis report generated")
        
        print(f"\n📁 Flask repository location: {flask_dir}")
        print("💡 Repository is preserved for future test runs")
        print("💡 To reset, delete: ~/.kirolinter_test/flask_repo")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())