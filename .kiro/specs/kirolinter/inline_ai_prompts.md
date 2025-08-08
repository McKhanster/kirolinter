# Inline AI Coding Prompts for KiroLinter Templates

## Suggester Template Generation

### 1. Complex Function Refactoring
**Prompt**: "Generate a template for refactoring complex functions that suggests specific decomposition strategies like extract method, parameter object, and strategy pattern. Include confidence scoring based on complexity metrics."

**Expected Output**: Template with specific refactoring suggestions based on function complexity, parameter count, and cyclomatic complexity.

### 2. Security Vulnerability Templates
**Prompt**: "Create suggestion templates for fixing SQL injection vulnerabilities that work with different database libraries (sqlite3, psycopg2, mysql-connector-python, SQLAlchemy) and suggest appropriate parameterization syntax for each."

**Expected Output**: Database-specific templates with proper parameterized query syntax.

### 3. Performance Optimization Templates
**Prompt**: "Generate templates for fixing performance issues like inefficient loops, suggesting specific optimizations such as list comprehensions, generator expressions, caching, and algorithmic improvements."

**Expected Output**: Performance-focused templates with before/after code examples.

### 4. Import Organization Templates
**Prompt**: "Create templates for import organization that follow PEP 8 guidelines, including standard library first, third-party packages, local imports, and proper grouping with blank lines."

**Expected Output**: Import sorting and organization templates.

### 5. Type Hint Addition Templates
**Prompt**: "Generate templates for adding type hints to functions and variables, detecting the appropriate types from usage patterns and suggesting proper typing imports."

**Expected Output**: Type annotation templates with proper import suggestions.

## Diff Generator Enhancement

### 6. Multi-line Fix Generation
**Prompt**: "Create diff generation logic for multi-line fixes like refactoring nested if statements into guard clauses, with proper indentation handling."

**Expected Output**: Complex diff generation for structural changes.

### 7. Context-Aware Replacements
**Prompt**: "Generate context-aware code replacements that consider surrounding code patterns, variable names, and existing imports when suggesting fixes."

**Expected Output**: Smart replacement logic that adapts to code context.

## Team Style Analysis

### 8. Naming Convention Detection
**Prompt**: "Create code to analyze a codebase's naming conventions by examining variable names, function names, and class names to detect patterns like snake_case vs camelCase preferences."

**Expected Output**: Pattern detection algorithms for naming conventions.

### 9. Code Structure Preferences
**Prompt**: "Generate analysis code to detect team preferences for code structure like early returns vs nested conditions, list comprehensions vs loops, and function length preferences."

**Expected Output**: Code structure analysis algorithms.

## Advanced Security Templates

### 10. Cryptography Best Practices
**Prompt**: "Create templates for fixing cryptographic issues like weak random number generation, insecure hash algorithms, and improper key management, with suggestions for secure alternatives."

**Expected Output**: Cryptography-focused security templates.

### 11. Input Validation Templates
**Prompt**: "Generate templates for adding input validation to functions that process user data, including sanitization, type checking, and bounds validation."

**Expected Output**: Input validation templates with security focus.

## Code Quality Templates

### 12. Documentation Generation
**Prompt**: "Create templates for adding docstrings to functions and classes, detecting parameter types and return values to generate appropriate documentation."

**Expected Output**: Documentation templates with auto-generated content.

### 13. Error Handling Improvements
**Prompt**: "Generate templates for improving error handling by replacing bare except clauses with specific exception types and adding proper logging."

**Expected Output**: Error handling improvement templates.

## Testing Templates

### 14. Unit Test Generation
**Prompt**: "Create templates for generating unit tests for functions, detecting edge cases and creating appropriate test scenarios based on function parameters and logic."

**Expected Output**: Test generation templates with comprehensive coverage.

### 15. Mock Usage Templates
**Prompt**: "Generate templates for adding proper mocking to tests, detecting external dependencies and suggesting appropriate mock strategies."

**Expected Output**: Mocking templates for test improvement.

## Usage Examples

### How to Use These Prompts with Kiro

1. **Select relevant code section** in your editor
2. **Invoke Kiro's inline AI** (Ctrl+K or Cmd+K)
3. **Paste the prompt** and let Kiro generate the template
4. **Review and integrate** the generated template into your suggester

### Template Integration Process

1. **Generate template** using AI prompt
2. **Add to template files** in `kirolinter/config/templates/`
3. **Update suggester logic** to use new templates
4. **Add unit tests** for new template functionality
5. **Test with real code** to validate suggestions

### Quality Criteria for Generated Templates

- **Specificity**: Templates should be specific to the issue type
- **Confidence**: Include appropriate confidence scores (0.0-1.0)
- **Explanation**: Clear explanation of why the fix is needed
- **Code Quality**: Generated code should follow best practices
- **Context Awareness**: Consider surrounding code patterns

### Example Template Structure

```json
{
  "rule_name": {
    "fix_type": "REPLACE|DELETE|INSERT|REFACTOR",
    "confidence": 0.85,
    "template": "Human-readable description with {placeholders}",
    "explanation": "Detailed explanation of the issue and fix",
    "code_template": "Actual code replacement with {variables}",
    "prerequisites": ["required imports", "dependencies"],
    "alternatives": ["alternative approaches"]
  }
}
```

This structure ensures consistency and quality across all generated templates.