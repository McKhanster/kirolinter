# KiroLinter Technical Specification

## Overview

KiroLinter is an AI-driven code review tool that combines AST-based static analysis with intelligent suggestions to help teams maintain high-quality Python codebases. This specification details the core modules, their interactions, and implementation requirements.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface (Click)                    │
├─────────────────────────────────────────────────────────────┤
│                   Core Analysis Engine                      │
├─────────────────────────────────────────────────────────────┤
│  Scanner  │  Suggester  │  Style Analyzer  │  CVE Checker  │
├─────────────────────────────────────────────────────────────┤
│           GitHub Integration  │  Report Generator           │
├─────────────────────────────────────────────────────────────┤
│              Repository Handler & File System              │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules Specification

### 1. Code Scanner Module (`kirolinter/core/scanner.py`)

#### Purpose
Performs AST-based static analysis to detect code quality issues, security vulnerabilities, and performance bottlenecks in Python code.

#### Key Components

##### 1.1 BaseScanner Class
```python
class BaseScanner:
    def __init__(self, config: Dict[str, Any])
    def scan_file(self, file_path: Path) -> ScanResult
    def _analyze_ast(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]
    def _calculate_metrics(self, tree: ast.AST, content: str) -> Dict[str, Any]
```

**Responsibilities:**
- Parse Python files into AST representations
- Provide base functionality for all scanner types
- Calculate basic code metrics (LOC, functions, classes, imports)
- Handle parsing errors gracefully

##### 1.2 CodeSmellScanner Class
```python
class CodeSmellScanner(BaseScanner):
    def _find_unused_variables(self, tree: ast.AST, file_path: str) -> List[Issue]
    def _find_unused_imports(self, tree: ast.AST, file_path: str) -> List[Issue]
    def _find_dead_code(self, tree: ast.AST, file_path: str) -> List[Issue]
    def _find_complex_functions(self, tree: ast.AST, file_path: str) -> List[Issue]
```

**Detection Algorithms:**

*Unused Variables:*
- Track variable assignments using `ast.Name` nodes with `ast.Store` context
- Track variable usage using `ast.Name` nodes with `ast.Load` context
- Exclude variables starting with underscore (convention for intentionally unused)
- Handle function parameters and loop variables as implicitly used

*Unused Imports:*
- Extract import statements using `ast.Import` and `ast.ImportFrom` nodes
- Track imported names and their aliases
- Scan for usage of imported names in the code
- Report imports that are never referenced

*Dead Code Detection:*
- Identify unreachable statements after `return`, `raise`, `break`, `continue`
- Use control flow analysis to detect unreachable branches
- Handle exception handling and conditional returns

*Complex Functions:*
- Calculate cyclomatic complexity using decision points
- Count `if`, `while`, `for`, `try/except`, boolean operators
- Configurable complexity threshold (default: 10)

##### 1.3 SecurityScanner Class
```python
class SecurityScanner(BaseScanner):
    def _find_sql_injection_risks(self, tree: ast.AST, file_path: str) -> List[Issue]
    def _find_hardcoded_secrets(self, tree: ast.AST, file_path: str, content: str) -> List[Issue]
    def _find_unsafe_operations(self, tree: ast.AST, file_path: str) -> List[Issue]
```

**Detection Algorithms:**

*SQL Injection Detection:*
- Identify database operation calls (`cursor.execute`, `connection.query`)
- Detect string formatting operations (`%`, `.format()`, f-strings) in SQL contexts
- Flag parameterized query violations
- Support multiple database libraries (sqlite3, psycopg2, mysql-connector)

*Hardcoded Secrets Detection:*
- AST-based detection of assignment nodes with secret-like variable names
- Pattern matching for common secret formats (API keys, passwords, tokens)
- Regex fallback for edge cases not caught by AST analysis
- Exclude obvious placeholders and test values

*Unsafe Operations:*
- Detect `eval()` and `exec()` function calls
- Identify `pickle.loads()` with untrusted data
- Flag `subprocess` calls with shell=True
- Detect `input()` usage in security-sensitive contexts

##### 1.4 PerformanceScanner Class
```python
class PerformanceScanner(BaseScanner):
    def _find_inefficient_loops(self, tree: ast.AST, file_path: str) -> List[Issue]
    def _find_redundant_operations(self, tree: ast.AST, file_path: str) -> List[Issue]
```

**Detection Algorithms:**

*Inefficient Loop Patterns:*
- String concatenation in loops (should use `join()`)
- List concatenation with `+` operator in loops
- Repeated `append()` calls (suggest list comprehension)
- Nested loops with O(n²) complexity

*Redundant Operations:*
- `len()` calls in loop conditions (should cache result)
- Repeated dictionary lookups (should cache or use `get()`)
- Redundant type conversions
- Unnecessary function calls in loops

