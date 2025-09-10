# KiroLinter Quickstart Guide ⚡

**Get up and running with KiroLinter's AI-powered code analysis in 5 minutes!**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Tests-190%2B%20passing-brightgreen.svg)](tests/)
[![Performance](https://img.shields.io/badge/Performance-10k%20files%20in%2010s-blue.svg)](docs/performance.md)

---

## 🚀 What is KiroLinter?

KiroLinter is an **AI-powered code analysis tool** that provides intelligent insights and recommendations. It offers both traditional static analysis and AI-enhanced workflows:

- 🔍 **Static analysis** with traditional rule-based scanning
- 🤖 **AI-powered insights** using LLM analysis for code quality assessment
- 📊 **Detailed recommendations** with priority ranking and actionable steps
- 🔧 **Smart suggestions** for code improvements and security fixes
- 📋 **Executive summaries** and comprehensive reports
- 🛡️ **Security vulnerability analysis** with specific remediation guidance

## ⏱️ 5-Minute Setup

### Step 1: Install Dependencies (30 seconds)

```bash
# Check Python version (3.8+ required)
python --version

# Install Redis (required for pattern memory)
# Ubuntu/Debian:
sudo apt install redis-server
# macOS:
brew install redis
# Windows: Download from https://redis.io/downloads
# Docker (cross-platform):
# docker run -d --name redis-kirolinter -p 6379:6379 redis:alpine

# Start Redis
redis-server --daemonize yes
# OR with Docker:
# docker start redis-kirolinter
```

### Step 2: Install KiroLinter (1 minute)

```bash
# Clone the repository
git clone https://github.com/yourusername/kirolinter.git
cd kirolinter

# Method 1: Install with pip (recommended)
# Option A: Install with all features
pip install -e ".[ai,devops]"

# Option B: Install basic version only
# pip install -e .

# Method 2: Install from requirements.txt (alternative)
# pip install -r requirements.txt
# pip install -e .

# Verify installation
python -m kirolinter --version
# OR
kirolinter --version
```

### Step 3: AI Setup (Optional but Recommended) (1 minute)

For AI-powered features (agent system, intelligent fixes), set your API key:

```bash
# OpenAI (recommended)
export OPENAI_API_KEY="your-key-here"

# OR Grok (XAI)
export XAI_API_KEY="your-key-here"
```

### Step 4: First Analysis (30 seconds)

```bash
# Traditional rule-based analysis (fast, no AI)
kirolinter analyze . --format=summary

# OR analyze a specific file
kirolinter analyze path/to/your/file.py --format=detailed
```

### Step 5: Run AI-Powered Analysis (1 minute)

```bash
# Ensure Redis is running (required for AI features)
redis-server --daemonize yes
# OR with Docker: docker start redis-kirolinter

# Run AI-powered analysis with detailed insights
kirolinter agent workflow --repo=. --verbose

# For automated fixes (user approval required)
kirolinter agent workflow --repo=. --auto-apply
```

🎉 **You're done!** KiroLinter can now provide AI-powered code analysis and recommendations.

---

## 📋 Common Use Cases

### 1. Basic Code Analysis
```bash
# Analyze current project
kirolinter analyze . --format=summary

# Analyze with specific severity
kirolinter analyze . --severity=high --format=detailed

# Analyze only changed files
kirolinter analyze . --changed-only --format=json
```

### 2. GitHub Integration
```bash
# Set up GitHub integration
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPO="owner/repository"

# Analyze and comment on PR
kirolinter analyze . --github-pr=123 --format=summary

# AI-enhanced GitHub workflow
kirolinter agent workflow --repo=. --create-pr --auto-apply
```

### 3. AI-Powered Workflows

**⚠️ Redis Required**: AI workflows require Redis for pattern memory and analysis coordination.

```bash
# Ensure Redis is running (required for AI features)
# Option 1: Local Redis
redis-server --daemonize yes

# Option 2: Docker Redis (if you prefer Docker)
docker run -d --name redis-kirolinter -p 6379:6379 redis:alpine

# Analyze patterns from your team's code history
kirolinter agent learn --repo=. --commits=100

# Run AI-powered analysis workflow
kirolinter agent workflow --repo=. --auto-apply --verbose

# Enable scheduled monitoring
kirolinter daemon start --interval=3600  # Every hour
```

### 4. DevOps Integration

```bash
# Note: DevOps dependencies should already be installed from Step 2
# If not, install them:
# pip install -e ".[devops]"

# Initialize DevOps infrastructure
kirolinter devops init

# Check system health
kirolinter devops health --check-all

# Start GitOps monitoring
kirolinter devops git-monitor start --repo=. --events=all

# Launch monitoring dashboard
kirolinter devops dashboard --host=0.0.0.0 --port=8000
# Visit: http://localhost:8000/dashboard

# Set up GitHub integration (optional)
export GITHUB_TOKEN="your-github-token"
export GITLAB_TOKEN="your-gitlab-token"
```

### 5. Interactive Fixes

```bash
# Show what fixes would be applied
kirolinter analyze . --dry-run --interactive-fixes

# Apply fixes interactively
kirolinter analyze . --interactive-fixes

# AI-powered fixes with confidence scoring
kirolinter agent workflow --repo=. --auto-apply
```

---

## 🤖 Understanding the AI Analysis System

KiroLinter uses AI-powered analysis to provide intelligent code insights and recommendations:

### Agent Architecture
```
┌─────────────────────────────────────────────┐
│              COORDINATOR AGENT              │
│         (Orchestrates all workflows)        │
├─────────────────────────────────────────────┤
│  REVIEWER  │  FIXER   │ INTEGRATOR │ LEARNER │
│   Agent    │  Agent   │   Agent    │  Agent  │
│   ────     │   ────   │    ────    │   ────  │
│  Analyzes  │ Applies  │  Manages   │ Learns  │
│   Code     │  Fixes   │  GitHub    │ Patterns│
├─────────────────────────────────────────────┤
│         CROSS-REPO LEARNER AGENT            │
│      (Shares knowledge across repos)        │
└─────────────────────────────────────────────┘
```

### Agent Commands
```bash
# Check agent status
kirolinter agent status

# Run specific agents
kirolinter agent review --repo=. --verbose
kirolinter agent fix --repo=. --dry-run
kirolinter agent integrate --repo=. --pr-number=123
kirolinter agent learn --repo=. --commits=50

# Full coordinated workflow
kirolinter agent workflow --repo=. --template=full_review
```

---

## 🔧 DevOps Integration

### GitOps Monitoring Setup

```bash
# Start real-time Git monitoring
kirolinter devops git-monitor start --repo=. --events=all

# Set up webhooks for GitHub/GitLab
kirolinter devops webhook setup --platform=github --secret=your-secret
```

### CI/CD Platform Integration

#### GitHub Actions
```python
from kirolinter.devops.integrations.cicd.github_actions import GitHubActionsConnector

github = GitHubActionsConnector(
    github_token="your-github-token",
    webhook_secret="your-webhook-secret"
)

# Discover and trigger workflows
workflows = await github.discover_workflows("owner/repo")
result = await github.trigger_workflow(
    repository="owner/repo",
    workflow_id="12345",
    branch="main"
)
```

#### GitLab CI
```python
from kirolinter.devops.integrations.cicd.gitlab_ci import GitLabCIConnector

gitlab = GitLabCIConnector(
    gitlab_token="your-gitlab-token",
    gitlab_url="https://gitlab.com"
)

# Manage pipelines and quality gates
async with gitlab as connector:
    pipelines = await connector.discover_workflows("group/project")
    result = await connector.trigger_workflow("group/project", "456", "main")
```

### Dashboard & API

```bash
# Start monitoring dashboard
kirolinter devops dashboard --host=0.0.0.0 --port=8000

# API endpoints available at:
# - http://localhost:8000/api/health
# - http://localhost:8000/api/metrics
# - http://localhost:8000/api/workflows
```

---

## 📊 Performance & Configuration

### Performance Benchmarks
- **Analysis Speed**: 10,000 files in 10 seconds
- **Memory Usage**: < 500MB for massive repositories
- **Concurrent Workflows**: 5+ simultaneous executions
- **Fix Accuracy**: 98.5% safe fixes

### Configuration Examples

#### Custom Config File (`.kirolinter.yaml`)
```yaml
# Analysis settings
analysis:
  min_severity: "medium"
  exclude_patterns:
    - "tests/*"
    - "*.pyc"
    - "__pycache__/*"

# AI settings
ai:
  provider: "openai"  # or "grok"
  model: "gpt-4"
  confidence_threshold: 0.85

# GitHub integration
github:
  token: "${GITHUB_TOKEN}"
  repository: "owner/repo"
  auto_create_prs: true

# DevOps settings
devops:
  redis_url: "redis://localhost:6379"
  webhook_port: 8080
  dashboard_port: 8000
```

#### Environment Variables
```bash
# Core settings
export KIROLINTER_CONFIG="/path/to/config.yaml"
export REDIS_URL="redis://localhost:6379"

# AI providers
export OPENAI_API_KEY="your-openai-key"
export XAI_API_KEY="your-grok-key"

# GitHub integration
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPO="owner/repository"

# GitLab integration
export GITLAB_TOKEN="your-gitlab-token"
export GITLAB_URL="https://gitlab.com"
```

---

## 🔍 Example Outputs

### Analysis Summary
```bash
$ kirolinter analyze . --format=summary

🔍 KiroLinter Analysis Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary:
   Files analyzed: 45
   Issues found: 12
   Critical: 2
   High: 3
   Medium: 7
   Low: 0

🚨 Critical Issues:
   • SQL injection vulnerability (auth.py:127)
   • Hardcoded API key (config.py:45)

⚡ Performance: Analyzed in 1.2s
🤖 AI-powered suggestions: 8/12 issues have auto-fixes available
```

### AI-Powered Workflow Output
```bash
$ kirolinter agent workflow --repo=. --auto-apply --verbose

🤖 Starting AI Analysis Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[AI Analysis] Analyzing code patterns... ✅
[AI Review] Generating insights and recommendations... ✅
[Smart Fixes] Identifying safe improvements... ✅
[Report] Creating comprehensive summary... ✅

📈 Results:
   • Issues found: 12
   • Auto-fixes applied: 8
   • Manual review needed: 4
   • PR created: https://github.com/owner/repo/pull/123
   • Learning patterns: 23 new patterns discovered

🎯 Next analysis scheduled: 2025-01-15 14:30:00
```

---

## 🛡️ Safety & Security

### Safe Fixes Only
- **98.5% accuracy** rate for auto-applied fixes
- **Automatic backups** before any changes
- **Syntax validation** for all fixes
- **Rollback capability** for failed fixes

### Privacy Protection
- **Automatic anonymization** of sensitive data
- **Local pattern storage** with Redis encryption
- **No data leaves your environment** without consent
- **Audit trails** for all agent actions

### Enterprise Features
- **Role-based access control**
- **Comprehensive audit logging**  
- **Compliance reporting**
- **Custom security policies**

---

## 🚨 Troubleshooting

### Common Issues

**Installation Warnings about Missing Extras:**
```bash
# If you see: WARNING: kirolinter 0.1.0 does not provide the extra 'ai'
# This means you need to reinstall with the updated configuration:

# Uninstall first
pip uninstall kirolinter -y

# Reinstall with extras  
pip install -e ".[ai,devops]"

# Or install just what you need:
pip install -e ".[ai]"  # For AI features only
pip install -e "."     # For basic functionality only
```

**Redis Connection Issues:**
```bash
# Check if Redis is running
redis-cli ping  # Should return PONG

# Start Redis if not running
redis-server --daemonize yes
```

**GitHub API Rate Limits:**
```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# The system automatically handles rate limits with exponential backoff
```

**Performance Issues:**
```bash
# Check system resources
kirolinter debug performance

# Clear Redis cache if needed
redis-cli FLUSHALL
```

**AI Provider Issues:**
```bash
# Verify API key is set
echo $OPENAI_API_KEY  # or $XAI_API_KEY

# Test AI connectivity
kirolinter debug ai-connection
```

### Getting Help

```bash
# Detailed help for any command
kirolinter --help
kirolinter analyze --help
kirolinter agent --help
kirolinter devops --help

# Debug information
kirolinter debug system-info
kirolinter debug agent-status
```

---

## 🛠️ Development & Building

### Building GitHub Actions

If you're contributing to the GitHub Actions or they need rebuilding:

```bash
# Navigate to the action directory
cd .github/actions/kirolinter-devops

# Install dependencies
npm install

# Build the action
npm run build
```

This creates the `dist/index.js` file required for the GitHub Action to run.

---

## 📚 What's Next?

### Immediate Next Steps
1. **Run your first analysis**: `kirolinter analyze . --format=summary`
2. **Learn your patterns**: `kirolinter agent learn --repo=. --commits=50`
3. **Try autonomous mode**: `kirolinter agent workflow --repo=. --auto-apply`
4. **Set up GitHub integration**: Add your GitHub token and try PR automation

### Advanced Features to Explore
- **DevOps Integration**: Set up GitOps monitoring and CI/CD orchestration
- **Custom Rules**: Create team-specific analysis rules
- **Cross-Repository Learning**: Share patterns across projects
- **Enterprise Deployment**: Scale to organization-wide usage

### Resources
- **[Full Documentation](README.md)** - Complete feature guide
- **[API Reference](docs/api_reference.md)** - Programming interface
- **[Advanced Configuration](docs/advanced_config.md)** - Customization options
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[Live Demo](https://demo.kirolinter.ai)** - See it in action

---

## 💡 Tips & Tricks

### Pro Tips
1. **Start small**: Begin with a single file or small project to understand the output
2. **Learn first**: Run `agent learn` to get personalized analysis
3. **Use dry-run**: Test fixes with `--dry-run` before applying
4. **Monitor performance**: Check the dashboard for system insights
5. **Customize config**: Tailor settings to your team's needs

### Power User Commands
```bash
# Analyze specific file types only
kirolinter analyze . --format=json | jq '.issues[] | select(.file | endswith(".py"))'

# Chain commands for complex workflows
kirolinter agent learn --repo=. --commits=100 && \
kirolinter agent workflow --repo=. --auto-apply --create-pr

# Background monitoring with logging
nohup kirolinter daemon start --interval=1800 --log-file=/var/log/kirolinter.log &
```

---

<div align="center">

## 🎉 You're Ready!

**KiroLinter is now providing AI-powered code analysis and recommendations.**

🤖 **AI-Powered Analysis** • 📊 **Detailed Insights** • 🛡️ **Security-Focused** • ⚡ **Fast Analysis**

---

**Built with ❤️ using Kiro IDE for the Code with Kiro Hackathon 2025**

[GitHub Repository](https://github.com/yourusername/kirolinter) • [Documentation](README.md) • [Live Demo](https://demo.kirolinter.ai) • [Kiro IDE](https://kiro.ai)

</div>