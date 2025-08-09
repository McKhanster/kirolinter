# Design Document

## Overview

KiroLinter is a CLI-based AI-driven code review tool built with Python that analyzes codebases for quality issues, security vulnerabilities, and performance bottlenecks. The tool leverages AST parsing, machine learning for style analysis, and integrates with GitHub for automated PR reviews. The architecture follows a modular design with clear separation of concerns for analysis, reporting, and integration capabilities.

## Architecture

The system follows a layered architecture with the following components:

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

## Project Structure

```
kirolinter/
├── kirolinter/
│   ├── __init__.py
│   ├── cli.py                    # Click-based CLI interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py             # Main analysis orchestrator
│   │   ├── scanner.py            # Code analysis and issue detection
│   │   ├── suggester.py          # AI-powered fix suggestions
│   │   └── style_analyzer.py     # Team style learning and analysis
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── github_client.py      # GitHub API integration
│   │   ├── cve_database.py       # CVE database integration
│   │   └── repository_handler.py # Git repository management
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── json_reporter.py      # JSON report generation
│   │   ├── diff_generator.py     # Patch/diff creation
│   │   └── formatters.py         # Output formatting utilities
│   ├── models/
│   │   ├── __init__.py
│   │   ├── issue.py              # Issue data models
│   │   ├── suggestion.py         # Suggestion data models
│   │   └── config.py             # Configuration models
│   └── utils/
│       ├── __init__.py
│       ├── ast_helpers.py        # AST parsing utilities
│       ├── performance_tracker.py # Performance monitoring
│       └── cache.py              # Caching mechanisms
├── tests/
│   ├── __init__.py
│   ├── test_scanner.py
│   ├── test_suggester.py
│   ├── test_github_integration.py
│   └── fixtures/                 # Test code samples
├── config/
│   ├── default_rules.yaml        # Default analysis rules
│   └── cve_patterns.json         # Security vulnerability patterns
├── .kiro/
│   ├── hooks/                    # Kiro agent hooks
│   │   ├── on_commit_analysis.md
│   │   └── pr_review_automation.md
│   └── steering/
│       └── coding_standards.md   # Team coding standards
├── requirements.txt
├── setup.py
├── README.md
└── pyproject.toml
```

## Components and Interfaces

### CLI Interface (cli.py)
- **Technology**: Python Click library
- **Responsibilities**: Command parsing, user interaction, progress display
- **Key Commands**:
  - `kirolinter analyze <path/url>` - Main analysis command
  - `kirolinter config` - Configuration management
  - `kirolinter github setup` - GitHub integration setup

### Core Analysis Engine (engine.py)
- **Responsibilities**: Orchestrates the analysis pipeline, manages performance tracking
- **Key Methods**:
  - `analyze_codebase()` - Main entry point for analysis
  - `process_file()` - Individual file processing
  - `generate_report()` - Consolidates results

### Scanner Module (scanner.py)
- **Technology**: Python AST, pylint, bandit, radon
- **Responsibilities**: Code quality analysis, security scanning, performance detection
- **Detection Categories**:
  - Code smells: unused variables, dead code, complexity metrics
  - Security: SQL injection, hardcoded secrets, unsafe imports
  - Performance: inefficient loops, memory usage patterns

### Suggester Module (suggester.py)
- **Technology**: OpenAI API, local LLM integration
- **Responsibilities**: AI-powered fix generation, context-aware suggestions
- **Key Features**:
  - Pattern-based fix templates
  - Context-aware code generation
  - Integration with team style preferences

### Style Analyzer (style_analyzer.py)
- **Technology**: GitPython, scikit-learn, AST analysis
- **Responsibilities**: Team coding style learning, pattern extraction
- **Analysis Areas**:
  - Naming conventions
  - Code structure patterns
  - Import organization
  - Function/class design patterns

### GitHub Integration (github_client.py)
- **Technology**: PyGithub, GitHub REST API
- **Responsibilities**: PR comment posting, repository access, webhook handling
- **Key Features**:
  - Authenticated API access
  - Rate limiting and retry logic
  - Comment threading and updates

### CVE Database Integration (cve_database.py)
- **Technology**: CVE API, local caching
- **Responsibilities**: Security vulnerability database access
- **Features**:
  - CVE pattern matching
  - Severity scoring
  - Regular database updates

## Data Models

### Issue Model
```python
@dataclass
class Issue:
    id: str
    type: IssueType  # CODE_SMELL, SECURITY, PERFORMANCE
    severity: Severity  # LOW, MEDIUM, HIGH, CRITICAL
    file_path: str
    line_number: int
    column: int
    message: str
    rule_id: str
    cve_id: Optional[str] = None
```

### Suggestion Model
```python
@dataclass
class Suggestion:
    issue_id: str
    fix_type: FixType  # REPLACE, INSERT, DELETE
    original_code: str
    suggested_code: str
    confidence: float
    explanation: str
    diff_patch: Optional[str] = None
```

## Error Handling

### Analysis Errors
- **File Access Errors**: Graceful handling of permission issues, missing files
- **Parsing Errors**: Continue analysis on syntax errors, report parsing failures
- **Memory Constraints**: Implement streaming analysis for large files