#### AST Visitor Implementation

The scanner uses custom AST visitors for efficient traversal:

```python
class IssueDetectorVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, issues: List[Issue]):
        self.file_path = file_path
        self.issues = issues
        self.scope_stack = []  # Track variable scopes
        
    def visit_FunctionDef(self, node):
        # Enter new scope
        self.scope_stack.append({})
        self.generic_visit(node)
        self.scope_stack.pop()
        
    def visit_Name(self, node):
        # Track variable assignments and usage
        if isinstance(node.ctx, ast.Store):
            self._record_assignment(node)
        elif isinstance(node.ctx, ast.Load):
            self._record_usage(node)
```

### 2. Suggestion Engine Module (`kirolinter/core/suggester.py`)

#### Purpose
Generates intelligent fix suggestions for detected issues using rule-based templates and optional AI enhancement.

#### Key Components

##### 2.1 RuleBasedSuggester Class
```python
class RuleBasedSuggester:
    def __init__(self, templates_path: Optional[str] = None)
    def generate_suggestion(self, issue: Issue) -> Optional[Suggestion]
    def _load_templates(self) -> Dict[str, Dict[str, Any]]
    def _generate_code_suggestion(self, issue: Issue, template: Dict[str, Any]) -> str
```

**Template System:**
- JSON-based templates for each rule type
- Configurable confidence scores
- Context-aware code generation
- Support for multiple fix strategies per issue type

**Template Structure:**
```json
{
  "rule_id": {
    "fix_type": "REPLACE|DELETE|INSERT|REFACTOR",
    "confidence": 0.85,
    "template": "Human-readable description with {placeholders}",
    "explanation": "Detailed explanation of the issue and fix",
    "code_template": "Actual code replacement with {variables}",
    "prerequisites": ["required imports", "dependencies"]
  }
}
```

##### 2.2 OpenAISuggester Class
```python
class OpenAISuggester:
    def __init__(self, api_key: str)
    def generate_suggestion(self, issue: Issue, context: str = "") -> Optional[Suggestion]
    def _create_prompt(self, issue: Issue, context: str) -> str
    def _parse_ai_response(self, issue: Issue, response: str) -> Suggestion
```

**AI Integration:**
- OpenAI GPT-3.5/4 integration for complex issues
- Context-aware prompting with code snippets
- Confidence scoring based on AI response quality
- Fallback to rule-based suggestions on API failure

##### 2.3 TeamStyleAnalyzer Class
```python
class TeamStyleAnalyzer:
    def __init__(self, repo_path: str)
    def analyze_team_style(self) -> Dict[str, Any]
    def prioritize_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]
    def customize_suggestion(self, suggestion: Suggestion) -> Suggestion
```

**Style Analysis:**
- Git commit history analysis for coding patterns
- Naming convention detection (snake_case vs camelCase)
- Code structure preferences (early returns, list comprehensions)
- Import organization patterns
- Security preferences (environment variable naming)

**Prioritization Algorithm:**
```python
def calculate_priority(suggestion: Suggestion) -> float:
    base_confidence = suggestion.confidence
    issue_type_multiplier = team_preferences["priority_rules"][issue_type]
    style_alignment_bonus = calculate_style_alignment(suggestion)
    return base_confidence * issue_type_multiplier * (1 + style_alignment_bonus)
```

### 3. Report Generator Module (`kirolinter/reporting/`)

#### Purpose
Generates structured reports in multiple formats with optional diff patches for suggested fixes.

#### Key Components

##### 3.1 JSONReporter Class
```python
class JSONReporter:
    def __init__(self, include_diffs: bool = False)
    def generate_report(self, target: str, scan_results: List[ScanResult], 
                       total_files: int, analysis_time: float, 
                       errors: List[str] = None) -> str
```

**Report Structure:**
```json
{
  "kirolinter_version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "target": "path/to/analyzed/code",
  "summary": {
    "total_files_analyzed": 45,
    "total_issues_found": 12,
    "analysis_time_seconds": 1.23,
    "issues_by_severity": {"critical": 0, "high": 2, "medium": 5, "low": 5},
    "issues_by_type": {"code_smell": 8, "security": 2, "performance": 2},
    "has_critical_issues": false
  },
  "files": [
    {
      "file_path": "src/app.py",
      "issues": [
        {
          "id": "unique_issue_id",
          "type": "security",
          "severity": "high",
          "line_number": 15,
          "column": 0,
          "message": "Hardcoded API key detected",
          "rule_id": "hardcoded_api_key",
          "cve_id": null,
          "suggested_fix": {
            "fix_type": "replace",
            "suggested_code": "os.environ.get('API_KEY', 'default')",
            "confidence": 0.9,
            "explanation": "Use environment variables for secrets",
            "diff_patch": "--- a/src/app.py\n+++ b/src/app.py\n..."
          }
        }
      ],
      "metrics": {
        "lines_of_code": 234,
        "functions": 12,
        "classes": 3,
        "imports": 8
      },
      "parse_errors": []
    }
  ],
  "metadata": {
    "rules_applied": ["unused_variable", "hardcoded_secret"],
    "file_extensions_analyzed": [".py"],
    "excluded_patterns": ["tests/*", "__pycache__/*"]
  }
}
```

