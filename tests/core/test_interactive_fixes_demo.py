#!/usr/bin/env python3
"""
Demo script to test interactive fixes functionality on a small test file.
This creates a test file with known issues and demonstrates the fix process.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_test_file_with_issues(test_dir):
    """Create a test Python file with known fixable issues."""
    test_file = Path(test_dir) / "test_issues.py"
    
    content = '''#!/usr/bin/env python3
"""Test file with various fixable issues."""

import os  # This import is unused
import sys  # This import is also unused
from pathlib import Path  # This one too

def main():
    """Main function with issues."""
    unused_var = "This variable is never used"
    another_unused = 42
    
    # Inefficient concatenation
    result = []
    for i in range(10):
        result = result + [i]  # This is inefficient
    
    print("Hello, world!")
    return result

if __name__ == "__main__":
    main()
'''
    
    test_file.write_text(content)
    print(f"📝 Created test file: {test_file}")
    return test_file

def create_config_file(test_dir):
    """Create a simple configuration for testing."""
    config_content = '''# KiroLinter test configuration
enable_cve_integration: false

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

exclude_patterns: []
max_complexity: 15
'''
    
    config_path = Path(test_dir) / '.kirolinter.yaml'
    config_path.write_text(config_content)
    print(f"📝 Created config: {config_path}")
    return config_path

def run_dry_run_analysis(test_dir):
    """Run dry-run analysis to show what would be fixed."""
    print("\n🔍 Running dry-run analysis...")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', test_dir,
        '--config', str(Path(test_dir) / '.kirolinter.yaml'),
        '--dry-run',
        '--severity', 'low',
        '--verbose'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        print("📊 Dry-run Results:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  Warnings:")
            print(result.stderr)
        
        return result.returncode in [0, 1]  # 1 means issues found, which is expected
        
    except subprocess.TimeoutExpired:
        print("❌ Analysis timed out")
        return False
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def run_interactive_fixes(test_dir):
    """Run interactive fixes with simulated user input."""
    print("\n🔧 Running interactive fixes...")
    print("Note: This will prompt for confirmation for each fix type")
    
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', test_dir,
        '--config', str(Path(test_dir) / '.kirolinter.yaml'),
        '--interactive-fixes',
        '--severity', 'low',
        '--verbose'
    ]
    
    try:
        # Run interactively - user will see prompts
        result = subprocess.run(cmd, timeout=120)
        
        if result.returncode == 0:
            print("✅ Interactive fixes completed successfully")
        else:
            print(f"⚠️  Interactive fixes completed with exit code: {result.returncode}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Interactive fixes timed out")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Interactive fixes cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error running interactive fixes: {e}")
        return False

def show_file_changes(test_dir):
    """Show the changes made to files."""
    print("\n📄 File Changes:")
    print("=" * 50)
    
    test_file = Path(test_dir) / "test_issues.py"
    backup_file = Path(test_dir) / "test_issues.py.kirolinter-backup"
    
    if backup_file.exists():
        print("✅ Backup file created")
        print(f"📁 Original: {backup_file}")
        print(f"📁 Modified: {test_file}")
        
        print("\n📝 Original content:")
        print("-" * 30)
        print(backup_file.read_text())
        
        print("\n📝 Modified content:")
        print("-" * 30)
        print(test_file.read_text())
        
    else:
        print("ℹ️  No backup file found - no changes were made")

def main():
    """Main demo function."""
    print("🚀 KiroLinter Interactive Fixes Demo")
    print("=" * 50)
    print("This demo creates a test file with known issues and")
    print("demonstrates the interactive fix process.")
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
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix='kirolinter_demo_')
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Create test files
        test_file = create_test_file_with_issues(test_dir)
        config_file = create_config_file(test_dir)
        
        # Run dry-run analysis
        print("\n" + "=" * 50)
        if run_dry_run_analysis(test_dir):
            print("✅ Dry-run analysis completed")
        else:
            print("⚠️  Dry-run analysis had issues")
        
        # Ask user if they want to proceed
        print("\n" + "=" * 50)
        response = input("🤔 Proceed with interactive fixes? (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # Run interactive fixes
            if run_interactive_fixes(test_dir):
                # Show changes
                show_file_changes(test_dir)
                
                print("\n🎉 Interactive fixes demo completed!")
                print("💡 Review the changes above to see what was fixed")
            else:
                print("❌ Interactive fixes failed")
                return 1
        else:
            print("⏭️  Skipped interactive fixes")
        
        print("\n✨ Demo Summary:")
        print("   • Test file created with known issues")
        print("   • Dry-run analysis showed potential fixes")
        print("   • Interactive fixes demonstrated (if selected)")
        print("   • File changes shown with before/after comparison")
        
        return 0
        
    finally:
        # Ask if user wants to clean up
        print(f"\n🧹 Test directory: {test_dir}")
        cleanup = input("Clean up test directory? (y/N): ").strip().lower()
        
        if cleanup in ['y', 'yes']:
            shutil.rmtree(test_dir, ignore_errors=True)
            print("✅ Test directory cleaned up")
        else:
            print(f"📁 Test directory preserved: {test_dir}")

if __name__ == "__main__":
    sys.exit(main())