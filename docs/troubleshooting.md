# Troubleshooting Guide 🔧

This guide helps you diagnose and resolve common issues with KiroLinter's agentic system. Find quick solutions to get your autonomous code review system running smoothly.

## 📋 Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Redis Connection Problems](#redis-connection-problems)
- [Agent System Issues](#agent-system-issues)
- [AI Provider Problems](#ai-provider-problems)
- [Performance Issues](#performance-issues)
- [Configuration Errors](#configuration-errors)
- [Workflow Failures](#workflow-failures)
- [Memory and Storage Issues](#memory-and-storage-issues)
- [Integration Problems](#integration-problems)
- [Debug Mode and Logging](#debug-mode-and-logging)

## Quick Diagnostics

### Health Check Command

```bash
# Run comprehensive system health check
kirolinter doctor

# Expected output for healthy system:
✅ Python version: 3.9.0 (supported)
✅ Redis connection: Connected to localhost:6379
✅ Pattern memory: 1,247 patterns loaded
✅ AI providers: OpenAI (healthy), XAI (healthy)
✅ Agents: All 6 agents operational
✅ Memory usage: 245MB / 1024MB (24%)
✅ Disk space: 15GB available
✅ Configuration: Valid
```

### System Status Check

```bash
# Quick status overview
kirolinter status

# Detailed component status
kirolinter status --verbose

# Check specific component
kirolinter status --component=redis
kirolinter status --component=agents
kirolinter status --component=memory
```

## Installation Issues

### 1. Python Version Compatibility

**Problem**: KiroLinter requires Python 3.8+ but system has older version

```bash
# Check Python version
python --version
# or
python3 --version

# Error: Python 3.7.x or older
```

**Solution**:
```bash
# Install Python 3.8+ using pyenv (recommended)
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0

# Or use system package manager
# Ubuntu/Debian:
sudo apt update && sudo apt install python3.11

# macOS:
brew install python@3.11
```

### 2. Dependencies Installation Failures

**Problem**: Package installation fails with dependency conflicts

```bash
# Error example:
ERROR: pip's dependency resolver does not currently consider all the packages
```

**Solution**:
```bash
# Clean install with fresh virtual environment
python -m venv kirolinter-env
source kirolinter-env/bin/activate  # Linux/Mac
# or kirolinter-env\Scripts\activate  # Windows

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install KiroLinter
pip install -e ".[ai]"

# If still failing, install dependencies individually
pip install redis langchain langchain-openai psutil click pyyaml
```

### 3. Permission Errors

**Problem**: Permission denied when installing or running

```bash
# Error: PermissionError: [Errno 13] Permission denied
```

**Solution**:
```bash
# Option 1: Install for user only
pip install --user kirolinter

# Option 2: Fix permissions
sudo chown -R $(whoami) ~/.local/
sudo chown -R $(whoami) ~/.kirolinter/

# Option 3: Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install kirolinter
```

## Redis Connection Problems

### 1. Redis Not Running

**Problem**: Connection refused to Redis server

```bash
# Error: redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Diagnosis**:
```bash
# Check if Redis is running
redis-cli ping
# Expected: PONG

# Check Redis status
systemctl status redis  # Linux
brew services list | grep redis  # macOS
```

**Solution**:
```bash
# Start Redis server
# Linux:
sudo systemctl start redis
sudo systemctl enable redis  # Auto-start on boot

# macOS:
brew services start redis

# Manual start:
redis-server --daemonize yes

# Verify connection:
redis-cli ping  # Should return PONG
```

### 2. Redis Authentication Issues

**Problem**: Authentication failed with Redis password

```bash
# Error: NOAUTH Authentication required
```

**Solution**:
```bash
# Option 1: Configure password in .kirolinter.yaml
memory:
  redis:
    host: localhost
    port: 6379
    password: "your-redis-password"

# Option 2: Set environment variable
export REDIS_PASSWORD="your-redis-password"

# Option 3: Test connection manually
redis-cli -a your-redis-password ping
```

### 3. Redis Memory Issues

**Problem**: Redis running out of memory

```bash
# Error: OOM command not allowed when used memory > 'maxmemory'
```

**Diagnosis**:
```bash
# Check Redis memory usage
redis-cli info memory

# Check Redis configuration
redis-cli config get maxmemory
```

**Solution**:
```bash
# Increase Redis memory limit
redis-cli config set maxmemory 2gb
redis-cli config set maxmemory-policy allkeys-lru

# Or edit redis.conf permanently
echo "maxmemory 2gb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf

# Clean up old patterns
kirolinter admin cleanup --older-than=30days
```

## Agent System Issues

### 1. Agents Not Starting

**Problem**: Agent initialization fails

```bash
# Error: Failed to initialize agent system
```

**Diagnosis**:
```bash
# Check agent status
kirolinter agent status

# Check configuration
kirolinter config validate --section=agents

# Check logs
kirolinter logs --component=agents --tail=50
```

**Solution**:
```bash
# Restart agent system
kirolinter agent restart

# Reset agent state
kirolinter agent reset --confirm

# Check dependencies
pip install langchain langchain-openai litellm

# Verify AI provider access
export OPENAI_API_KEY="your-key"
kirolinter agent test --provider=openai
```

### 2. Workflow Execution Failures

**Problem**: Workflows fail to complete

```bash
# Error: Workflow 'full_review' failed with status 'partial_complete'
```

**Diagnosis**:
```bash
# Check workflow history
kirolinter agent history --failed

# Get detailed workflow status
kirolinter agent status --workflow=full_review --verbose

# Check workflow logs
kirolinter logs --workflow=full_review --last=1
```

**Solution**:
```bash
# Retry failed workflow
kirolinter agent retry --workflow-id=abc123

# Reduce workflow complexity
kirolinter agent workflow --template=quick_fix --repo=.

# Check resource usage
kirolinter status --resources

# Increase timeout
kirolinter agent workflow --timeout=600 --repo=.
```

### 3. Agent Communication Issues

**Problem**: Agents can't communicate with each other

```bash
# Error: Agent communication timeout
```

**Solution**:
```bash
# Check Redis connection (agents use Redis for communication)
redis-cli ping

# Restart agent coordinator
kirolinter agent restart --component=coordinator

# Check firewall settings
sudo ufw status  # Linux
# Ensure Redis port 6379 is accessible

# Verify network connectivity
telnet localhost 6379
```

## AI Provider Problems

### 1. OpenAI API Issues

**Problem**: OpenAI API calls failing

```bash
# Error: openai.error.RateLimitError: Rate limit exceeded
# Error: openai.error.AuthenticationError: Invalid API key
```

**Diagnosis**:
```bash
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check rate limits
kirolinter agent test --provider=openai --verbose
```

**Solution**:
```bash
# Rate limit issues:
# Reduce request rate in configuration
ai:
  providers:
    openai:
      rate_limiting:
        requests_per_minute: 20  # Reduce from default

# Invalid API key:
# Verify and update API key
export OPENAI_API_KEY="sk-your-new-key"

# Use fallback provider
ai:
  fallback_to_rules: true
  provider_priority: ["xai", "openai"]
```

### 2. XAI/Grok API Issues

**Problem**: XAI Grok API connectivity issues

```bash
# Error: xai.error.APIConnectionError: Connection timeout
```

**Solution**:
```bash
# Check XAI API status
curl -H "Authorization: Bearer $XAI_API_KEY" \
     https://api.x.ai/v1/models

# Update configuration for XAI
ai:
  providers:
    xai:
      timeout: 60  # Increase timeout
      retry_attempts: 5

# Test XAI connection
kirolinter agent test --provider=xai
```

### 3. Local Model Issues

**Problem**: Local LLM model not responding

```bash
# Error: Connection refused to local model endpoint
```

**Solution**:
```bash
# Check if local model server is running
curl http://localhost:8000/health

# Start local model server (example with Ollama)
ollama serve
ollama run llama2

# Update configuration
ai:
  providers:
    local:
      endpoint: "http://localhost:11434"  # Ollama default
      model: "llama2"
```

## Performance Issues

### 1. Slow Analysis Performance

**Problem**: Analysis takes too long

```bash
# Analysis taking > 30 seconds for small projects
```

**Diagnosis**:
```bash
# Profile performance
kirolinter analyze . --profile --verbose

# Check system resources
kirolinter status --resources

# Monitor during analysis
top -p $(pgrep -f kirolinter)
```

**Solution**:
```bash
# Enable parallel processing
performance:
  max_workers: 8
  parallel_file_analysis: true
  
# Reduce analysis scope
analysis:
  exclude_patterns:
    - "venv/*"
    - "node_modules/*"
    - "*.pyc"
    - "__pycache__/*"

# Use incremental analysis
kirolinter analyze . --incremental

# Optimize Redis
redis-cli config set save ""  # Disable disk persistence for speed
```

### 2. High Memory Usage

**Problem**: KiroLinter consuming too much memory

```bash
# Memory usage > 2GB
```

**Diagnosis**:
```bash
# Check memory usage breakdown
kirolinter status --memory --verbose

# Monitor memory during analysis
watch -n 1 'ps aux | grep kirolinter'
```

**Solution**:
```bash
# Limit memory usage
performance:
  max_memory_mb: 1024
  gc_threshold: 0.7

# Reduce cache sizes
memory:
  storage:
    max_patterns_per_repo: 5000
performance:
  pattern_cache_size: 500

# Enable garbage collection
kirolinter admin gc --force
```

### 3. Redis Performance Issues

**Problem**: Redis operations are slow

```bash
# Redis response time > 100ms
```

**Solution**:
```bash
# Optimize Redis configuration
redis-cli config set maxmemory-policy allkeys-lru
redis-cli config set timeout 300

# Check Redis slow log
redis-cli slowlog get 10

# Consider Redis clustering for large datasets
# Or use Redis with SSD storage
```

## Configuration Errors

### 1. Invalid Configuration File

**Problem**: Configuration file has syntax errors

```bash
# Error: yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.kirolinter.yaml'))"

# Use configuration validation
kirolinter config validate --strict

# Generate fresh configuration
kirolinter config init --template=basic --force
```

### 2. Missing Configuration Values

**Problem**: Required configuration values missing

```bash
# Error: Missing required configuration: ai.providers.openai.api_key
```

**Solution**:
```bash
# Set missing values via environment variables
export OPENAI_API_KEY="your-key"

# Or update configuration file
ai:
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"

# Check configuration completeness
kirolinter config check --required
```

## Workflow Failures

### 1. Workflow Timeout

**Problem**: Workflows timing out

```bash
# Error: Workflow execution timeout after 300 seconds
```

**Solution**:
```bash
# Increase timeout
workflows:
  max_execution_time: 1800  # 30 minutes

# Or use simpler workflow
kirolinter agent workflow --template=quick_fix --repo=.

# Check for stuck processes
ps aux | grep kirolinter
kill -9 <stuck-process-pid>
```

### 2. Partial Workflow Completion

**Problem**: Workflows complete partially

```bash
# Status: partial_complete (3/5 steps completed)
```

**Diagnosis**:
```bash
# Check workflow details
kirolinter agent history --workflow-id=abc123 --verbose

# Check step-specific errors
kirolinter logs --workflow=abc123 --step=fix
```

**Solution**:
```bash
# Resume from last successful step
kirolinter agent resume --workflow-id=abc123

# Reduce workflow scope
kirolinter agent workflow --template=analyze_only --repo=.

# Check individual agent health
kirolinter agent status --component=fixer
```

## Memory and Storage Issues

### 1. Pattern Storage Full

**Problem**: Pattern storage approaching limits

```bash
# Warning: Pattern storage 95% full (9,500/10,000 patterns)
```

**Solution**:
```bash
# Clean up old patterns
kirolinter admin cleanup --older-than=90days

# Increase storage limits
memory:
  storage:
    max_patterns_per_repo: 20000

# Archive old patterns
kirolinter admin export --older-than=180days --output=archive.json
kirolinter admin cleanup --older-than=180days
```

### 2. Disk Space Issues

**Problem**: Insufficient disk space

```bash
# Error: No space left on device
```

**Solution**:
```bash
# Check disk usage
df -h ~/.kirolinter/

# Clean up logs
kirolinter admin cleanup --logs --older-than=30days

# Compress old backups
gzip ~/.kirolinter/backups/*.json

# Move data to larger disk
kirolinter admin migrate --data-dir=/path/to/larger/disk
```

## Integration Problems

### 1. GitHub Integration Issues

**Problem**: GitHub PR creation failing

```bash
# Error: 401 Unauthorized - Bad credentials
```

**Solution**:
```bash
# Check GitHub token permissions
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/user

# Update token with required scopes:
# - repo (for private repos)
# - public_repo (for public repos)
# - workflow (for GitHub Actions)

# Test GitHub integration
kirolinter github test --repo=owner/repo
```

### 2. Git Hooks Not Working

**Problem**: Git hooks not triggering analysis

```bash
# Commits not triggering KiroLinter analysis
```

**Solution**:
```bash
# Reinstall hooks
kirolinter hooks install --force

# Check hook permissions
ls -la .git/hooks/
chmod +x .git/hooks/post-commit

# Test hook manually
.git/hooks/post-commit

# Check hook content
cat .git/hooks/post-commit
```

## Debug Mode and Logging

### Enable Debug Mode

```bash
# Enable debug mode globally
export KIROLINTER_DEBUG=true
export KIROLINTER_LOG_LEVEL=DEBUG

# Or in configuration
development:
  debug_mode: true
  verbose_logs: true

# Run with debug output
kirolinter analyze . --debug --verbose
```

### Access Logs

```bash
# View recent logs
kirolinter logs --tail=100

# View logs by component
kirolinter logs --component=agents --tail=50
kirolinter logs --component=redis --tail=50

# View logs by time range
kirolinter logs --since="1 hour ago"
kirolinter logs --since="2024-08-16 10:00"

# Export logs for analysis
kirolinter logs --export --output=debug.log
```

### Log Locations

```bash
# Default log locations
~/.kirolinter/logs/kirolinter.log      # Main application log
~/.kirolinter/logs/agents.log          # Agent system log
~/.kirolinter/logs/workflows.log       # Workflow execution log
~/.kirolinter/logs/audit.log           # Audit trail
~/.kirolinter/logs/performance.log     # Performance metrics

# Real-time log monitoring
tail -f ~/.kirolinter/logs/kirolinter.log
```

## Emergency Recovery

### Complete System Reset

```bash
# ⚠️ WARNING: This will delete all patterns and configuration
kirolinter admin reset --all --confirm

# Steps performed:
# 1. Stop all running processes
# 2. Clear Redis database
# 3. Remove pattern storage
# 4. Reset configuration to defaults
# 5. Clear all logs and backups
```

### Backup and Restore

```bash
# Create full backup before troubleshooting
kirolinter admin backup --output=emergency-backup.tar.gz

# Restore from backup if needed
kirolinter admin restore --input=emergency-backup.tar.gz
```

### Safe Mode

```bash
# Start in safe mode (basic features only)
kirolinter --safe-mode analyze .

# Safe mode disables:
# - AI providers
# - Agent system
# - Pattern learning
# - Automatic fixes
```

## Getting Additional Help

### Community Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/yourusername/kirolinter/issues)
- **Discussions**: [Community Q&A and tips](https://github.com/yourusername/kirolinter/discussions)
- **Discord**: Join our [Discord server](https://discord.gg/kirolinter) for real-time help

### Professional Support

- **Enterprise Support**: Contact enterprise@kirolinter.ai
- **Consulting**: Professional setup and optimization services
- **Training**: Team training and onboarding

### Reporting Bugs

When reporting issues, include:

```bash
# Generate diagnostic report
kirolinter doctor --output=diagnostic-report.json

# Include in bug report:
# 1. Diagnostic report
# 2. Configuration file (.kirolinter.yaml)
# 3. Recent logs
# 4. Steps to reproduce
# 5. Expected vs actual behavior
```

---

**Next**: Check out [Best Practices](best_practices.md) for optimal KiroLinter deployment and usage patterns.