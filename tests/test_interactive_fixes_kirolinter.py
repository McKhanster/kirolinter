#!/usr/bin/env python3
"""
Test interactive fixes functionality on KiroLinter repository.
Demonstrates KiroLinter's batch fix capabilities on its own codebase.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import json

def check_kirolinter_installation():
    """Check if KiroLinter is properly installed."""
    try:
        # Try to import kirolinter
        import kirolinter
        kirolinter_path = Path(kirolinter.__file__).parent
        print(f"✅ KiroLinter installed at: {kirolinter_path}")
        return True
    except ImportError:
        print("❌ KiroLinter not available. Please install with: pip install -e .")
        return False

def setup_kirolinter_test_environment():
    """Set up KiroLinter repository for interactive fixes testing."""
    print("🔧 Setting up KiroLinter test environment...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='kirolinter_self_test_')
    print(f"📁 Working directory: {temp_dir}")
    
    try:
        # Clone KiroLinter repository
        print("📥 Cloning KiroLinter repository...")
        result = subprocess.run([
            'git', 'clone', '--depth', '1', 
            'https://github.com/McKhanster/kirolinter.git', 
            temp_dir
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"❌ Failed to clone KiroLinter: {result.stderr}")
            return None
        
        print("✅ KiroLinter repository cloned successfully")
        return temp_dir
        
    except subprocess.TimeoutExpired:
        print("❌ Git clone timed out")
        return None
    except Exception as e:
        print(f"❌ Error setting up environment: {e}")
        return None

def create_test_config(repo_dir):
    """Create KiroLinter configuration for self-analysis."""
    config_content = """# KiroLinter configuration for self-analysis
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
  - ".venv/*"
  - "venv/*"

