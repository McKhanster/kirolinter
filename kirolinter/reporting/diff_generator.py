"""
Diff/patch generation for suggested code fixes.
"""

import difflib
from typing import Optional, List
from pathlib import Path

from kirolinter.models.issue import Issue


class DiffGenerator:
    """Generate diff patches for code fixes."""
    
    def generate_patch(self, issue: Issue) -> Optional[str]:
        """
        Generate a diff patch for fixing an issue.
        
        Args:
            issue: The issue to generate a fix for
        
        Returns:
            Diff patch string or None if no fix available
        """
        try:
            # Read the original file
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
            
            # Generate fixed version based on issue type
            fixed_lines = self._apply_fix(original_lines, issue)
            
            if fixed_lines is None or fixed_lines == original_lines:
                return None
            
            # Generate unified diff
            diff = difflib.unified_diff(
                original_lines,
                fixed_lines,
                fromfile=f"a/{issue.file_path}",
                tofile=f"b/{issue.file_path}",
                lineterm=''
            )
            
            return '\n'.join(diff)
            
        except Exception:
            return None
    
    def _apply_fix(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]:
        """
        Apply a fix to the original lines based on the issue type.
        
        Args:
            original_lines: Original file lines
            issue: Issue to fix
        
        Returns:
            Fixed lines or None if no fix available
        """
        if issue.rule_id == "unused_variable":
            return self._fix_unused_variable(original_lines, issue)
        elif issue.rule_id == "unused_import":
            return self._fix_unused_import(original_lines, issue)
        elif issue.rule_id == "dead_code":
            return self._fix_dead_code(original_lines, issue)
        elif issue.rule_id == "hardcoded_secret":
            return self._fix_hardcoded_secret(original_lines, issue)
        else:
            return None
    
    def _fix_unused_variable(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]:
        """Fix unused variable by removing the assignment."""
        fixed_lines = original_lines.copy()
        line_index = issue.line_number - 1
        
        if 0 <= line_index < len(fixed_lines):
            line = fixed_lines[line_index]
            
            # Simple case: remove entire line if it's just an assignment
            if '=' in line and line.strip().endswith(('\'', '"', ')', ']', '}')) or line.strip().endswith(tuple('0123456789')):
                # Check if this is a simple assignment line
                if not line.strip().startswith(('if ', 'elif ', 'while ', 'for ', 'def ', 'class ')):
                    # Remove the line
                    fixed_lines.pop(line_index)
                    return fixed_lines
        
        return None
    
    def _fix_unused_import(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]:
        """Fix unused import by removing the import statement."""
        fixed_lines = original_lines.copy()
        line_index = issue.line_number - 1
        
        if 0 <= line_index < len(fixed_lines):
            line = fixed_lines[line_index]
            
            # Remove entire import line
            if line.strip().startswith(('import ', 'from ')):
                fixed_lines.pop(line_index)
                return fixed_lines
        
        return None
    
    def _fix_dead_code(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]:
        """Fix dead code by removing unreachable statements."""
        fixed_lines = original_lines.copy()
        line_index = issue.line_number - 1
        
        if 0 <= line_index < len(fixed_lines):
            # Remove the dead code line
            fixed_lines.pop(line_index)
            return fixed_lines
        
        return None
    
    def _fix_hardcoded_secret(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]:
        """Fix hardcoded secret by replacing with environment variable."""
        fixed_lines = original_lines.copy()
        line_index = issue.line_number - 1
        
        if 0 <= line_index < len(fixed_lines):
            line = fixed_lines[line_index]
            
            # Replace hardcoded value with environment variable
            if '=' in line:
                var_name, value_part = line.split('=', 1)
                var_name = var_name.strip()
                
                # Generate environment variable name based on variable name
                if 'api_key' in var_name.lower():
                    env_var_name = 'API_KEY'
                elif 'password' in var_name.lower():
                    env_var_name = 'PASSWORD'
                elif 'secret' in var_name.lower():
                    env_var_name = 'SECRET_KEY'
                elif 'token' in var_name.lower():
                    env_var_name = 'ACCESS_TOKEN'
                else:
                    env_var_name = var_name.upper().replace(' ', '_')
                
                # Replace with os.environ.get()
                indent = len(line) - len(line.lstrip())
                new_line = ' ' * indent + f'{var_name} = os.environ.get("{env_var_name}", "your_{env_var_name.lower()}_here")\n'
                
                fixed_lines[line_index] = new_line
                
                # Add import if not present
                has_os_import = any('import os' in line or 'from os import' in line for line in fixed_lines)
                if not has_os_import:
                    # Find a good place to add the import (after existing imports)
                    import_index = 0
                    for i, line in enumerate(fixed_lines):
                        if line.strip().startswith(('import ', 'from ')):
                            import_index = i + 1
                        elif line.strip() and not line.strip().startswith('#'):
                            break
                    
                    fixed_lines.insert(import_index, 'import os\n')
                
                return fixed_lines
        
        return None
    
    def generate_suggestion_text(self, issue: Issue) -> str:
        """
        Generate human-readable suggestion text for an issue.
        
        Args:
            issue: Issue to generate suggestion for
        
        Returns:
            Suggestion text
        """
        suggestions = {
            "unused_variable": "Remove the unused variable assignment.",
            "unused_import": "Remove the unused import statement.",
            "dead_code": "Remove the unreachable code after the return statement.",
            "hardcoded_secret": "Replace hardcoded secret with environment variable using os.environ.get().",
            "sql_injection": "Use parameterized queries instead of string formatting.",
            "unsafe_eval": "Replace eval() with safer alternatives like json.loads() or ast.literal_eval().",
            "unsafe_exec": "Avoid using exec() or validate input thoroughly before execution.",
            "complex_function": "Consider breaking this function into smaller, more focused functions.",
            "inefficient_loop_concat": "Use list comprehension or str.join() instead of concatenation in loops.",
            "redundant_len_in_loop": "Cache the len() result outside the loop to improve performance."
        }
        
        return suggestions.get(issue.rule_id, "Consider reviewing this code for potential improvements.")