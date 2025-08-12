"""
Interactive fixer for applying batch fixes with user authorization.
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

import click

from kirolinter.core.engine import AnalysisResults
from kirolinter.models.issue import Issue, IssueType


class InteractiveFixer:
    """Interactive fixer for applying batch code fixes."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.fixable_rules = {
            'unused_variable': self._fix_unused_variable,
            'unused_import': self._fix_unused_import,
            'inefficient_loop_concat': self._fix_inefficient_concat,
            'redundant_len_in_loop': self._fix_redundant_len
        }
    
    def show_potential_fixes(self, results: AnalysisResults):
        """Show what fixes would be applied in dry-run mode."""
        fixable_issues = self._group_fixable_issues(results)
        
        if not fixable_issues:
            click.echo("ℹ️  No automatically fixable issues found")
            return
        
        click.echo("🔍 Potential fixes that could be applied:")
        click.echo("=" * 50)
        
        total_fixes = 0
        for rule_id, issues in fixable_issues.items():
            total_fixes += len(issues)
            click.echo(f"\n📋 {rule_id.replace('_', ' ').title()} ({len(issues)} issues)")
            
            # Group by file
            by_file = defaultdict(list)
            for issue in issues:
                by_file[issue.file_path].append(issue)
            
            for file_path, file_issues in by_file.items():
                click.echo(f"   📄 {file_path}: {len(file_issues)} issues")
                if self.verbose:
                    for issue in file_issues[:3]:  # Show first 3
                        click.echo(f"      Line {issue.line_number}: {issue.message}")
                    if len(file_issues) > 3:
                        click.echo(f"      ... and {len(file_issues) - 3} more")
        
        click.echo(f"\n📊 Total fixable issues: {total_fixes}")
        click.echo("\n💡 Run without --dry-run to apply fixes interactively")
    
    def apply_interactive_fixes(self, results: AnalysisResults) -> int:
        """Apply fixes interactively with user authorization."""
        fixable_issues = self._group_fixable_issues(results)
        
        if not fixable_issues:
            click.echo("ℹ️  No automatically fixable issues found")
            return 0
        
        total_applied = 0
        
        for rule_id, issues in fixable_issues.items():
            rule_name = rule_id.replace('_', ' ').title()
            
            click.echo(f"\n🔧 Found {len(issues)} {rule_name} issues")
            
            # Group by file for better organization
            by_file = defaultdict(list)
            for issue in issues:
                by_file[issue.file_path].append(issue)
            
            # Show preview
            click.echo("Preview of issues:")
            for file_path, file_issues in list(by_file.items())[:3]:  # Show first 3 files
                click.echo(f"   📄 {file_path}: {len(file_issues)} issues")
                if self.verbose:
                    for issue in file_issues[:2]:  # Show first 2 per file
                        click.echo(f"      Line {issue.line_number}: {issue.message}")
            
            if len(by_file) > 3:
                remaining_files = len(by_file) - 3
                remaining_issues = sum(len(issues) for file_path, issues in list(by_file.items())[3:])
                click.echo(f"   ... and {remaining_issues} more issues in {remaining_files} files")
            
            # Ask for confirmation
            if click.confirm(f"\n❓ Apply fixes for all {len(issues)} {rule_name} issues?"):
                applied = self._apply_fixes_for_rule(rule_id, issues)
                total_applied += applied
                click.echo(f"✅ Applied {applied} {rule_name} fixes")
            else:
                click.echo(f"⏭️  Skipped {rule_name} fixes")
        
        return total_applied
    
    def _group_fixable_issues(self, results: AnalysisResults) -> Dict[str, List[Issue]]:
        """Group fixable issues by rule type."""
        fixable_issues = defaultdict(list)
        
        for scan_result in results.scan_results:
            for issue in scan_result.issues:
                if issue.rule_id in self.fixable_rules:
                    fixable_issues[issue.rule_id].append(issue)
        
        return dict(fixable_issues)
    
    def _apply_fixes_for_rule(self, rule_id: str, issues: List[Issue]) -> int:
        """Apply fixes for a specific rule type."""
        if rule_id not in self.fixable_rules:
            return 0
        
        fixer_func = self.fixable_rules[rule_id]
        applied_count = 0
        
        # Group by file to process efficiently
        by_file = defaultdict(list)
        for issue in issues:
            by_file[issue.file_path].append(issue)
        
        for file_path, file_issues in by_file.items():
            try:
                if self._apply_fixes_to_file(file_path, file_issues, fixer_func):
                    applied_count += len(file_issues)
                    if self.verbose:
                        click.echo(f"   ✅ Fixed {len(file_issues)} issues in {file_path}")
            except Exception as e:
                if self.verbose:
                    click.echo(f"   ❌ Failed to fix issues in {file_path}: {e}")
        
        return applied_count
    
    def _apply_fixes_to_file(self, file_path: str, issues: List[Issue], fixer_func) -> bool:
        """Apply fixes to a single file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            # Read original content
            original_content = path.read_text(encoding='utf-8')
            
            # Create backup
            backup_path = path.with_suffix(path.suffix + '.kirolinter-backup')
            backup_path.write_text(original_content, encoding='utf-8')
            
            # Apply fixes
            modified_content = fixer_func(original_content, issues)
            
            if modified_content != original_content:
                path.write_text(modified_content, encoding='utf-8')
                return True
            else:
                # Remove backup if no changes
                backup_path.unlink()
                return False
                
        except Exception as e:
            if self.verbose:
                click.echo(f"Error fixing {file_path}: {e}")
            return False
    
    def _fix_unused_variable(self, content: str, issues: List[Issue]) -> str:
        """Fix unused variable issues."""
        lines = content.split('\n')
        
        # Sort issues by line number in reverse order to avoid line number shifts
        sorted_issues = sorted(issues, key=lambda x: x.line_number, reverse=True)
        
        for issue in sorted_issues:
            line_idx = issue.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                
                # Extract variable name from message
                var_match = re.search(r"Unused variable '([^']+)'", issue.message)
                if var_match:
                    var_name = var_match.group(1)
                    
                    # Simple removal for assignment statements
                    if f"{var_name} =" in line and not line.strip().startswith('#'):
                        # Check if it's a simple assignment we can remove
                        if re.match(rf'^\s*{re.escape(var_name)}\s*=', line.strip()):
                            lines[line_idx] = f"# {line}  # Removed unused variable"
        
        return '\n'.join(lines)
    
    def _fix_unused_import(self, content: str, issues: List[Issue]) -> str:
        """Fix unused import issues."""
        lines = content.split('\n')
        
        # Sort issues by line number in reverse order
        sorted_issues = sorted(issues, key=lambda x: x.line_number, reverse=True)
        
        for issue in sorted_issues:
            line_idx = issue.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                
                # Only remove if it's clearly an import line
                if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                    lines[line_idx] = f"# {line}  # Removed unused import"
        
        return '\n'.join(lines)
    
    def _fix_inefficient_concat(self, content: str, issues: List[Issue]) -> str:
        """Fix inefficient list concatenation issues."""
        lines = content.split('\n')
        
        for issue in issues:
            line_idx = issue.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                
                # Look for pattern: result = result + [item]
                concat_pattern = r'(\w+)\s*=\s*\1\s*\+\s*\[([^\]]+)\]'
                match = re.search(concat_pattern, line)
                
                if match:
                    var_name = match.group(1)
                    item = match.group(2)
                    
                    # Replace with append
                    new_line = re.sub(concat_pattern, rf'{var_name}.append({item})', line)
                    lines[line_idx] = new_line + "  # Fixed inefficient concatenation"
        
        return '\n'.join(lines)
    
    def _fix_redundant_len(self, content: str, issues: List[Issue]) -> str:
        """Fix redundant len() calls in loops."""
        # This is more complex and would require AST manipulation
        # For now, just add comments
        lines = content.split('\n')
        
        for issue in issues:
            line_idx = issue.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                if not line.strip().endswith('# TODO: Cache len() result'):
                    lines[line_idx] = line + "  # TODO: Cache len() result"
        
        return '\n'.join(lines)


class BatchFixSummary:
    """Summary of batch fix operations."""
    
    def __init__(self):
        self.fixes_by_rule = defaultdict(int)
        self.files_modified = set()
        self.errors = []
    
    def add_fix(self, rule_id: str, file_path: str, count: int = 1):
        """Add a successful fix."""
        self.fixes_by_rule[rule_id] += count
        self.files_modified.add(file_path)
    
    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(error)
    
    def total_fixes(self) -> int:
        """Get total number of fixes applied."""
        return sum(self.fixes_by_rule.values())
    
    def print_summary(self):
        """Print a summary of the batch fix operation."""
        if self.total_fixes() == 0:
            click.echo("ℹ️  No fixes were applied")
            return
        
        click.echo(f"\n📊 Batch Fix Summary:")
        click.echo(f"   Total fixes applied: {self.total_fixes()}")
        click.echo(f"   Files modified: {len(self.files_modified)}")
        
        if self.fixes_by_rule:
            click.echo("\n   Fixes by type:")
            for rule_id, count in self.fixes_by_rule.items():
                rule_name = rule_id.replace('_', ' ').title()
                click.echo(f"     {rule_name}: {count}")
        
        if self.errors:
            click.echo(f"\n   Errors encountered: {len(self.errors)}")
            if len(self.errors) <= 3:
                for error in self.errors:
                    click.echo(f"     ❌ {error}")
            else:
                for error in self.errors[:3]:
                    click.echo(f"     ❌ {error}")
                click.echo(f"     ... and {len(self.errors) - 3} more errors")
        
        click.echo("\n💡 Backup files created with .kirolinter-backup extension")
        click.echo("   Review changes and remove backups when satisfied")