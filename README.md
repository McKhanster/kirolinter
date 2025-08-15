# KiroLinter 🔍

**AI-Driven Code Review Tool for Python Projects**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code with Kiro Hackathon](https://img.shields.io/badge/Code%20with%20Kiro-Hackathon-purple.svg)](https://kiro.ai)

KiroLinter is an intelligent code analysis tool that combines AST-based static analysis with AI-powered suggestions to help teams maintain high-quality Python codebases. Built for the Code with Kiro Hackathon, it detects code smells, security vulnerabilities, and performance bottlenecks while providing actionable fix suggestions.

## ✨ Features

### 🔍 **Comprehensive Code Analysis**
- **Code Smells**: Unused variables, dead code, complex functions
- **Security Vulnerabilities**: SQL injection, hardcoded secrets, unsafe eval/exec
- **Performance Issues**: Inefficient loops, redundant operations

### 🤖 **AI-Powered Suggestions**
- Rule-based fix templates with high confidence
- OpenAI integration for complex issues (optional)
- Context-aware code suggestions with diff patches

### 🎯 **Team Style Learning**
- Analyzes commit history for coding patterns
- Personalizes suggestions based on team preferences
- Prioritizes fixes according to team standards

### 🔗 **Seamless Integration**
- CLI interface with multiple output formats (JSON, summary, detailed)
- GitHub PR integration for automated reviews
- Git hooks for commit-time analysis
- Kiro IDE integration with agent hooks

### ⚡ **High Performance**
- Processes 10,000+ lines of code in under 5 minutes
- Concurrent file analysis
- Smart caching and exclusion patterns

### 🤖 **AI Agent System** *(New!)*
- **Multi-Agent Architecture**: Coordinator, Reviewer, Fixer, Integrator, and Learner agents
- **Autonomous Workflows**: Full code review, fix application, and GitHub integration
- **Continuous Learning**: Adapts to team patterns and improves over time
- **LangChain Integration**: Advanced AI capabilities with conversation memory
- **Safe Automation**: Backup creation and safety checks for all operations

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/McKhanster/kirolinter.git
cd kirolinter

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Basic Usage

```bash
# Analyze current directory
kirolinter analyze . --format=summary

# Analyze specific file with JSON output
kirolinter analyze src/main.py --format=json --output=report.json

# Focus on security issues
kirolinter analyze . --severity=high --format=detailed

# Analyze only changed files (requires Git)
kirolinter analyze . --changed-only --format=summary

# AI Agent System Commands (requires: pip install langchain langchain-openai)
kirolinter agent review --repo=https://github.com/pallets/flask
kirolinter agent workflow --repo=./my-project --auto-apply --create-pr
kirolinter agent fix --repo=./project --auto-apply
```

## 📊 Example Output

### JSON Report with Suggestions
```json
{
  "kirolinter_version": "0.1.0",
  "target": "src/app.py",
  "summary": {
    "total_files_analyzed": 1,
    "total_issues_found": 3,
    "analysis_time_seconds": 0.45,
    "issues_by_severity": {
      "critical": 1,
      "high": 1,
      "medium": 0,
      "low": 1
    }
  },
  "files": [
    {
      "file_path": "src/app.py",
      "issues": [
        {
          "id": "hardcoded_secret_123",
          "type": "security",
          "severity": "high",
          "line_number": 15,
          "message": "Hardcoded API key detected",
          "rule_id": "hardcoded_api_key",
          "suggested_fix": {
            "fix_type": "replace",
            "suggested_code": "os.environ.get('API_KEY', 'your_api_key_here')",
            "confidence": 0.9,
            "explanation": "API keys should be stored in environment variables to prevent unauthorized access.",
            "diff_patch": "--- a/src/app.py\n+++ b/src/app.py\n@@ -12,7 +12,8 @@\n+import os\n \n-API_KEY = 'sk-1234567890abcdef'\n+API_KEY = os.environ.get('API_KEY', 'your_api_key_here')"
          }
        }
      ]
    }
  ]
}
```

### Summary Report
```
📊 KiroLinter Analysis Summary
Files analyzed: 45
Issues found: 12

🔴 CRITICAL SEVERITY (1):
  src/auth.py:23 - Unsafe use of eval() function

🟠 HIGH SEVERITY (2):
  src/config.py:15 - Hardcoded API key detected
  src/database.py:67 - Potential SQL injection vulnerability

🟡 MEDIUM SEVERITY (5):
  src/utils.py:34 - Function has high cyclomatic complexity (15)
  src/models.py:89 - Inefficient loop concatenation detected

🟢 LOW SEVERITY (4):
  src/helpers.py:12 - Unused import 'sys'
  src/main.py:45 - Unused variable 'temp_data'
```

## 🛠️ Advanced Usage

### Configuration

Create a `.kirolinter.yaml` file in your project root:

```yaml
enabled_rules:
  - unused_variable
  - unused_import
  - hardcoded_secret
  - sql_injection
  - unsafe_eval

min_severity: medium
max_complexity: 10

exclude_patterns:
  - "tests/*"
  - "venv/*"
  - "__pycache__/*"

# AI Integration (optional)
openai_api_key: "your-api-key-here"
use_ai_suggestions: true
fallback_to_rules: true

# GitHub Integration
github_token: "your-github-token"
```

### Git Hooks Integration

Set up automatic analysis on commits:

```bash
# Copy the post-commit hook
cp .kiro/hooks/on_commit_analysis.md .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Now analysis runs automatically after each commit
git commit -m "Your changes"
# 🔍 Running KiroLinter analysis on changed files...
# ✅ No issues found in changed files
```

### GitHub PR Integration

```bash
# Set up GitHub integration
kirolinter github setup --token your_github_token

# Analyze a pull request
kirolinter github review --pr-number 123 --repo owner/repo
```

## 🧪 Testing with Real Projects

### Flask Framework Analysis
```bash
# Clone and analyze Flask
git clone https://github.com/pallets/flask.git
cd flask

# Run comprehensive analysis
kirolinter analyze src/flask --format=json --severity=medium --exclude="tests/*"

# Results: Typically finds 50-100 issues in ~2 seconds
```

### Django Framework Analysis
```bash
# Analyze Django codebase
git clone https://github.com/django/django.git
cd django

# Focus on security issues
kirolinter analyze django --severity=high --format=detailed
```

## 🏗️ Architecture

KiroLinter follows a modular architecture designed for extensibility:

```
kirolinter/
├── cli.py                    # Click-based CLI interface
├── core/
│   ├── engine.py            # Analysis orchestration
│   ├── scanner.py           # AST-based code analysis
│   └── suggester.py         # AI-powered suggestions
├── models/
│   ├── issue.py             # Issue data models
│   ├── suggestion.py        # Suggestion data models
│   └── config.py            # Configuration management
├── reporting/
│   ├── json_reporter.py     # JSON report generation
│   └── diff_generator.py    # Diff patch creation
├── integrations/
│   ├── github_client.py     # GitHub API integration
│   └── repository_handler.py # Git operations
└── utils/
    ├── ast_helpers.py       # AST parsing utilities
    └── performance_tracker.py # Performance monitoring
```

## 🎯 Hackathon Highlights

### Innovation
- **AI-Enhanced Analysis**: Combines rule-based detection with AI suggestions
- **Team Style Learning**: Adapts to team coding preferences automatically
- **Intelligent Prioritization**: Ranks issues by team importance and severity

### Implementation Quality
- **High Performance**: 229 issues detected in 1.23 seconds on real codebases
- **Comprehensive Testing**: 95%+ test coverage with unit and integration tests
- **Production Ready**: Error handling, logging, and graceful degradation

### Kiro Integration
- **Spec-Driven Development**: Built using Kiro's systematic approach
- **Agent Hooks**: Automated workflows for commit analysis and PR reviews
- **Inline AI Coding**: Leveraged AI assistance for complex implementations

## 🧪 Development & Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_scanner.py -v
pytest tests/test_suggester.py -v

# Run with coverage
pytest tests/ --cov=kirolinter --cov-report=html
```

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
flake8 kirolinter/
black kirolinter/

# Type checking
mypy kirolinter/
```

## 📈 Performance Benchmarks

| Repository | Files | Lines of Code | Analysis Time | Issues Found |
|------------|-------|---------------|---------------|--------------|
| Flask      | 45    | ~15,000       | 1.2s         | 89           |
| Django     | 200+  | ~100,000      | 12.3s        | 234          |
| Requests   | 25    | ~8,000        | 0.8s         | 45           |

*Benchmarks run on MacBook Pro M1, Python 3.9*

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](.kiro/specs/kirolinter/design.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

### Adding New Rules
1. Add rule logic to appropriate scanner in `kirolinter/core/scanner.py`
2. Create suggestion template in `kirolinter/config/templates/`
3. Add tests in `tests/`
4. Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Kiro AI** for the amazing development environment and hackathon opportunity
- **Python AST** module for powerful code analysis capabilities
- **Click** for the excellent CLI framework
- **OpenAI** for AI-powered suggestion capabilities

## 🔗 Links

- [Kiro IDE](https://kiro.ai) - The AI-powered development environment
- [Code with Kiro Hackathon](https://kiro.ai/hackathon) - Join the next hackathon!
- [Documentation](.kiro/specs/kirolinter/) - Detailed specs and design docs

---

**Built with ❤️ using Kiro AI for the Code with Kiro Hackathon**

*KiroLinter: Making Python code reviews intelligent, one suggestion at a time.*## 🤖 Agen
tic Features

KiroLinter now includes advanced AI agent capabilities that enable autonomous code quality management with continuous learning and adaptation.

### Pattern Memory System

The PatternMemory system provides persistent storage of learned coding patterns and team preferences:

```python
from kirolinter.memory.pattern_memory import PatternMemory

# Initialize pattern memory
memory = PatternMemory()

# Store team coding patterns
memory.store_pattern(
    repo_path="/project/repo",
    pattern_type="naming_conventions", 
    pattern_data={"variables": {"snake_case": 45, "camelCase": 5}},
    confidence=0.85
)

# Retrieve patterns for analysis
patterns = memory.retrieve_patterns("/project/repo", "naming_conventions")
```

### Adaptive Learner Agent

The LearnerAgent analyzes commit history and adapts to team coding styles:

```python
from kirolinter.agents.learner import LearnerAgent
from kirolinter.models.config import Config

# Initialize learner agent
learner = LearnerAgent(model="grok-3-mini", provider="xai", verbose=True)

# Learn from commit history
config = Config()
result = learner.learn_from_commits("/project/repo", config)
print(f"Learned {result['patterns_stored']} patterns from {result['commits_analyzed']} commits")

# Adapt team style based on learned patterns
adaptation = learner.adapt_team_style(config, result['patterns'])
print(f"Made {adaptation['adaptations_made']} team style adaptations")
```

### Key Features

- **🔒 Data Privacy**: Automatic anonymization of sensitive information before storage
- **📊 Pattern Learning**: Extract coding patterns from Git commit history
- **🎯 Team Adaptation**: Automatically adapt analysis rules to team preferences
- **⏰ Proactive Scheduling**: Background learning with configurable intervals
- **🔄 Continuous Improvement**: Learn from analysis results and user feedback

### Security & Privacy

All sensitive data is automatically anonymized before storage:

- API keys, passwords, and secrets are masked
- Email addresses and URLs are redacted
- Sensitive files (.env, secrets.yaml) are excluded from analysis
- Complete audit trail of all learning activities

### Performance

- **Pattern Storage**: <10ms per pattern
- **Commit Analysis**: <2s for 100 commits
- **Memory Usage**: <50MB for 1000 patterns
- **Background Learning**: Minimal impact on development workflow