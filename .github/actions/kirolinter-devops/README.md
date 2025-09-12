# KiroLinter DevOps Quality Gate Action

GitHub Action for running KiroLinter DevOps quality gates with comprehensive CI/CD integration.

## 🚀 Features

- **Pre-commit, Pre-merge, Pre-deploy, and Post-deploy** quality gates
- **AI-powered risk assessment** for deployment impact analysis  
- **SARIF report generation** for GitHub Security tab integration
- **Automatic PR comments** with quality insights
- **GitHub check runs** with detailed status reporting
- **Redis-powered** pattern matching and event storage

## 📋 Prerequisites

This action requires:

1. **Redis server** running and accessible
2. **KiroLinter** installed with DevOps dependencies
3. **Proper GitHub permissions** (see below)
4. **Optional**: OpenAI API key for AI-powered features

## 🔐 Required Permissions

**CRITICAL**: This action requires specific GitHub permissions to function properly. Add this to your workflow file:

```yaml
permissions:
  contents: read
  checks: write        # Required for creating check runs
  pull-requests: write # Required for PR comments  
  security-events: write # Required for SARIF uploads
  issues: read
```

**Without these permissions, you'll get the error:**
```
Error: Resource not accessible by integration - create-a-check-run
```

## 💡 Usage

### Basic Usage

```yaml
- name: Run KiroLinter DevOps Quality Gate
  uses: ./.github/actions/kirolinter-devops
  with:
    gate-type: 'pre-deploy'
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Advanced Usage

```yaml
- name: Run Advanced Quality Gate  
  uses: ./.github/actions/kirolinter-devops
  with:
    gate-type: 'pre-deploy'
    risk-assessment: true
    deployment-analysis: true
    fail-on-issues: true
    severity-threshold: 'medium'
    create-check-run: true
    output-format: 'sarif'
    github-token: ${{ secrets.GITHUB_TOKEN }}
    config-path: '.kirolinter.yml'
    create-pr-comment: true
    timeout: 300
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    REDIS_URL: 'redis://localhost:6379'
```

## 📊 Complete Workflow Example

```yaml
name: 'KiroLinter DevOps Quality Gates'

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

# ⚠️  REQUIRED: These permissions are essential
permissions:
  contents: read
  checks: write
  pull-requests: write
  security-events: write
  issues: read

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Redis
      run: |
        sudo apt-get update
        sudo apt-get install -y redis-server
        sudo systemctl start redis-server
        redis-cli ping
    
    - name: Install KiroLinter
      run: |
        pip install -e ".[devops,ai]"
        kirolinter devops init
    
    - name: Run Quality Gate
      uses: ./.github/actions/kirolinter-devops
      with:
        gate-type: 'pre-deploy'
        risk-assessment: true
        deployment-analysis: true
        fail-on-issues: false
        create-check-run: true
        github-token: ${{ secrets.GITHUB_TOKEN }}
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        REDIS_URL: 'redis://localhost:6379'
    
    - name: Upload SARIF results
      if: always()
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'kirolinter-results.sarif'
        category: 'kirolinter-devops'
```

## ⚙️ Input Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `gate-type` | Quality gate type (`pre-commit`, `pre-merge`, `pre-deploy`, `post-deploy`) | Yes | `pre-merge` |
| `risk-assessment` | Enable AI-powered risk assessment | No | `true` |
| `deployment-analysis` | Enable deployment impact analysis | No | `true` |
| `fail-on-issues` | Fail the action if critical issues found | No | `true` |
| `github-token` | GitHub token for API access | No | `${{ github.token }}` |
| `config-path` | Path to KiroLinter config file | No | `.kirolinter.yml` |
| `output-format` | Output format (`json`, `markdown`, `sarif`) | No | `markdown` |
| `create-pr-comment` | Create PR comment with results | No | `true` |
| `create-check-run` | Create GitHub check run | No | `true` |
| `severity-threshold` | Minimum severity to report | No | `medium` |
| `timeout` | Analysis timeout in seconds | No | `300` |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `quality-score` | Overall quality score (0-100) |
| `issues-found` | Number of issues found |
| `critical-issues` | Number of critical issues |
| `high-issues` | Number of high severity issues |
| `medium-issues` | Number of medium severity issues |
| `low-issues` | Number of low severity issues |
| `risk-score` | Deployment risk score (0-100) |
| `passed` | Whether quality gate passed (true/false) |
| `report-url` | URL to detailed quality report |
| `sarif-file` | Path to SARIF report file |
| `check-run-id` | ID of created GitHub check run |

## 🐛 Troubleshooting

### "Resource not accessible by integration" Error

This error occurs when the workflow doesn't have the required permissions. Add these permissions to your workflow:

```yaml
permissions:
  contents: read
  checks: write        # ← This is required for check runs
  pull-requests: write # ← This is required for PR comments
  security-events: write # ← This is required for SARIF uploads
```

### Redis Connection Issues

Ensure Redis is properly installed and running:

```yaml
- name: Install and Start Redis
  run: |
    sudo apt-get update
    sudo apt-get install -y redis-server
    sudo systemctl start redis-server
    redis-cli ping  # Should return PONG
```

### KiroLinter Installation Issues

Install with all required dependencies:

```yaml
- name: Install KiroLinter
  run: |
    pip install -e ".[devops,ai]"  # Install all features
    kirolinter devops init         # Initialize DevOps infrastructure
```

### Timeout Issues

Increase the timeout for large repositories:

```yaml
- name: Run Quality Gate
  uses: ./.github/actions/kirolinter-devops
  with:
    timeout: 600  # 10 minutes
```

## 🔧 Development

To rebuild the action after making changes:

```bash
cd .github/actions/kirolinter-devops
npm install
npm run build
```

The `dist/index.js` file must be committed after rebuilding.

## 📚 Examples

See the [workflow examples](.github/workflows/) directory for complete working examples of different quality gate configurations.

## 🤝 Support

For issues with this GitHub Action:

1. Check the [troubleshooting section](#-troubleshooting) above
2. Ensure all required permissions are set
3. Verify Redis is running and accessible
4. Check the action logs for detailed error information

For general KiroLinter support, see the main [README](../../../README.md) and [QUICKSTART](../../../QUICKSTART.md) guides.