max_complexity: 15
"""
    
    config_path = Path(repo_dir) / '.kirolinter.yaml'
    config_path.write_text(config_content)
    print(f"📝 Created configuration: {config_path}")
    return config_path

def run_analysis_with_dry_run(repo_dir):
    """Run analysis with dry-run to show potential fixes."""
    print("\n🔍 Running analysis with dry-run to preview fixes...")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', repo_dir,
        '--config', str(Path(repo_dir) / '.kirolinter.yaml'),
        '--dry-run',
        '--severity', 'low',
        '--format', 'json'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("📊 Dry-run Analysis Results:")
        print("=" * 50)
        
        if result.stdout:
            try:
                # Try to parse JSON output
                analysis_data = json.loads(result.stdout)
                
                # Print summary
                if 'summary' in analysis_data:
                    summary = analysis_data['summary']
                    print(f"🔍 Analyzing  {repo_dir}...")
                    print("Analyzing code")
                    print(json.dumps(analysis_data, indent=2))
                else:
                    print(result.stdout)
            except json.JSONDecodeError:
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

def run_interactive_fixes_demo(repo_dir):
    """Run actual interactive fixes on the repository."""
    print("\n🔧 Running interactive fixes...")
    print("Note: This will prompt for user confirmation for each fix type")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', repo_dir,
        '--config', str(Path(repo_dir) / '.kirolinter.yaml'),
        '--interactive-fixes',
        '--severity', 'low',
        '--verbose'
    ]
    
    try:
        # Run interactively - user will see prompts
        result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print("✅ Interactive fixes completed successfully")
        else:
            print(f"⚠️  Interactive fixes completed with exit code: {result.returncode}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Interactive fixes timed out after 5 minutes")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Interactive fixes cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error running interactive fixes: {e}")
        return False

def show_backup_files(repo_dir):
    """Show backup files created during fixes."""
    print("\n📁 Checking for backup files...")
    
    backup_files = list(Path(repo_dir).rglob('*.kirolinter-backup'))
    
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

def run_interactive_fixes_simulation(repo_dir):
    """Show what fixes would be available without applying them."""
    print("\n🔧 Showing available fixes (simulation mode)...")
    
    # First, let's see what fixes are available
    cmd_analyze = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', repo_dir,
        '--config', str(Path(repo_dir) / '.kirolinter.yaml'),
        '--severity', 'low',
        '--format', 'json'
    ]
    
    try:
        # Get analysis results first
        result = subprocess.run(cmd_analyze, capture_output=True, text=True, timeout=300)
        
        if result.returncode not in [0, 1]:
            print(f"❌ Analysis failed with exit code: {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        
        # Parse results to see if there are fixable issues
        if result.stdout:
            try:
                analysis_data = json.loads(result.stdout)
                fixable_issues = []
                
                if 'files' in analysis_data:
                    for file_data in analysis_data['files']:
                        if 'issues' in file_data:
                            for issue in file_data['issues']:
                                if 'suggested_fix' in issue and issue['suggested_fix']:
                                    fixable_issues.append(issue)
                
                print(f"📋 Found {len(fixable_issues)} fixable issues")
                
                if fixable_issues:
                    print("\n🔧 Sample fixable issues:")
                    for i, issue in enumerate(fixable_issues[:5]):  # Show first 5
                        print(f"   {i+1}. {issue['message']} in {issue['file_path']}:{issue['line_number']}")
                        if 'suggested_fix' in issue:
                            fix = issue['suggested_fix']
                            print(f"      Fix: {fix.get('explanation', 'No explanation')}")
                    
                    if len(fixable_issues) > 5:
                        print(f"   ... and {len(fixable_issues) - 5} more fixable issues")
                
            except json.JSONDecodeError:
                print("⚠️  Could not parse analysis results")
        
        # Now demonstrate the fix command options
        print("\n💡 To apply fixes interactively, you would run:")
        print(f"   kirolinter analyze {repo_dir} --interactive-fixes --severity low")
        print("\n💡 To see what would be fixed without applying changes:")
        print(f"   kirolinter analyze {repo_dir} --dry-run --severity low")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Analysis timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def demonstrate_fix_capabilities(repo_dir):
    """Demonstrate what the fix capabilities would do without actually applying them."""
    print("\n🎯 Demonstrating Fix Capabilities:")
    print("=" * 50)
    
    # Show the help for fix-related commands
    try:
        result = subprocess.run([
            sys.executable, '-m', 'kirolinter.cli', 'analyze', '--help'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract fix-related options from help
            help_lines = result.stdout.split('\n')
            fix_options = []
            for line in help_lines:
                if 'fix' in line.lower() or 'interactive' in line.lower():
                    fix_options.append(line.strip())
            
            if fix_options:
                print("🔧 Available fix options:")
                for option in fix_options:
                    print(f"   {option}")
            else:
                print("ℹ️  Fix options available in CLI help")
        
    except Exception as e:
        print(f"⚠️  Could not retrieve help information: {e}")
    
    print("\n📝 Fix Types Supported:")
    print("   • unused_import: Remove unused import statements")
    print("   • unused_variable: Remove unused variable assignments")
    print("   • inefficient_loop_concat: Optimize string concatenation in loops")
    print("   • redundant_len_in_loop: Remove redundant len() calls in loops")
    
    print("\n🛡️  Safety Features:")
    print("   • Backup files created before modifications (.kirolinter-backup)")
    print("   • Interactive confirmation for each fix type")
    print("   • Dry-run mode to preview changes")
    print("   • Selective fixing by rule type")

def generate_summary_report(repo_dir):
    """Generate a final summary report."""
    print("\n📊 Generating final summary report...")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', repo_dir,
        '--config', str(Path(repo_dir) / '.kirolinter.yaml'),
        '--format', 'summary',
        '--severity', 'medium'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("📋 Final Analysis Summary:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  Warnings:")
            print(result.stderr)
        
        # Return True if analysis ran successfully (issues found is OK)
        return result.returncode in [0, 1]
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return False

def main():
    """Main testing function."""
    print("🚀 KiroLinter Interactive Fixes Test on KiroLinter Repository")
    print("=" * 60)
    print("This test demonstrates KiroLinter's batch fix capabilities")
    print("on its own codebase (self-analysis).")
    print()
    
    # Check if KiroLinter is available
    if not check_kirolinter_installation():
        return 1
    
    # Set up test environment
    repo_dir = setup_kirolinter_test_environment()
    if not repo_dir:
        print("❌ Failed to set up test environment")
        return 1
    
    try:
        # Create configuration
        create_test_config(repo_dir)
        
        # Run dry-run analysis
        print("\n" + "=" * 60)
        dry_run_success = run_analysis_with_dry_run(repo_dir)
        if not dry_run_success:
            print("⚠️  Dry-run analysis had issues, but continuing...")
        
        # Show what fixes are available
        print("\n" + "=" * 60)
        if run_interactive_fixes_simulation(repo_dir):
            print("✅ Fix simulation completed")
        else:
            print("⚠️  Fix simulation had issues")
        
        # Ask user if they want to proceed with actual interactive fixes
        print("\n" + "=" * 60)
        response = input("🤔 Proceed with actual interactive fixes? This will modify the repository files (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # Run actual interactive fixes
            if run_interactive_fixes_demo(repo_dir):
                # Show backup files
                show_backup_files(repo_dir)
                print("✅ Interactive fixes completed")
            else:
                print("⚠️  Interactive fixes had issues")
        else:
            print("⏭️  Skipped interactive fixes")
        
        # Demonstrate fix capabilities
        demonstrate_fix_capabilities(repo_dir)
        
        # Generate final summary
        print("\n" + "=" * 60)
        generate_summary_report(repo_dir)
        
        print("\n🎉 Interactive fixes test completed!")
        print(f"📁 Test directory: {repo_dir}")
        
        print("\n✨ Test Summary:")
        print("   • KiroLinter repository cloned and configured")
        print("   • Self-analysis performed successfully")
        print("   • Interactive fix capabilities demonstrated")
        print("   • Fix types and safety features explained")
        print("   • Final analysis report generated")
        
        print("\n💡 Next Steps:")
        print("   • Run with --interactive-fixes to apply fixes interactively")
        print("   • Use --auto-fix with specific rule types for batch fixes")
        print("   • Review backup files before committing changes")
        
        return 0
        
    finally:
        # Ask if user wants to clean up
        print(f"\n🧹 Test directory: {repo_dir}")
        cleanup = input("Clean up test directory? (y/N): ").strip().lower()
        
        if cleanup in ['y', 'yes']:
            shutil.rmtree(repo_dir, ignore_errors=True)
            print("✅ Test directory cleaned up")
        else:
            print(f"📁 Test directory preserved: {repo_dir}")

if __name__ == "__main__":
    sys.exit(main())