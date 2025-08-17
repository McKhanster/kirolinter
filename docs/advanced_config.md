# Advanced Configuration Guide 🛠️

This guide covers advanced configuration options for KiroLinter's agentic system, allowing you to customize every aspect of the multi-agent architecture for your specific needs.

## 📋 Table of Contents

- [Configuration File Structure](#configuration-file-structure)
- [Agent Configuration](#agent-configuration)
- [Pattern Memory Settings](#pattern-memory-settings)
- [Workflow Customization](#workflow-customization)
- [Redis Configuration](#redis-configuration)
- [AI Provider Settings](#ai-provider-settings)
- [Performance Tuning](#performance-tuning)
- [Security Configuration](#security-configuration)
- [Integration Settings](#integration-settings)
- [Environment Variables](#environment-variables)

## Configuration File Structure

KiroLinter uses a hierarchical configuration system with multiple sources:

```bash
# Configuration precedence (highest to lowest):
1. Command-line arguments
2. Environment variables
3. .kirolinter.yaml (project-specific)
4. ~/.kirolinter/config.yaml (user-global)
5. Default values
```

### Complete Configuration File Example

```yaml
# .kirolinter.yaml - Complete configuration example
version: "1.0"
name: "MyProject KiroLinter Config"

# === BASIC ANALYSIS SETTINGS ===
analysis:
  enabled_rules:
    - unused_variable
    - unused_import
    - hardcoded_secret
    - sql_injection
    - unsafe_eval
    - complex_function
    - inefficient_loop
    - security_headers
  
  severity_threshold: medium
  max_complexity: 10
  max_line_length: 88
  
  exclude_patterns:
    - "tests/*"
    - "venv/*"
    - "__pycache__/*"
    - "*.pyc"
    - ".git/*"
    - "docs/_build/*"
  
  include_patterns:
    - "*.py"
    - "*.pyi"

# === AGENTIC SYSTEM CONFIGURATION ===
agents:
  # Global agent settings
  enable_system: true
  verbose_logging: true
  error_recovery: true
  
  # Coordinator Agent
  coordinator:
    enabled: true
    max_concurrent_workflows: 5
    workflow_timeout: 300  # 5 minutes
    error_retry_attempts: 3
    state_persistence: true
    
  # Reviewer Agent  
  reviewer:
    enabled: true
    pattern_aware_analysis: true
    intelligent_prioritization: true
    risk_assessment: true
    confidence_threshold: 0.8
    max_issues_per_file: 50
    
  # Fixer Agent
  fixer:
    enabled: true
    auto_apply_fixes: false  # Set to true for autonomous mode
    confidence_threshold: 0.95
    create_backups: true
    validate_syntax: true
    rollback_on_failure: true
    max_fixes_per_session: 100
    
  # Integrator Agent
  integrator:
    enabled: true
    create_prs: true
    assign_reviewers: true
    add_pr_labels: true
    merge_strategy: "squash"
    branch_prefix: "kirolinter/"
    
  # Learner Agent
  learner:
    enabled: true
    continuous_learning: true
    max_commits_to_analyze: 1000
    pattern_extraction_ml: true
    statistical_fallback: true
    cross_repo_learning: true
    
  # Cross-Repository Learner
  cross_repo_learner:
    enabled: true
    privacy_preservation: true
    anonymization_strength: "high"
    pattern_sharing: true
    similarity_threshold: 0.7

# === WORKFLOW CONFIGURATION ===
workflows:
  # Pre-defined workflow templates
  templates:
    quick_fix:
      steps: ["analyze", "fix"]
      auto_apply: true
      confidence_threshold: 0.9
      
    full_review:
      steps: ["predict", "analyze", "fix", "integrate", "learn"]
      auto_apply: false
      create_pr: true
      
    security_focus:
      steps: ["predict", "analyze", "fix", "notify"]
      severity_filter: ["critical", "high"]
      auto_apply: false
      
    daily_maintenance:
      steps: ["learn", "analyze", "notify"]
      schedule: "0 9 * * *"  # 9 AM daily
      
    weekly_deep_review:
      steps: ["predict", "analyze", "fix", "integrate", "learn"]
      schedule: "0 0 * * 0"  # Sunday midnight
      
  # Custom workflow settings
  default_template: "full_review"
  max_execution_time: 1800  # 30 minutes
  concurrent_execution: false
  state_checkpointing: true

# === PATTERN MEMORY CONFIGURATION ===
memory:
  # Redis configuration
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: null
    ssl: false
    connection_pool_size: 10
    socket_timeout: 5
    socket_connect_timeout: 5
    
  # Pattern storage settings  
  storage:
    max_patterns_per_repo: 10000
    pattern_expiry_days: 365
    compression: true
    encryption: false
    backup_interval: 86400  # 24 hours
    
  # Learning configuration
  learning:
    confidence_decay_rate: 0.001
    pattern_merge_threshold: 0.85
    quality_threshold: 0.7
    max_pattern_age_days: 180

# === AI PROVIDER CONFIGURATION ===
ai:
  # Primary provider
  primary_provider: "openai"
  
  # Provider-specific settings
  providers:
    openai:
      model: "gpt-4"
      api_key: "${OPENAI_API_KEY}"
      temperature: 0.1
      max_tokens: 1000
      timeout: 30
      
    xai:
      model: "grok-beta"
      api_key: "${XAI_API_KEY}"
      temperature: 0.2
      max_tokens: 1500
      timeout: 45
      
    local:
      model: "llama2"
      endpoint: "http://localhost:8000"
      timeout: 60
      
  # Fallback configuration
  fallback_to_rules: true
  retry_attempts: 3
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300

# === PERFORMANCE CONFIGURATION ===
performance:
  # Concurrency settings
  max_workers: 4
  thread_pool_size: 8
  process_pool_size: 2
  
  # Memory management
  max_memory_mb: 1024
  gc_threshold: 0.8
  cache_size: 1000
  
  # Analysis optimization
  parallel_file_analysis: true
  lazy_loading: true
  smart_caching: true
  incremental_analysis: true
  
  # Rate limiting
  requests_per_second: 10
  burst_size: 20

# === SECURITY CONFIGURATION ===
security:
  # Data protection
  anonymization:
    enabled: true
    strength: "high"
    preserve_structure: true
    
  # Sensitive data patterns
  sensitive_patterns:
    - "(?i)(password|pwd|secret|key|token)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"
    - "(?i)api[_-]?key\\s*[:=]\\s*['\"][^'\"]+['\"]"
    - "(?i)(access|refresh)[_-]?token\\s*[:=]\\s*['\"][^'\"]+['\"]"
    - "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"
    - "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
    
  # Audit logging
  audit:
    enabled: true
    log_level: "INFO"
    retain_days: 90
    log_file: "~/.kirolinter/audit.log"
    
  # Access control
  permissions:
    read_patterns: ["developer", "reviewer", "admin"]
    write_patterns: ["admin"]
    execute_workflows: ["developer", "admin"]

# === INTEGRATION CONFIGURATION ===
integrations:
  # GitHub integration
  github:
    enabled: true
    token: "${GITHUB_TOKEN}"
    base_url: "https://api.github.com"
    
    # PR settings
    pr_settings:
      title_template: "🤖 KiroLinter: {{issue_count}} Code Quality Improvements"
      body_template: |
        ## 🤖 Autonomous Code Quality Improvements
        
        KiroLinter has analyzed your code and applied the following improvements:
        
        ### 📊 Summary
        - **Issues Found**: {{issues_found}}
        - **Fixes Applied**: {{fixes_applied}}
        - **Confidence Score**: {{avg_confidence}}%
        
        ### 🔍 Changes Made
        {{change_details}}
        
        ### 🧠 Learning Insights
        {{learning_insights}}
        
        ---
        *Generated by KiroLinter v{{version}} • [Learn more](https://github.com/yourusername/kirolinter)*
        
      labels: ["code-quality", "automated", "kirolinter"]
      assignees: []
      reviewers: []
      
  # Git hooks
  git_hooks:
    enabled: true
    pre_commit: true
    post_commit: true
    pre_push: false
    
  # CI/CD integration
  ci_cd:
    enabled: true
    platforms: ["github-actions", "jenkins", "gitlab-ci"]
    webhook_url: null
    secret_token: "${CI_WEBHOOK_SECRET}"

# === MONITORING & ALERTING ===
monitoring:
  # Health checks
  health_checks:
    enabled: true
    interval: 300  # 5 minutes
    timeout: 30
    
  # Metrics collection
  metrics:
    enabled: true
    prometheus_endpoint: "http://localhost:9090"
    custom_metrics: true
    
  # Alerting
  alerts:
    enabled: true
    webhook_url: "${ALERT_WEBHOOK_URL}"
    email_smtp:
      host: "smtp.gmail.com"
      port: 587
      username: "${SMTP_USERNAME}"
      password: "${SMTP_PASSWORD}"
      
    # Alert conditions
    conditions:
      high_error_rate: 0.1
      memory_usage_threshold: 0.9
      response_time_threshold: 5000
      pattern_storage_full: 0.95

# === DAEMON CONFIGURATION ===
daemon:
  # Service settings
  enabled: true
  pid_file: "~/.kirolinter/daemon.pid"
  log_file: "~/.kirolinter/daemon.log"
  
  # Scheduling
  scheduler:
    enabled: true
    timezone: "UTC"
    max_jobs: 10
    
  # Job definitions
  jobs:
    pattern_learning:
      schedule: "0 */6 * * *"  # Every 6 hours
      workflow: "learn_only"
      
    health_check:
      schedule: "*/5 * * * *"  # Every 5 minutes
      workflow: "health_check"
      
    weekly_analysis:
      schedule: "0 0 * * 0"   # Sunday midnight
      workflow: "full_review"

# === DEVELOPMENT & DEBUGGING ===
development:
  # Debug settings
  debug_mode: false
  verbose_logs: false
  profile_performance: false
  
  # Testing
  test_mode: false
  mock_ai_responses: false
  dry_run: false
  
  # Development tools
  hot_reload: false
  auto_restart: false
  development_server: false
```

## Agent Configuration

### Coordinator Agent Settings

```yaml
agents:
  coordinator:
    enabled: true
    
    # Workflow management
    max_concurrent_workflows: 5
    workflow_timeout: 300
    workflow_retry_attempts: 3
    
    # State management
    state_persistence: true
    state_storage_backend: "redis"
    checkpoint_interval: 30
    
    # Error handling
    error_recovery: true
    graceful_degradation: true
    fallback_workflows: true
    
    # Performance
    resource_monitoring: true
    auto_scaling: false
    load_balancing: true
```

### Reviewer Agent Settings

```yaml
agents:
  reviewer:
    enabled: true
    
    # Analysis configuration
    pattern_aware_analysis: true
    intelligent_prioritization: true
    risk_assessment: true
    
    # Quality thresholds
    confidence_threshold: 0.8
    min_severity_level: "low"
    max_issues_per_file: 50
    
    # Performance optimization
    parallel_analysis: true
    cache_results: true
    incremental_mode: true
    
    # AI integration
    ai_enhanced_analysis: true
    fallback_to_static: true
    ai_timeout: 30
```

### Fixer Agent Settings

```yaml
agents:
  fixer:
    enabled: true
    
    # Fix application
    auto_apply_fixes: false
    confidence_threshold: 0.95
    max_fixes_per_session: 100
    
    # Safety measures
    create_backups: true
    validate_syntax: true
    rollback_on_failure: true
    safety_checks: ["syntax", "imports", "references"]
    
    # Fix types
    allowed_fix_types: ["replace", "insert", "delete", "format"]
    forbidden_patterns: ["eval", "exec", "subprocess"]
    
    # Adaptation
    adaptive_confidence: true
    learn_from_outcomes: true
    confidence_adjustment_rate: 0.05
```

## Pattern Memory Settings

### Redis Configuration

```yaml
memory:
  redis:
    # Connection settings
    host: "localhost"
    port: 6379
    db: 0
    password: null
    ssl: false
    
    # Connection pooling
    connection_pool_size: 10
    max_connections: 50
    
    # Timeouts
    socket_timeout: 5
    socket_connect_timeout: 5
    health_check_interval: 30
    
    # Advanced settings
    decode_responses: true
    retry_on_timeout: true
    unix_socket_path: null
```

### Pattern Storage Configuration

```yaml
memory:
  storage:
    # Capacity limits
    max_patterns_per_repo: 10000
    max_total_patterns: 100000
    pattern_size_limit_kb: 100
    
    # Retention policies
    pattern_expiry_days: 365
    auto_cleanup: true
    cleanup_interval: 86400
    
    # Optimization
    compression: true
    compression_algorithm: "gzip"
    encryption: false
    indexing: true
    
    # Backup settings
    backup_enabled: true
    backup_interval: 86400
    backup_retention: 30
    backup_location: "~/.kirolinter/backups"
```

## Workflow Customization

### Creating Custom Workflows

```yaml
workflows:
  templates:
    # Custom security-focused workflow
    security_audit:
      description: "Deep security analysis workflow"
      steps:
        - name: "security_scan"
          agent: "reviewer"
          config:
            focus: "security"
            severity_filter: ["critical", "high"]
            
        - name: "vulnerability_fix"
          agent: "fixer"
          config:
            auto_apply: false
            require_confirmation: true
            
        - name: "security_report"
          agent: "integrator"
          config:
            create_issue: true
            notify_security_team: true
            
      # Workflow conditions
      triggers:
        - "commit_contains_security_files"
        - "scheduled_weekly"
        
      # Success criteria
      success_conditions:
        - "no_critical_issues"
        - "all_fixes_validated"
```

### Conditional Workflow Execution

```yaml
workflows:
  conditional_execution:
    enabled: true
    
    # File-based conditions
    file_conditions:
      security_files:
        patterns: ["**/auth.py", "**/security.py", "**/crypto.py"]
        workflow: "security_audit"
        
      test_files:
        patterns: ["**/test_*.py", "**/tests/**/*.py"]
        workflow: "test_analysis"
        
    # Content-based conditions  
    content_conditions:
      sensitive_code:
        patterns: ["password", "secret", "api_key"]
        workflow: "security_audit"
        
      performance_critical:
        patterns: ["@performance", "@critical"]
        workflow: "performance_audit"
```

## AI Provider Settings

### Multiple Provider Configuration

```yaml
ai:
  # Provider priority order
  provider_priority: ["openai", "xai", "local"]
  
  # Load balancing
  load_balancing:
    enabled: true
    strategy: "round_robin"  # or "least_loaded", "random"
    
  # Fallback configuration
  fallback_chain:
    - provider: "openai"
      conditions: ["normal_operation"]
    - provider: "xai" 
      conditions: ["openai_unavailable"]
    - provider: "local"
      conditions: ["all_external_unavailable"]
      
  # Provider-specific configurations
  providers:
    openai:
      models:
        analysis: "gpt-4"
        suggestion: "gpt-3.5-turbo"
        learning: "gpt-4"
      
      rate_limiting:
        requests_per_minute: 60
        tokens_per_minute: 150000
        
      retry_config:
        max_retries: 3
        backoff_factor: 2
        
    xai:
      models:
        analysis: "grok-beta"
        suggestion: "grok-beta"
        learning: "grok-beta"
        
      rate_limiting:
        requests_per_minute: 100
        tokens_per_minute: 200000
```

## Performance Tuning

### Memory Management

```yaml
performance:
  memory:
    # Heap settings
    max_heap_size_mb: 2048
    gc_threshold: 0.8
    gc_frequency: 60
    
    # Caching
    pattern_cache_size: 1000
    analysis_cache_size: 500
    cache_ttl: 3600
    
    # Memory monitoring
    monitor_usage: true
    alert_threshold: 0.9
    auto_cleanup: true
```

### Concurrency Settings

```yaml
performance:
  concurrency:
    # Thread pools
    analyzer_threads: 4
    fixer_threads: 2
    learner_threads: 1
    
    # Process pools
    file_analysis_processes: 2
    pattern_extraction_processes: 1
    
    # Queue settings
    work_queue_size: 1000
    priority_queue: true
    
    # Rate limiting
    global_rate_limit: 100
    per_agent_rate_limit: 25
```

## Security Configuration

### Data Protection

```yaml
security:
  data_protection:
    # Encryption
    encryption_at_rest: true
    encryption_algorithm: "AES-256"
    key_rotation_days: 90
    
    # Anonymization
    anonymization:
      strength: "high"  # low, medium, high
      preserve_structure: true
      reversible: false
      
    # Data retention
    retention_policy:
      patterns: 365  # days
      audit_logs: 90
      backups: 30
      
    # Access control
    rbac:
      enabled: true
      roles:
        - name: "viewer"
          permissions: ["read_patterns", "view_reports"]
        - name: "developer"  
          permissions: ["read_patterns", "execute_workflows", "view_reports"]
        - name: "admin"
          permissions: ["*"]
```

### Audit Configuration

```yaml
security:
  audit:
    # Logging
    enabled: true
    log_level: "INFO"
    structured_logs: true
    
    # Events to audit
    events:
      - "pattern_access"
      - "workflow_execution"
      - "fix_application"
      - "configuration_change"
      - "authentication"
      
    # Log rotation
    max_file_size_mb: 100
    max_files: 10
    compression: true
    
    # External logging
    syslog_enabled: false
    external_endpoint: null
```

## Environment Variables

### Core Variables

```bash
# === REQUIRED ===
REDIS_HOST=localhost
REDIS_PORT=6379

# === AI PROVIDERS ===
OPENAI_API_KEY=sk-your-openai-key
XAI_API_KEY=xai-your-grok-key

# === GITHUB INTEGRATION ===
GITHUB_TOKEN=ghp_your-github-token

# === DATABASE ===
REDIS_PASSWORD=your-redis-password
REDIS_DB=0
REDIS_SSL=false

# === SECURITY ===
KIROLINTER_SECRET_KEY=your-secret-key
ANONYMIZATION_SALT=random-salt-value

# === PERFORMANCE ===
KIROLINTER_MAX_WORKERS=4
KIROLINTER_MEMORY_LIMIT=1024

# === MONITORING ===
PROMETHEUS_ENDPOINT=http://localhost:9090
ALERT_WEBHOOK_URL=https://hooks.slack.com/...

# === DEVELOPMENT ===
KIROLINTER_DEBUG=false
KIROLINTER_LOG_LEVEL=INFO
KIROLINTER_PROFILE=false
```

### Environment-Specific Configurations

```bash
# Production environment
cat > .env.production << EOF
REDIS_HOST=redis-cluster.company.com
REDIS_PORT=6379
REDIS_SSL=true
KIROLINTER_LOG_LEVEL=WARN
KIROLINTER_MAX_WORKERS=8
KIROLINTER_MEMORY_LIMIT=4096
EOF

# Development environment  
cat > .env.development << EOF
REDIS_HOST=localhost
REDIS_PORT=6379
KIROLINTER_DEBUG=true
KIROLINTER_LOG_LEVEL=DEBUG
KIROLINTER_PROFILE=true
EOF

# Testing environment
cat > .env.testing << EOF
REDIS_HOST=localhost
REDIS_PORT=6380
KIROLINTER_TEST_MODE=true
KIROLINTER_MOCK_AI=true
EOF
```

## Configuration Validation

### Validate Configuration

```bash
# Validate configuration file
kirolinter config validate

# Test specific configuration sections
kirolinter config test --section=agents
kirolinter config test --section=memory
kirolinter config test --section=workflows

# Show effective configuration (after merging all sources)
kirolinter config show --effective

# Export configuration schema
kirolinter config schema --output=schema.json
```

### Configuration Templates

```bash
# Generate configuration templates
kirolinter config init --template=basic
kirolinter config init --template=enterprise
kirolinter config init --template=development

# Available templates:
# - basic: Minimal configuration for getting started
# - enterprise: Full-featured enterprise configuration
# - development: Development and debugging configuration
# - security: Security-focused configuration
# - performance: Performance-optimized configuration
```

## Best Practices

### Configuration Management

1. **Use Environment-Specific Configs**
   ```bash
   # Development
   cp .kirolinter.yaml .kirolinter.dev.yaml
   
   # Production  
   cp .kirolinter.yaml .kirolinter.prod.yaml
   
   # Load specific config
   export KIROLINTER_CONFIG=.kirolinter.prod.yaml
   ```

2. **Version Control Your Configuration**
   ```bash
   # Include in version control
   git add .kirolinter.yaml
   
   # Exclude secrets
   echo ".env*" >> .gitignore
   ```

3. **Use Configuration Validation**
   ```bash
   # In CI/CD pipeline
   kirolinter config validate --strict
   ```

4. **Monitor Configuration Changes**
   ```bash
   # Audit configuration changes
   kirolinter config diff --before=v1.0 --after=v1.1
   ```

This advanced configuration guide enables you to customize every aspect of KiroLinter's agentic system. Start with the basic configuration and gradually add advanced features as your needs grow.

---

**Next**: Check out [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.