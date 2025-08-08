"""
AST parsing utilities for code analysis.
"""

import ast
from typing import List, Dict, Any, Optional


class ASTHelper:
    """Helper class for AST operations."""
    
    @staticmethod
    def get_function_names(tree: ast.AST) -> List[str]:
        """Extract all function names from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    
    @staticmethod
    def get_class_names(tree: ast.AST) -> List[str]:
        """Extract all class names from AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    
    @staticmethod
    def get_imports(tree: ast.AST) -> List[str]:
        """Extract all import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports
    
    @staticmethod
    def find_string_literals(tree: ast.AST) -> List[tuple]:
        """Find all string literals with their positions."""
        literals = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Str):  # Python < 3.8
                literals.append((node.s, node.lineno, node.col_offset))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):  # Python >= 3.8
                literals.append((node.value, node.lineno, node.col_offset))
        return literals
    
    @staticmethod
    def get_node_source(node: ast.AST, source_lines: List[str]) -> str:
        """Extract source code for a specific AST node."""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            return '\n'.join(source_lines[start_line:end_line])
        return ""