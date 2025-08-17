# Getting Started with KiroLinter 🚀

Welcome to KiroLinter, the world's first **autonomous AI agentic code review system**! This guide will help you set up and start using KiroLinter's powerful multi-agent architecture to transform your code quality management.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Setup](#quick-setup)
- [Your First Analysis](#your-first-analysis)
- [Enabling Agentic Features](#enabling-agentic-features)
- [Background Monitoring](#background-monitoring)
- [Understanding Results](#understanding-results)
- [Next Steps](#next-steps)

## Prerequisites

### System Requirements

```bash
# Operating System
- Linux (Ubuntu 18.04+, CentOS 7+)
- macOS (10.14+)
- Windows 10+ (with WSL recommended)

# Python Version
python --version  # Must be 3.8 or higher

# Memory & Storage
- RAM: 4GB minimum, 8GB recommended
- Storage: 1GB free space
- Network: Internet connection for AI features
```

### Required Dependencies

```bash
# 1. Redis Server (for pattern storage and agent coordination)
# Ubuntu/Debian:
sudo apt update && sudo apt install redis-server

# macOS:
brew install redis

# Windows (via WSL):
sudo apt install redis-server

# Verify Redis is running:
redis-cli ping  # Should return "PONG"
```

### Optional AI Provider Setup

KiroLinter supports multiple AI providers for enhanced analysis:

```bash
# Option 1: OpenAI (Recommended)
export OPENAI_API_KEY="sk-your-openai-api-key-here"

# Option 2: XAI Grok (Alternative)
export XAI_API_KEY="xai-your-grok-api-key-here"

# Option 3: Local Models (Advanced)
# No API key needed, uses local inference
```

## Installation

### Method 1: Clone and Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/kirolinter.git
cd kirolinter

# Install with all agentic features
pip install -e ".[ai]"

# Verify installation
kirolinter --version
```

### Method 2: Quick Install (Basic Features)

```bash
# Install without AI features (basic linting only)
pip install kirolinter

# Upgrade to include AI features later
pip install "kirolinter[ai]"
```

### Method 3: Development Setup

```bash
# For contributing or advanced usage
git clone https://github.com/yourusername/kirolinter.git
cd kirolinter

# Install with development dependencies
pip install -e ".[dev,ai]"

# Install pre-commit hooks
pre-commit install
```

## Quick Setup

### 1. Start Redis Server

```bash
# Start Redis in background
redis-server --daemonize yes

# Or start Redis in foreground (for debugging)
redis-server

# Verify Redis is accessible
redis-cli ping  # Should return "PONG"
```

### 2. Configure Environment

Create a `.env` file in your project root:

```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# AI Provider (choose one)
OPENAI_API_KEY=your-openai-key-here
# OR
XAI_API_KEY=your-grok-key-here

# Optional: Logging level
LOG_LEVEL=INFO
```

### 3. Initialize KiroLinter

```bash
# Initialize in your project directory
cd /path/to/your/project
kirolinter init

# This creates:
# - .kirolinter.yaml (configuration file)
# - .kirolinter/ (working directory)
# - Pattern memory database connection
```

## Your First Analysis

### Basic Analysis

```bash
# Analyze current directory
kirolinter analyze .

# Analyze specific file
kirolinter analyze src/main.py

# Get detailed JSON output
kirolinter analyze . --format=json --output=report.json
```

### Understanding the Output

```bash
📊 KiroLinter Analysis Summary
Files analyzed: 15
Issues found: 8
Analysis time: 1.23 seconds

🔴 CRITICAL SEVERITY (1):
  src/auth.py:23 - Unsafe use of eval() function

🟠 HIGH SEVERITY (2):
  src/config.py:15 - Hardcoded API key detected
  src/database.py:67 - Potential SQL injection vulnerability

🟡 MEDIUM SEVERITY (3):
  src/utils.py:34 - Function has high cyclomatic complexity (15)
  src/models.py:89 - Inefficient loop concatenation detected
  src/helpers.py:45 - Long parameter list (8 parameters)

🟢 LOW SEVERITY (2):
  src/helpers.py:12 - Unused import 'sys'
  src/main.py:45 - Unused variable 'temp_data'

💡 AI Suggestions: 6 fixes available
🎯 Team Patterns: Learning from 0 commits (run 'kirolinter agent learn' to start)
```

## Enabling Agentic Features

### 1. Initialize Pattern Memory

```bash
# Learn from your project's commit history
kirolinter agent learn --repo=. --commits=100

# The system will:
# - Analyze your Git history
# - Extract coding patterns
# - Adapt to your team's style
# - Store patterns securely in Redis
```

Expected output:
```bash
🧠 Learning from commit history...
📊 Analyzed 100 commits across 12 contributors
🎯 Extracted 45 coding patterns
✅ Stored 45 patterns in memory (anonymized)

Key patterns learned:
- Variable naming: snake_case preferred (87%)
- Import organization: stdlib first, then third-party
- Function complexity: avg 8.2 lines, max 25 lines
- Documentation: 78% of functions have docstrings
```

### 2. Run Autonomous Workflow

```bash
# Start full autonomous workflow
kirolinter agent workflow --repo=. --auto-apply --create-pr

# The workflow includes:
# 1. Pattern-aware analysis
# 2. Safe fix application
# 3. GitHub PR creation
# 4. Continuous learning
```

Expected workflow:
```bash
🚀 Starting autonomous workflow for /your/project
🔍 1/5 Analyzing code with team patterns...
   📊 Found 12 issues (3 high, 5 medium, 4 low priority)
🔧 2/5 Applying safe fixes...
   ✅ Applied 8 fixes safely (4 skipped due to low confidence)
🔗 3/5 Creating GitHub pull request...
   📝 PR #42 created: "AI Code Quality Improvements"
🧠 4/5 Learning from applied fixes...
   📈 Updated confidence scores based on successful fixes
🎯 5/5 Updating team patterns...
   ✨ Learned 3 new patterns from this workflow

✅ Workflow completed successfully!
📊 Summary: 8 fixes applied, 1 PR created, 3 patterns learned
```

### 3. Enable Background Monitoring

```bash
# Start background daemon (monitors for changes)
kirolinter daemon start --interval=3600  # Run every hour

# Check daemon status
kirolinter daemon status

# View daemon logs
kirolinter daemon logs

# Stop daemon
kirolinter daemon stop
```

## Background Monitoring

KiroLinter can automatically monitor your repository and apply fixes in the background.

### Setup Automated Workflows

```bash
# Configure automatic analysis on every commit
kirolinter hooks install

# This sets up:
# - Pre-commit analysis (catches issues before commit)
# - Post-commit learning (learns from your changes)
# - Scheduled reviews (daily/weekly deep analysis)
```

### Monitor Workflow Activity

```bash
# View recent workflow executions
kirolinter agent history

# See pattern learning progress
kirolinter agent patterns --repo=.

# Check agent health and performance
kirolinter agent status
```

Example monitoring output:
```bash
📊 KiroLinter Monitoring Dashboard

🤖 Agents Status:
├─ Coordinator: ✅ Active, 12 workflows completed
├─ Reviewer: ✅ Active, analyzing 34 files/hour
├─ Fixer: ✅ Active, 98.5% fix success rate
├─ Integrator: ✅ Active, 5 PRs created this week
└─ Learner: ✅ Active, 127 patterns learned

📈 Performance Metrics:
├─ Average analysis time: 1.2s per file
├─ Memory usage: 245MB
├─ Pattern retrieval: 0.8ms average
└─ Redis operations: 1,247/second peak

🎯 Learning Progress:
├─ Coding patterns: 127 learned, 98% accuracy
├─ Team preferences: 89% match rate
├─ Fix confidence: Improving +2.3% weekly
└─ Cross-repo insights: 15 projects contributing
```

## Understanding Results

### Analysis Report Structure

KiroLinter provides multiple output formats:

#### 1. Summary Format (Default)
```bash
kirolinter analyze . --format=summary
# Quick overview with issue counts and top priorities
```

#### 2. Detailed Format
```bash
kirolinter analyze . --format=detailed
# Full issue descriptions with context and suggestions
```

#### 3. JSON Format
```bash
kirolinter analyze . --format=json
# Machine-readable format for CI/CD integration
```

### Issue Severity Levels

| Severity | Description | Examples | Action Required |
|----------|-------------|----------|-----------------|
| **Critical** | Security vulnerabilities, unsafe code | `eval()`, SQL injection | Immediate fix |
| **High** | Serious bugs, performance issues | Memory leaks, hardcoded secrets | Fix ASAP |
| **Medium** | Code quality, maintainability | Complex functions, code smells | Plan fix |
| **Low** | Style, minor improvements | Unused imports, formatting | Optional fix |

### AI Suggestions Explained

```json
{
  "suggested_fix": {
    "fix_type": "replace",
    "suggested_code": "os.environ.get('API_KEY', 'default')",
    "confidence": 0.95,
    "explanation": "Store API keys in environment variables for security",
    "diff_patch": "--- before\n+++ after\n@@ -1 +1 @@\n-API_KEY = 'hardcoded-key'\n+API_KEY = os.environ.get('API_KEY', 'default')"
  }
}
```

### Pattern Learning Insights

View what KiroLinter has learned about your team:

```bash
# Show learned patterns
kirolinter agent patterns --repo=. --verbose

# Example output:
Pattern: variable_naming
├─ snake_case: 87% (preferred)
├─ camelCase: 13%
└─ Confidence: 0.94

Pattern: import_organization
├─ stdlib_first: 92%
├─ alphabetical: 78%
└─ Confidence: 0.89

Pattern: function_complexity
├─ avg_lines: 8.2
├─ max_lines: 25
├─ avg_parameters: 3.1
└─ Confidence: 0.91
```

## Next Steps

### 1. Customize Configuration

Create a `.kirolinter.yaml` file to customize behavior:

```yaml
# Basic settings
enabled_rules:
  - unused_variable
  - hardcoded_secret
  - sql_injection
  - unsafe_eval

severity_threshold: medium
max_complexity: 10

# Agentic features
agents:
  enable_learning: true
  auto_apply_fixes: true
  confidence_threshold: 0.85
  
  # Workflow templates
  workflows:
    daily_review:
      - analyze
      - learn
      - notify
    
    commit_check:
      - analyze
      - fix_high_confidence

# Integration settings
github:
  create_prs: true
  assign_reviewers: true
  add_labels: ["code-quality", "automated"]

redis:
  host: localhost
  port: 6379
  db: 0
```

### 2. Explore Advanced Features

```bash
# Cross-repository learning
kirolinter agent learn --repo=../other-project --share-patterns

# Custom workflow execution
kirolinter agent workflow --template=security_focus --repo=.

# Integration testing
kirolinter agent test --dry-run

# Performance monitoring
kirolinter agent benchmark --files=1000
```

### 3. Set Up Team Collaboration

```bash
# Share patterns with team (privacy-preserved)
kirolinter agent share --repo=. --team=your-team

# Import team patterns
kirolinter agent import --from=team-patterns.json

# Sync with team Redis instance
kirolinter config set redis.host team-redis.company.com
```

### 4. Production Deployment

```bash
# Health checks for production
kirolinter agent health

# Monitoring setup
kirolinter daemon start --production --log-level=INFO

# Backup pattern database
kirolinter admin backup --output=patterns-backup.json
```

## Common Use Cases

### For Individual Developers

```bash
# Daily workflow
kirolinter agent workflow --repo=. --auto-apply
git add -A && git commit -m "AI-assisted code improvements"

# Pre-commit checks
kirolinter analyze . --severity=medium --format=summary
```

### For Team Leads

```bash
# Team pattern analysis
kirolinter agent patterns --repo=. --team-insights

# Code quality metrics
kirolinter agent metrics --repo=. --period=30days

# Onboarding new developers
kirolinter agent teach --repo=. --output=team-guide.md
```

### For DevOps Engineers

```bash
# CI/CD integration
kirolinter analyze . --format=json --output=quality-report.json

# Automated PR reviews
kirolinter github setup --webhook-url=https://your-ci.com/kirolinter

# Monitoring and alerting
kirolinter daemon start --alert-webhook=https://slack.com/webhook
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check if Redis is running
   redis-cli ping
   
   # Start Redis if needed
   redis-server --daemonize yes
   ```

2. **No AI Features Available**
   ```bash
   # Install AI dependencies
   pip install "kirolinter[ai]"
   
   # Set API key
   export OPENAI_API_KEY="your-key"
   ```

3. **Permission Errors**
   ```bash
   # Fix file permissions
   chmod +x ~/.local/bin/kirolinter
   
   # Or install with user flag
   pip install --user kirolinter
   ```

### Getting Help

- **Documentation**: [docs/troubleshooting.md](troubleshooting.md)
- **Best Practices**: [docs/best_practices.md](best_practices.md)
- **Advanced Config**: [docs/advanced_config.md](advanced_config.md)
- **GitHub Issues**: Report bugs and request features
- **Community**: Join our Discord for real-time help

## Summary

Congratulations! 🎉 You've successfully set up KiroLinter's agentic system. Here's what you can do now:

✅ **Autonomous Code Review** - Let AI agents analyze and fix your code  
✅ **Continuous Learning** - System adapts to your team's coding style  
✅ **Background Monitoring** - 24/7 code quality management  
✅ **Team Collaboration** - Share patterns while preserving privacy  
✅ **Enterprise Integration** - Production-ready deployment options  

Your journey into autonomous code quality management starts now! 🚀

---

**Next**: Check out [Advanced Configuration](advanced_config.md) to customize KiroLinter for your specific needs.