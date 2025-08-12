#!/usr/bin/env python3
"""
Verification test to prove interactive fixes are actually working.
This test creates files, applies fixes, and verifies the changes.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_test_files_with_issues(test_dir):
    """Create test files with known fixable issues."""
    
    # Create a Python file with unused imports and variables
    test_file1 = Path(test_dir) / "test_file1.py"
    content1 = '''#!/usr/bin/env python3
"""Test file with unused imports and variables."""

import os  # This will be unused
import sys  # This will be unused
from pathlib import Path  # This will be unused
import json

def main():
    """Main function."""
    unused_var = "This variable is never used"
    another_unused = 42
    
    # This variable is used
    data = {"key": "value"}
    print(json.dumps(data))
    
    return "done"

if __name__ == "__main__":
    main()
'''
    
    test_file1.write_text(content1)
    
    # Create another test file
    test_file2 = Path(test_dir) / "test_file2.py"
    content2 = '''"""Another test file with issues."""

import re  # Unused
import datetime  # Unused
from typing import List  # Unused

def process_data():
    """Process some data."""
    temp_var = "temporary"
    result_var = []
    
    # Only result_var is actually used
    result_var.append("item")
    return result_var
'''
    
    test_file2.write_text(content2)
    
    return [test_file1, test_file2]

def create_config_file(test_dir):
    """Create configuration for testing."""
    config_content = '''# Test configuration
enable_cve_integration: false

rules:
  unused_variable:
    enabled: true
    severity: low
  unused_import:
    enabled: true
    severity: low

exclude_patterns: []
max_complexity: 15
'''
    
    config_path = Path(test_dir) / '.kirolinter.yaml'
    config_path.write_text(config_content)
    return config_path

def run_analysis_and_get_issues(test_dir):
    """Run analysis and return the number of issues found."""
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', test_dir,
        '--config', str(Path(test_dir) / '.kirolinter.yaml'),
        '--format', 'json',
        '--severity', 'low'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode in [0, 1]:  # 1 means issues found
            if result.stdout:
                import json
                try:
                    data = json.loads(result.stdout)
                    return data.get('summary', {}).get('total_issues_found', 0)
                except json.JSONDecodeError:
                    return 0
        return 0
        
    except Exception as e:
        print(f"Error running analysis: {e}")
        return 0

def apply_interactive_fixes_automatically(test_dir):
    """Apply fixes by simulating 'y' responses to all prompts."""
    cmd = [
        sys.executable, '-m', 'kirolinter.cli',
        'analyze', test_dir,
        '--config', str(Path(test_dir) / '.kirolinter.yaml'),
        '--interactive-fixes',
        '--severity', 'low'
    ]
    
    try:
        # Simulate user input by providing 'y' for each prompt
        # We expect 2 prompts: one for unused imports, one for unused variables
        user_input = "y\ny\n"
        
        result = subprocess.run(
            cmd, 
            input=user_input, 
            text=True, 
            timeout=120,
            capture_output=True
        )
        
        return result.returncode in [0, 1]  # Success or issues found
        
    except Exception as e:
        print(f"Error applying fixes: {e}")
        return False

def verify_file_changes(test_files):
    """Verify that files were actually modified."""
    changes_found = []
    
    for test_file in test_files:
        backup_file = Path(str(test_file) + '.kirolinter-backup')
        
        if backup_file.exists():
            # Read original and modified content
            original_content = backup_file.read_text()
            modified_content = test_file.read_text()
            
            if original_content != modified_content:
                changes_found.append({
                    'file': test_file.name,
                    'backup_exists': True,
                    'content_changed': True,
                    'original_lines': len(original_content.split('\n')),
                    'modified_lines': len(modified_content.split('\n'))
                })
            else:
                changes_found.append({
                    'file': test_file.name,
                    'backup_exists': True,
                    'content_changed': False
                })
        else:
            changes_found.append({
                'file': test_file.name,
                'backup_exists': False,
                'content_changed': False
            })
    
    return changes_found

def show_file_diff(test_file):
    """Show the differences between original and modified file."""
    backup_file = Path(str(test_file) + '.kirolinter-backup')
    
    if backup_file.exists():
        print(f"\n📄 Changes in {test_file.name}:")
        print("=" * 50)
        
        original_lines = backup_file.read_text().split('\n')
        modified_lines = test_file.read_text().split('\n')
        
        print("🔴 Original content (first 15 lines):")
        for i, line in enumerate(original_lines[:15], 1):
            print(f"{i:2d}: {line}")
        
        print("\n🟢 Modified content (first 15 lines):")
        for i, line in enumerate(modified_lines[:15], 1):
            print(f"{i:2d}: {line}")
        
        # Show lines that were commented out
        commented_lines = [line for line in modified_lines if line.strip().startswith('# ') and 'Removed unused' in line]
        if commented_lines:
            print(f"\n💡 Found {len(commented_lines)} commented out lines:")
            for line in commented_lines[:5]:  # Show first 5
                print(f"   {line.strip()}")

def main():
    """Main verification function."""
    print("🔍 KiroLinter Interactive Fixes Verification Test")
    print("=" * 60)
    print("This test verifies that interactive fixes actually modify files.")
    print()
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix='kirolinter_verify_')
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Create test files with known issues
        test_files = create_test_files_with_issues(test_dir)
        config_file = create_config_file(test_dir)
        
        print(f"📝 Created {len(test_files)} test files with known issues")
        
        # Run initial analysis
        print("\n🔍 Running initial analysis...")
        initial_issues = run_analysis_and_get_issues(test_dir)
        print(f"📊 Initial issues found: {initial_issues}")
        
        if initial_issues == 0:
            print("❌ No issues found in test files - something is wrong")
            return 1
        
        # Apply interactive fixes
        print("\n🔧 Applying interactive fixes...")
        fix_success = apply_interactive_fixes_automatically(test_dir)
        
        if not fix_success:
            print("❌ Failed to apply fixes")
            return 1
        
        print("✅ Interactive fixes completed")
        
        # Verify file changes
        print("\n📋 Verifying file changes...")
        changes = verify_file_changes(test_files)
        
        files_changed = 0
        for change in changes:
            print(f"   📄 {change['file']}:")
            print(f"      Backup exists: {'✅' if change['backup_exists'] else '❌'}")
            print(f"      Content changed: {'✅' if change['content_changed'] else '❌'}")
            
            if change['content_changed']:
                files_changed += 1
        
        print(f"\n📊 Summary: {files_changed}/{len(test_files)} files were modified")
        
        # Show detailed changes
        if files_changed > 0:
            print("\n🔍 Detailed changes:")
            for test_file in test_files:
                if Path(str(test_file) + '.kirolinter-backup').exists():
                    show_file_diff(test_file)
        
        # Run final analysis
        print("\n🔍 Running final analysis...")
        final_issues = run_analysis_and_get_issues(test_dir)
        print(f"📊 Final issues found: {final_issues}")
        
        # Calculate improvement
        if initial_issues > 0:
            improvement = initial_issues - final_issues
            improvement_pct = (improvement / initial_issues) * 100
            print(f"📈 Issues fixed: {improvement} ({improvement_pct:.1f}% improvement)")
        
        # Determine success
        if files_changed > 0 and final_issues < initial_issues:
            print("\n🎉 SUCCESS: Interactive fixes are working correctly!")
            print("   ✅ Files were modified")
            print("   ✅ Backup files were created")
            print("   ✅ Issue count decreased")
            return 0
        else:
            print("\n❌ FAILURE: Interactive fixes are not working properly")
            if files_changed == 0:
                print("   ❌ No files were modified")
            if final_issues >= initial_issues:
                print("   ❌ Issue count did not decrease")
            return 1
        
    finally:
        # Ask if user wants to clean up
        print(f"\n🧹 Test directory: {test_dir}")
        try:
            cleanup = input("Clean up test directory? (y/N): ").strip().lower()
            if cleanup in ['y', 'yes']:
                shutil.rmtree(test_dir, ignore_errors=True)
                print("✅ Test directory cleaned up")
            else:
                print(f"📁 Test directory preserved for inspection: {test_dir}")
        except KeyboardInterrupt:
            print(f"\n📁 Test directory preserved: {test_dir}")

if __name__ == "__main__":
    sys.exit(main())