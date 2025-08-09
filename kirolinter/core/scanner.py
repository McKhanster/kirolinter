"""
Code scanner module for detecting issues in Python code using AST analysis.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass

from kirolinter.models.issue import Issue, IssueType, Severity
from kirolinter.utils.ast_helpers import ASTHelper


@dataclass
class ScanResult:
    """Result of scanning a single file."""
    file_path: str
    issues: List[Issue]
    parse_errors: List[str]
    metrics: Dict[str, Any]
    
    def has_critical_issues(self) -> bool:
        """Check if any issue has critical severity."""
        return any(issue.severity == Severity.CRITICAL for issue in self.issues)


class BaseScanner:
    """Base class for all code scanners."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ast_helper = ASTHelper()
    
    def scan_file(self, file_path: Path) -> ScanResult:
        """Scan a single Python file for issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Run analysis
            issues = self._analyze_ast(tree, str(file_path), content)
            metrics = self._calculate_metrics(tree, content)
            
            return ScanResult(
                file_path=str(file_path),
                issues=issues,
                parse_errors=[],
                metrics=metrics
            )
            
        except SyntaxError as e:
            return ScanResult(
                file_path=str(file_path),
                issues=[],
                parse_errors=[f"Syntax error: {str(e)}"],
                metrics={}
            )
        except Exception as e:
            return ScanResult(
                file_path=str(file_path),
                issues=[],
                parse_errors=[f"Analysis error: {str(e)}"],
                metrics={}
            )
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]:
        """Override in subclasses to implement specific analysis."""
        raise NotImplementedError
    
    def _calculate_metrics(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Calculate basic code metrics."""
        return {
            'lines_of_code': len(content.splitlines()),
            'functions': len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
            'classes': len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]),
            'imports': len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))])
        }