### Integration Errors
- **GitHub API**: Rate limiting, authentication failures, network timeouts
- **CVE Database**: Fallback to cached data, graceful degradation
- **Git Operations**: Handle repository access issues, authentication problems

### Performance Constraints
- **Timeout Handling**: 5-minute maximum for large repositories
- **Memory Management**: Streaming processing for files > 1MB
- **Concurrent Processing**: Thread pool for parallel file analysis

## Testing Strategy

### Unit Testing
- **Scanner Tests**: Mock AST parsing, test rule detection
- **Suggester Tests**: Mock AI responses, test fix generation
- **Integration Tests**: Mock external APIs, test error handling

### Integration Testing
- **GitHub Integration**: Test with real repositories (using test accounts)
- **CVE Database**: Test with known vulnerable code samples
- **End-to-End**: Full pipeline testing with sample open-source repositories (Flask, Django, or similar Python projects)

### Performance Testing
- **Large Repository Testing**: Test with 10,000+ line codebases
- **Memory Profiling**: Monitor memory usage during analysis
- **Concurrent Load Testing**: Multiple simultaneous analyses

## Kiro Features Integration

### Spec-Driven Development
- Use Kiro's spec workflow to break down implementation into manageable tasks
- Leverage requirements traceability for feature completeness
- Iterative development with continuous user feedback

### Agent Hooks Implementation

#### On-Commit Analysis Hook
```markdown
# .kiro/hooks/on_commit_analysis.md
Trigger: post-commit (Git event: after 'git commit')
Action: Run KiroLinter analysis on files changed in last commit
Command: kirolinter analyze --changed-only --format=summary
Output: Console summary of new issues introduced
```

#### PR Review Automation Hook
```markdown
# .kiro/hooks/pr_review_automation.md
Trigger: pull_request (GitHub webhook event)
Action: Analyze PR diff and post review comments
Command: kirolinter github review --pr-number=$PR_NUMBER
Output: GitHub PR comments with suggestions
```

### Inline AI Coding
- Use Kiro's AI assistance for complex algorithm implementation
- Leverage AI for test case generation
- AI-assisted documentation and code comments

### Steering Rules
- Define team-specific coding standards in `.kiro/steering/`
- Customize analysis rules based on project requirements
- Maintain consistency across team members

## Recommended Python Libraries

### Core Dependencies
- **click**: CLI interface framework
- **GitPython**: Git repository operations
- **PyGithub**: GitHub API integration
- **requests**: HTTP client for CVE database
- **pyyaml**: Configuration file parsing
- **dataclasses**: Data model definitions

### Analysis Libraries
- **ast**: Python AST parsing
- **pylint**: Code quality analysis
- **bandit**: Security vulnerability scanning
- **radon**: Code complexity metrics
- **vulture**: Dead code detection

### AI/ML Libraries
- **openai**: AI-powered suggestions
- **scikit-learn**: Style pattern analysis
- **numpy**: Numerical computations
- **pandas**: Data analysis for commit history

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Type checking
- **coverage**: Test coverage analysis

## Implementation Phases

### Phase 1: Core Analysis Engine (MVP Focus) ✅ COMPLETED
- Basic CLI interface with Click (defer web interface as stretch goal)
- File system scanning and AST parsing
- Simple rule-based issue detection
- JSON report generation
- Fallback rule-based suggestions if OpenAI API unavailable

### Phase 2: AI Integration & Suggestions ✅ COMPLETED
- OpenAI API integration for suggestions
- Rule-based fix generation templates
- Diff/patch creation functionality
- Team style prioritization

### Phase 3: CI/CD Integration (CURRENT)
- GitHub Actions workflow for automated PR analysis
- Automated code review comments using GitHub API
- Integration with reviewdog for enhanced PR feedback
- Workflow triggers on pull requests to main branch

### Phase 4: GitHub Integration
- GitHub API authentication
- PR comment posting
- Webhook handling for automation

### Phase 5: Style Learning
- Git history analysis
- Team pattern extraction
- Personalized suggestion ranking

### Phase 6: Advanced Features
- CVE database integration
- Performance optimization
- Agent hooks implementation
- Web interface (stretch goal)

## CI/CD Integration Design

### GitHub Actions Workflow

The CI/CD pipeline automatically runs KiroLinter on pull requests to provide immediate feedback to developers.

#### Workflow Triggers
- Pull requests to `main` branch
- Push events to pull request branches
- Manual workflow dispatch for testing

#### Workflow Steps
1. **Checkout Code**: Get the PR branch and base branch
2. **Setup Python**: Install Python 3.8+ and dependencies
3. **Install KiroLinter**: Install the tool in the CI environment
4. **Analyze Changed Files**: Run analysis only on files modified in the PR
5. **Generate Report**: Create JSON report with suggestions and diffs
6. **Post PR Comments**: Use GitHub API to comment on specific lines
7. **Set Status Check**: Pass/fail based on critical issues found

#### Integration Options

**Option 1: Direct GitHub API Integration**
- Use GitHub API to post review comments
- Comment on specific lines where issues are found
- Provide summary comment with overall analysis results

**Option 2: Reviewdog Integration**
- Use reviewdog for enhanced PR feedback
- Better formatting and filtering of comments
- Integration with existing review tools

**Option 3: Hybrid Approach**
- Use reviewdog for line comments
- Use GitHub API for summary comments
- Provide both detailed and overview feedback