##### 3.2 DiffGenerator Class
```python
class DiffGenerator:
    def generate_patch(self, issue: Issue) -> Optional[str]
    def _apply_fix(self, original_lines: List[str], issue: Issue) -> Optional[List[str]]
    def generate_suggestion_text(self, issue: Issue) -> str
```

**Diff Generation Algorithms:**
- Unified diff format compatible with Git
- Context-aware line replacement
- Import statement handling for environment variable fixes
- Multi-line fix support for complex refactoring

## Implementation Guidelines

### AST Visitor Patterns

Use the visitor pattern for efficient AST traversal:

```python
class CustomVisitor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        # Process function definition
        self.analyze_function(node)
        self.generic_visit(node)  # Continue traversal
    
    def visit_Call(self, node):
        # Process function calls
        if self.is_database_call(node):
            self.check_sql_injection(node)
        self.generic_visit(node)
```

### Error Handling Strategy

Implement graceful degradation:

```python
def scan_file(self, file_path: Path) -> ScanResult:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
        issues = self._analyze_ast(tree, str(file_path), content)
        return ScanResult(file_path=str(file_path), issues=issues, parse_errors=[])
    except SyntaxError as e:
        return ScanResult(file_path=str(file_path), issues=[], 
                         parse_errors=[f"Syntax error: {str(e)}"])
    except Exception as e:
        return ScanResult(file_path=str(file_path), issues=[], 
                         parse_errors=[f"Analysis error: {str(e)}"])
```

### Performance Optimization

- Use `ast.walk()` for simple traversals
- Implement custom visitors for complex analysis
- Cache expensive operations (file I/O, regex compilation)
- Process files concurrently when possible
- Implement early termination for large files

### Testing Strategy

#### Unit Tests
- Test each scanner class independently
- Mock file system operations
- Use synthetic AST trees for edge cases
- Test suggestion generation with known inputs

#### Integration Tests
- Test complete analysis pipeline
- Use real Python files with known issues
- Verify JSON report structure and content
- Test diff generation accuracy

#### Performance Tests
- Benchmark analysis speed on large codebases
- Memory usage profiling
- Concurrent processing validation

## Inline AI Coding Recommendations

### Scanner Enhancement Prompts

1. **"Generate AST visitor code for detecting nested loop patterns that could be optimized with set operations or dictionary lookups"**

2. **"Create a visitor class to detect potential memory leaks in Python code, focusing on circular references and unclosed resources"**

3. **"Generate code to detect anti-patterns in exception handling, such as bare except clauses and exception swallowing"**

### Suggester Template Prompts

4. **"Generate suggestion templates for refactoring complex conditional statements into guard clauses or strategy patterns"**

5. **"Create templates for converting imperative loops into functional programming constructs (map, filter, reduce)"**

6. **"Generate templates for adding type hints to function signatures based on usage patterns in the code"**

### Report Generator Prompts

7. **"Create code to generate HTML reports with syntax highlighting and interactive issue filtering"**

8. **"Generate code for creating diff visualizations that show before/after code with highlighted changes"**

## CI/CD Integration Specification

### GitHub Actions Workflow

The CI/CD pipeline provides automated code review through GitHub Actions:

#### Workflow Triggers
- Pull requests to `main` or `develop` branches
- Push events to PR branches
- Manual workflow dispatch

#### Analysis Process
1. **File Detection**: Identify changed Python files in the PR
2. **Analysis Execution**: Run KiroLinter on changed files only
3. **Report Generation**: Create JSON report with suggestions and diffs
4. **Comment Posting**: Use reviewdog for line-specific comments
5. **Summary Generation**: Post overall analysis summary
6. **Status Check**: Set PR status based on critical issues

#### Integration Components

**Reviewdog Integration:**
- Converts JSON output to reviewdog diagnostic format
- Posts line-specific comments on PR files
- Filters comments to show only issues in changed lines

**GitHub API Integration:**
- Posts summary comments with analysis overview
- Creates status checks for PR merge protection
- Uploads analysis artifacts for debugging

**Security Considerations:**
- Minimal required permissions (contents: read, pull-requests: write)
- Secure token handling
- No sensitive data in logs or artifacts

This specification provides the foundation for implementing a robust, scalable, and maintainable code analysis tool with intelligent suggestions and seamless CI/CD integration.