class CodeSmellScanner(BaseScanner):
    """Scanner for detecting code smells like unused variables."""
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]:
        """Analyze AST for code smell issues."""
        issues = []
        
        # Find unused variables
        issues.extend(self._find_unused_variables(tree, file_path))
        
        # Find dead code
        issues.extend(self._find_dead_code(tree, file_path))
        
        # Find complex functions
        issues.extend(self._find_complex_functions(tree, file_path))
        
        return issues
    
    def _find_unused_variables(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find unused variables in the AST."""
        issues = []
        
        # Track variable assignments and usage
        assigned_vars = {}  # name -> (line_number, node)
        used_vars = set()
        
        class VariableVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    # Variable assignment
                    assigned_vars[node.id] = (node.lineno, node)
                elif isinstance(node.ctx, ast.Load):
                    # Variable usage
                    used_vars.add(node.id)
                self.generic_visit(node)
            
            def visit_FunctionDef(self, node):
                # Function parameters are considered used
                for arg in node.args.args:
                    used_vars.add(arg.arg)
                self.generic_visit(node)
            
            def visit_For(self, node):
                # For loop variables are considered used
                if isinstance(node.target, ast.Name):
                    used_vars.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            used_vars.add(elt.id)
                self.generic_visit(node)
        
        visitor = VariableVisitor()
        visitor.visit(tree)
        
        # Find unused variables
        for var_name, (line_no, node) in assigned_vars.items():
            if var_name not in used_vars and not var_name.startswith('_'):
                issues.append(Issue(
                    id=f"unused_var_{var_name}_{line_no}",
                    type=IssueType.CODE_SMELL,
                    severity=Severity.LOW,
                    file_path=file_path,
                    line_number=line_no,
                    column=node.col_offset,
                    message=f"Unused variable '{var_name}'",
                    rule_id="unused_variable"
                ))
        
        # Find unused imports
        issues.extend(self._find_unused_imports(tree, file_path))
        
        return issues
    
    def _find_unused_imports(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find unused imports in the AST."""
        issues = []
        
        # Get all imports
        imports = self.ast_helper.get_imports(tree)
        imported_names = set()
        import_nodes = {}
        
        # Track import statements and their names
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    imported_names.add(name)
                    import_nodes[name] = (node.lineno, node.col_offset)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imported_names.add(name)
                    import_nodes[name] = (node.lineno, node.col_offset)
        
        # Find used names
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
        
        # Find unused imports
        for import_name in imported_names:
            if import_name not in used_names and import_name != '*':
                line_no, col_offset = import_nodes[import_name]
                issues.append(Issue(
                    id=f"unused_import_{import_name}_{line_no}",
                    type=IssueType.CODE_SMELL,
                    severity=Severity.LOW,
                    file_path=file_path,
                    line_number=line_no,
                    column=col_offset,
                    message=f"Unused import '{import_name}'",
                    rule_id="unused_import"
                ))
        
        return issues
    
    def _find_dead_code(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find unreachable code (dead code)."""
        issues = []
        
        class DeadCodeVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Check for code after return statements
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return):
                        # Check if there are statements after this return
                        if i < len(node.body) - 1:
                            next_stmt = node.body[i + 1]
                            issues.append(Issue(
                                id=f"dead_code_{next_stmt.lineno}",
                                type=IssueType.CODE_SMELL,
                                severity=Severity.MEDIUM,
                                file_path=file_path,
                                line_number=next_stmt.lineno,
                                column=next_stmt.col_offset,
                                message="Unreachable code after return statement",
                                rule_id="dead_code"
                            ))
                            break
                self.generic_visit(node)
        
        visitor = DeadCodeVisitor()
        visitor.visit(tree)
        
        return issues
    
    def _find_complex_functions(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find overly complex functions."""
        issues = []
        max_complexity = self.config.get('max_complexity', 10)
        
        class ComplexityVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > max_complexity:
                    issues.append(Issue(
                        id=f"complex_function_{node.name}_{node.lineno}",
                        type=IssueType.CODE_SMELL,
                        severity=Severity.MEDIUM if complexity <= 15 else Severity.HIGH,
                        file_path=file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has high cyclomatic complexity ({complexity})",
                        rule_id="complex_function"
                    ))
                self.generic_visit(node)
            
            def _calculate_cyclomatic_complexity(self, node):
                """Calculate cyclomatic complexity for a function."""
                complexity = 1  # Base complexity
                
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                        complexity += 1
                    elif isinstance(child, ast.ExceptHandler):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                
                return complexity
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        
        return issues


class SecurityScanner(BaseScanner):
    """Scanner for detecting security vulnerabilities."""
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]:
        """Analyze AST for security issues."""
        issues = []
        
        # Find SQL injection risks
        issues.extend(self._find_sql_injection_risks(tree, file_path))
        
        # Find hardcoded secrets
        issues.extend(self._find_hardcoded_secrets(tree, file_path, content))
        
        # Find unsafe imports and eval usage
        issues.extend(self._find_unsafe_operations(tree, file_path))
        
        return issues
    
    def _find_sql_injection_risks(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find potential SQL injection vulnerabilities."""
        issues = []
        
        class SQLInjectionVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check for string formatting in SQL-like contexts
                if (isinstance(node.func, ast.Attribute) and 
                    hasattr(node.func, 'attr') and 
                    node.func.attr in ['execute', 'executemany']):
                    
                    if node.args:
                        arg = node.args[0]
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                            # String formatting with % operator
                            issues.append(Issue(
                                id=f"sql_injection_{node.lineno}",
                                type=IssueType.SECURITY,
                                severity=Severity.HIGH,
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                message="Potential SQL injection: use parameterized queries instead of string formatting",
                                rule_id="sql_injection"
                            ))
                
                self.generic_visit(node)
        
        visitor = SQLInjectionVisitor()
        visitor.visit(tree)
        
        return issues
    
    def _find_hardcoded_secrets(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]:
        """Find hardcoded secrets in the code."""
        issues = []
        
        # AST-based detection using string literals
        string_literals = self.ast_helper.find_string_literals(tree)
        
        # Patterns for secret detection in variable names and string values
        secret_keywords = ['password', 'api_key', 'secret', 'token', 'private_key', 'access_key']
        
        # Check AST assignments for hardcoded secrets
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id.lower()
                        if any(keyword in var_name for keyword in secret_keywords):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                # Skip obvious placeholders
                                value = node.value.value
                                if not any(placeholder in value.lower() for placeholder in ['placeholder', 'your_', 'example', 'test']):
                                    issues.append(Issue(
                                        id=f"hardcoded_secret_{target.id}_{node.lineno}",
                                        type=IssueType.SECURITY,
                                        severity=Severity.HIGH,
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        message=f"Potential hardcoded secret in variable '{target.id}'",
                                        rule_id="hardcoded_secret"
                                    ))
        
        # Fallback: regex patterns for edge cases
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'hardcoded_password'),
            (r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']', 'hardcoded_api_key'),
            (r'secret\s*=\s*["\'][A-Za-z0-9]{16,}["\']', 'hardcoded_secret'),
            (r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']', 'hardcoded_token'),
        ]
        
        lines = content.splitlines()
        for line_no, line in enumerate(lines, 1):
            for pattern, rule_id in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Avoid duplicates from AST detection
                    existing_ids = {issue.id for issue in issues}
                    new_id = f"{rule_id}_{line_no}"
                    if new_id not in existing_ids:
                        issues.append(Issue(
                            id=new_id,
                            type=IssueType.SECURITY,
                            severity=Severity.HIGH,
                            file_path=file_path,
                            line_number=line_no,
                            column=0,
                            message=f"Potential hardcoded secret detected (regex fallback)",
                            rule_id=rule_id
                        ))
        
        return issues
    
    def _find_unsafe_operations(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find unsafe operations like eval() usage."""
        issues = []
        
        class UnsafeOperationVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        issues.append(Issue(
                            id=f"unsafe_{node.func.id}_{node.lineno}",
                            type=IssueType.SECURITY,
                            severity=Severity.CRITICAL,
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            message=f"Unsafe use of {node.func.id}() function",
                            rule_id=f"unsafe_{node.func.id}"
                        ))
                
                self.generic_visit(node)
        
        visitor = UnsafeOperationVisitor()
        visitor.visit(tree)
        
        return issues


class PerformanceScanner(BaseScanner):
    """Scanner for detecting performance bottlenecks."""
    
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str, config: Dict[str, Any] = None) -> List[Issue]:
        """Analyze AST for performance issues with graceful error handling."""
        issues = []
        config = config or {}
        
        try:
            # Find inefficient loops
            issues.extend(self._find_inefficient_loops(tree, file_path))
            
            # Find redundant operations
            issues.extend(self._find_redundant_operations(tree, file_path))
            
        except Exception as e:
            # Graceful fallback for intentional parse errors or analysis issues
            if config.get('verbose', False):
                print(f"Warning: Performance analysis encountered an issue in {file_path}: {e}")
            
            # Create a fallback issue to indicate analysis limitation
            issues.append(Issue(
                id=f"analysis_limitation_{hash(file_path)}",
                type=IssueType.CODE_SMELL,
                severity=Severity.LOW,
                file_path=file_path,
                line_number=1,
                column=0,
                message="Performance analysis encountered limitations - manual review recommended",
                rule_id="analysis_fallback"
            ))
        
        return issues
    
    def _find_inefficient_loops(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find inefficient loop patterns."""
        issues = []
        
        class LoopVisitor(ast.NodeVisitor):
            def visit_For(self, node):
                # Check for list concatenation in loops
                for stmt in ast.walk(node):
                    if (isinstance(stmt, ast.AugAssign) and 
                        isinstance(stmt.op, ast.Add) and
                        isinstance(stmt.target, ast.Name)):
                        
                        issues.append(Issue(
                            id=f"inefficient_loop_{node.lineno}",
                            type=IssueType.PERFORMANCE,
                            severity=Severity.MEDIUM,
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            message="Inefficient list concatenation in loop - consider using list comprehension or join()",
                            rule_id="inefficient_loop_concat"
                        ))
                
                self.generic_visit(node)
        
        visitor = LoopVisitor()
        visitor.visit(tree)
        
        return issues
    
    def _find_redundant_operations(self, tree: ast.AST, file_path: str) -> List[Issue]:
        """Find redundant operations that could be optimized."""
        issues = []
        
        # This is a simplified example - real implementation would be more sophisticated
        class RedundantOpVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check for len() in loops (could be cached)
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'len' and
                    self._is_in_loop_condition(node)):
                    
                    issues.append(Issue(
                        id=f"redundant_len_{node.lineno}",
                        type=IssueType.PERFORMANCE,
                        severity=Severity.LOW,
                        file_path=file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message="Consider caching len() result outside loop",
                        rule_id="redundant_len_in_loop"
                    ))
                
                self.generic_visit(node)
            
            def _is_in_loop_condition(self, node):
                """Check if a node is in a loop condition by traversing parent nodes."""
                # This is a simplified implementation - in a real scenario,
                # you'd need to track parent nodes during AST traversal
                current = node
                while hasattr(current, 'parent'):
                    parent = current.parent
                    if isinstance(parent, (ast.For, ast.While)):
                        # Check if the node is in the condition/iterator part
                        if (isinstance(parent, ast.For) and current in ast.walk(parent.iter)) or \
                           (isinstance(parent, ast.While) and current in ast.walk(parent.test)):
                            return True
                    current = parent
                return False
        
        visitor = RedundantOpVisitor()
        visitor.visit(tree)
        
        return issues


class CodeScanner:
    """Main scanner that orchestrates all individual scanners."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scanners = [
            CodeSmellScanner(config),
            SecurityScanner(config),
            PerformanceScanner(config)
        ]
    
    def scan_file(self, file_path: Path) -> ScanResult:
        """Scan a file using all enabled scanners."""
        all_issues = []
        all_errors = []
        combined_metrics = {}
        
        for scanner in self.scanners:
            result = scanner.scan_file(file_path)
            all_issues.extend(result.issues)
            all_errors.extend(result.parse_errors)
            combined_metrics.update(result.metrics)
        
        return ScanResult(
            file_path=str(file_path),
            issues=all_issues,
            parse_errors=all_errors,
            metrics=combined_metrics
        )