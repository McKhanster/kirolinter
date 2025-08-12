"""
LangChain tool wrapper for KiroLinter scanner functionality.
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ...core.scanner import CodeScanner
from ...core.engine import AnalysisEngine
from ...models.config import Config


class ScannerInput(BaseModel):
    """Input schema for scanner tool."""
    file_path: str = Field(description="Path to Python file to analyze")
    rules: Optional[List[str]] = Field(default=None, description="Specific rules to apply")
    severity: Optional[str] = Field(default="low", description="Minimum severity level")


class ScannerTool(BaseTool):
    """LangChain tool for code scanning and analysis."""
    
    name: str = "code_scanner"
    description: str = """
    Scan Python code files for quality issues, security vulnerabilities, and performance bottlenecks.
    
    This tool analyzes Python code using AST parsing and detects:
    - Code smells: unused variables, dead code, complex functions
    - Security issues: SQL injection risks, hardcoded secrets, unsafe imports
    - Performance issues: inefficient loops, redundant operations
    
    Returns detailed analysis results with issue locations, severity, and descriptions.
    """
    args_schema: type[BaseModel] = ScannerInput
    
    def _run(self, file_path: str, rules: Optional[List[str]] = None, severity: str = "low") -> Dict[str, Any]:
        """Execute code scanning on the specified file."""
        try:
            # Initialize scanner with configuration
            config = Config()
            if rules:
                config.enabled_rules = rules
            config.min_severity = severity
            
            scanner = CodeScanner(config)
            
            # Perform analysis
            issues = scanner.scan_file(file_path)
            
            # Format results for agent consumption
            result = {
                "file_path": file_path,
                "total_issues": len(issues),
                "issues_by_severity": {},
                "issues_by_type": {},
                "issues": []
            }
            
            # Categorize issues
            for issue in issues:
                # Count by severity
                severity_key = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                result["issues_by_severity"][severity_key] = result["issues_by_severity"].get(severity_key, 0) + 1
                
                # Count by type
                type_key = issue.type.value if hasattr(issue.type, 'value') else str(issue.type)
                result["issues_by_type"][type_key] = result["issues_by_type"].get(type_key, 0) + 1
                
                # Add issue details
                result["issues"].append({
                    "id": issue.id,
                    "type": type_key,
                    "severity": severity_key,
                    "line_number": issue.line_number,
                    "column": issue.column,
                    "message": issue.message,
                    "rule_id": issue.rule_id,
                    "cve_id": issue.cve_id
                })
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to scan file {file_path}: {str(e)}",
                "file_path": file_path,
                "total_issues": 0,
                "issues": []
            }


@tool
def scan_repository(repo_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze entire repository for code quality issues.
    
    Args:
        repo_path: Path to repository root directory
        config_path: Optional path to configuration file
        
    Returns:
        Dictionary containing analysis results for all Python files in repository
    """
    import os
    import ast
    import time
    from pathlib import Path
    
    try:
        start_time = time.time()
        
        # Find all Python files in the repository
        python_files = []
        repo_path = Path(repo_path)
        
        if repo_path.is_file() and repo_path.suffix == '.py':
            python_files = [repo_path]
        else:
            # Recursively find Python files
            for root, dirs, files in os.walk(repo_path):
                # Skip common directories that shouldn't be analyzed
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(Path(root) / file)
        
        # Analyze each Python file
        all_issues = []
        files_analyzed = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Basic AST-based analysis
                file_issues = _analyze_python_file(str(file_path), content)
                
                files_analyzed.append({
                    "file_path": str(file_path),
                    "issues_count": len(file_issues),
                    "issues": file_issues
                })
                
                all_issues.extend(file_issues)
                
            except Exception as e:
                # Skip files that can't be parsed
                files_analyzed.append({
                    "file_path": str(file_path),
                    "issues_count": 1,
                    "issues": [{
                        "id": "parse_error",
                        "type": "syntax",
                        "severity": "high",
                        "line_number": 1,
                        "message": f"Failed to parse file: {str(e)}",
                        "rule_id": "E999"
                    }]
                })
        
        # Categorize issues
        issues_by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        issues_by_type = {}
        
        for issue in all_issues:
            severity = issue.get("severity", "low")
            issue_type = issue.get("type", "unknown")
            
            issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
            issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1
        
        analysis_time = time.time() - start_time
        
        return {
            "repository_path": str(repo_path),
            "total_files_analyzed": len(files_analyzed),
            "total_issues_found": len(all_issues),
            "analysis_time_seconds": round(analysis_time, 2),
            "issues_by_severity": issues_by_severity,
            "issues_by_type": issues_by_type,
            "has_critical_issues": issues_by_severity.get("critical", 0) > 0,
            "files": files_analyzed
        }
    
    except Exception as e:
        return {
            "error": f"Repository analysis failed: {str(e)}",
            "repository_path": str(repo_path) if repo_path else "unknown"
        }


def _analyze_python_file(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Analyze a single Python file for common issues.
    
    Args:
        file_path: Path to the file being analyzed
        content: File content as string
        
    Returns:
        List of issues found in the file
    """
    import ast
    import re
    
    issues = []
    
    try:
        # Parse the AST
        tree = ast.parse(content)
        
        # Check for common issues
        for node in ast.walk(tree):
            # Check for unused variables (simple heuristic)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                var_name = node.id
                if var_name.startswith('_') and not var_name.startswith('__'):
                    # Likely unused variable
                    issues.append({
                        "id": f"unused_var_{var_name}",
                        "type": "code_smell",
                        "severity": "low",
                        "line_number": node.lineno,
                        "message": f"Variable '{var_name}' may be unused",
                        "rule_id": "W0612"
                    })
            
            # Check for long functions (>50 lines)
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 50:
                        issues.append({
                            "id": f"long_function_{node.name}",
                            "type": "maintainability",
                            "severity": "medium",
                            "line_number": node.lineno,
                            "message": f"Function '{node.name}' is {func_length} lines long (consider breaking it down)",
                            "rule_id": "C0103"
                        })
            
            # Check for hardcoded strings that might be secrets
            if isinstance(node, ast.Str):
                value = node.s
                if re.search(r'(password|secret|key|token).*[=:].*[a-zA-Z0-9]{8,}', value, re.IGNORECASE):
                    issues.append({
                        "id": f"potential_secret_{node.lineno}",
                        "type": "security",
                        "severity": "high",
                        "line_number": node.lineno,
                        "message": "Potential hardcoded secret detected",
                        "rule_id": "S105"
                    })
        
        # Check for long lines (>100 characters)
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append({
                    "id": f"long_line_{i}",
                    "type": "style",
                    "severity": "low",
                    "line_number": i,
                    "message": f"Line too long ({len(line)} characters, should be ≤100)",
                    "rule_id": "E501"
                })
        
        # Check for missing docstrings in functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not ast.get_docstring(node):
                    issues.append({
                        "id": f"missing_docstring_{node.name}",
                        "type": "documentation",
                        "severity": "low",
                        "line_number": node.lineno,
                        "message": f"Function '{node.name}' is missing a docstring",
                        "rule_id": "D100"
                    })
    
    except SyntaxError as e:
        issues.append({
            "id": "syntax_error",
            "type": "syntax",
            "severity": "critical",
            "line_number": e.lineno or 1,
            "message": f"Syntax error: {e.msg}",
            "rule_id": "E999"
        })
    
    return issues


@tool  
def get_file_metrics(file_path: str) -> Dict[str, Any]:
    """
    Get code metrics for a Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        Dictionary containing code metrics like lines of code, functions, classes, complexity
    """
    try:
        scanner = CodeScanner(Config())
        metrics = scanner.get_file_metrics(file_path)
        
        return {
            "file_path": file_path,
            "lines_of_code": metrics.get("lines_of_code", 0),
            "functions": metrics.get("functions", 0),
            "classes": metrics.get("classes", 0),
            "imports": metrics.get("imports", 0),
            "complexity_score": metrics.get("complexity_score", 0),
            "maintainability_index": metrics.get("maintainability_index", 0)
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get metrics for {file_path}: {str(e)}",
            "file_path": file_path
        }