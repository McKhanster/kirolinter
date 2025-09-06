-- KiroLinter DevOps Orchestration Database Schema
-- PostgreSQL schema for workflow state management, analytics, and monitoring

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSONB operators
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Workflow Definitions Table
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    definition JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT unique_workflow_name_version UNIQUE (name, version)
);

-- Workflow Executions Table
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_definition_id UUID NOT NULL REFERENCES workflow_definitions(id),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    triggered_by VARCHAR(255),
    environment VARCHAR(100) DEFAULT 'default',
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_data JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10,3),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    CONSTRAINT valid_duration CHECK (duration_seconds >= 0)
);

-- Workflow Stage Results Table
CREATE TABLE IF NOT EXISTS workflow_stage_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    stage_id VARCHAR(255) NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    stage_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10,3),
    output_data JSONB DEFAULT '{}',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_stage_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'timeout')),
    CONSTRAINT valid_stage_duration CHECK (duration_seconds >= 0),
    CONSTRAINT valid_retry_count CHECK (retry_count >= 0)
);

-- DevOps Metrics Table
CREATE TABLE IF NOT EXISTS devops_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(100) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL, -- ci_cd, infrastructure, application
    source_name VARCHAR(255) NOT NULL, -- github, aws, prometheus, etc.
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    value NUMERIC,
    string_value TEXT,
    dimensions JSONB DEFAULT '{}',
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_metric_value CHECK (value IS NOT NULL OR string_value IS NOT NULL)
);

-- Quality Gates Table
CREATE TABLE IF NOT EXISTS quality_gates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    gate_type VARCHAR(100) NOT NULL, -- pre_commit, pre_merge, pre_deploy, post_deploy
    criteria JSONB NOT NULL,
    configuration JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    
    CONSTRAINT valid_gate_type CHECK (gate_type IN ('pre_commit', 'pre_merge', 'pre_deploy', 'post_deploy'))
);

-- Quality Gate Executions Table
CREATE TABLE IF NOT EXISTS quality_gate_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quality_gate_id UUID NOT NULL REFERENCES quality_gates(id),
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    execution_context JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    result JSONB DEFAULT '{}',
    score NUMERIC(5,2),
    passed BOOLEAN,
    bypass_reason TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10,3),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_gate_status CHECK (status IN ('pending', 'running', 'passed', 'failed', 'bypassed')),
    CONSTRAINT valid_score CHECK (score >= 0 AND score <= 100)
);

-- CI/CD Integrations Table
CREATE TABLE IF NOT EXISTS cicd_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(100) NOT NULL, -- github, gitlab, jenkins, azure_devops, circleci
    configuration JSONB NOT NULL,
    credentials_encrypted TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_platform CHECK (platform IN ('github', 'gitlab', 'jenkins', 'azure_devops', 'circleci')),
    CONSTRAINT valid_sync_status CHECK (sync_status IN ('pending', 'syncing', 'success', 'failed'))
);

-- Pipeline Executions Table
CREATE TABLE IF NOT EXISTS pipeline_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cicd_integration_id UUID NOT NULL REFERENCES cicd_integrations(id),
    external_id VARCHAR(255) NOT NULL, -- ID from external system
    pipeline_name VARCHAR(255) NOT NULL,
    branch VARCHAR(255),
    commit_sha VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10,3),
    trigger_event VARCHAR(100),
    triggered_by VARCHAR(255),
    pipeline_data JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_external_pipeline UNIQUE (cicd_integration_id, external_id),
    CONSTRAINT valid_pipeline_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled'))
);

-- Risk Assessments Table
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_type VARCHAR(100) NOT NULL, -- deployment, code_change, infrastructure
    target_identifier VARCHAR(255) NOT NULL, -- workflow_id, commit_sha, etc.
    risk_score NUMERIC(5,2) NOT NULL,
    risk_level VARCHAR(50) NOT NULL, -- low, medium, high, critical
    factors JSONB NOT NULL, -- risk factors and their weights
    recommendations JSONB DEFAULT '[]',
    mitigation_strategies JSONB DEFAULT '[]',
    confidence_score NUMERIC(5,2),
    model_version VARCHAR(50),
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_risk_score CHECK (risk_score >= 0 AND risk_score <= 100),
    CONSTRAINT valid_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT valid_confidence CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100))
);

-- Deployment Tracking Table
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id VARCHAR(255) UNIQUE NOT NULL,
    application_name VARCHAR(255) NOT NULL,
    version VARCHAR(255) NOT NULL,
    environment VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    deployment_strategy VARCHAR(100), -- blue_green, rolling, canary
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10,3),
    deployed_by VARCHAR(255),
    commit_sha VARCHAR(255),
    pipeline_execution_id UUID REFERENCES pipeline_executions(id),
    risk_assessment_id UUID REFERENCES risk_assessments(id),
    rollback_deployment_id UUID REFERENCES deployments(id),
    deployment_data JSONB DEFAULT '{}',
    health_checks JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_deployment_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'rolled_back')),
    CONSTRAINT valid_strategy CHECK (deployment_strategy IS NULL OR deployment_strategy IN ('blue_green', 'rolling', 'canary'))
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_type VARCHAR(100) NOT NULL, -- workflow, alert, digest
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'info',
    target_platforms JSONB NOT NULL, -- platforms to send to
    sent_platforms JSONB DEFAULT '{}', -- platforms successfully sent to
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_notification_type CHECK (notification_type IN ('workflow', 'alert', 'digest', 'system')),
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'error', 'warning', 'info', 'success')),
    CONSTRAINT valid_notification_status CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'cancelled'))
);

-- Analytics Aggregations Table
CREATE TABLE IF NOT EXISTS analytics_aggregations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregation_type VARCHAR(100) NOT NULL, -- hourly, daily, weekly, monthly
    metric_category VARCHAR(100) NOT NULL, -- workflow, cicd, infrastructure, quality
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
    aggregated_data JSONB NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_aggregation UNIQUE (aggregation_type, metric_category, time_bucket),
    CONSTRAINT valid_aggregation_type CHECK (aggregation_type IN ('hourly', 'daily', 'weekly', 'monthly')),
    CONSTRAINT valid_record_count CHECK (record_count >= 0)
);

-- System Configuration Table
CREATE TABLE IF NOT EXISTS system_configuration (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(255)
);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL, -- workflow, quality_gate, integration, etc.
    entity_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL, -- create, update, delete, execute
    actor VARCHAR(255) NOT NULL, -- user or system identifier
    changes JSONB, -- before/after for updates
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Create Indexes for Performance

-- Workflow Executions Indexes
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_started_at ON workflow_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_definition_id ON workflow_executions(workflow_definition_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_triggered_by ON workflow_executions(triggered_by);

-- Workflow Stage Results Indexes
CREATE INDEX IF NOT EXISTS idx_stage_results_execution_id ON workflow_stage_results(workflow_execution_id);
CREATE INDEX IF NOT EXISTS idx_stage_results_status ON workflow_stage_results(status);
CREATE INDEX IF NOT EXISTS idx_stage_results_stage_type ON workflow_stage_results(stage_type);

-- DevOps Metrics Indexes
CREATE INDEX IF NOT EXISTS idx_devops_metrics_timestamp ON devops_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_devops_metrics_type_source ON devops_metrics(metric_type, source_name);
CREATE INDEX IF NOT EXISTS idx_devops_metrics_source_type ON devops_metrics(source_type);
CREATE INDEX IF NOT EXISTS idx_devops_metrics_dimensions ON devops_metrics USING GIN(dimensions);
CREATE INDEX IF NOT EXISTS idx_devops_metrics_tags ON devops_metrics USING GIN(tags);

-- Quality Gate Executions Indexes
CREATE INDEX IF NOT EXISTS idx_quality_gate_executions_gate_id ON quality_gate_executions(quality_gate_id);
CREATE INDEX IF NOT EXISTS idx_quality_gate_executions_workflow_id ON quality_gate_executions(workflow_execution_id);
CREATE INDEX IF NOT EXISTS idx_quality_gate_executions_status ON quality_gate_executions(status);
CREATE INDEX IF NOT EXISTS idx_quality_gate_executions_started_at ON quality_gate_executions(started_at);

-- Pipeline Executions Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_integration_id ON pipeline_executions(cicd_integration_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_status ON pipeline_executions(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_started_at ON pipeline_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_branch ON pipeline_executions(branch);

-- Risk Assessments Indexes
CREATE INDEX IF NOT EXISTS idx_risk_assessments_type_target ON risk_assessments(assessment_type, target_identifier);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_level ON risk_assessments(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_assessed_at ON risk_assessments(assessed_at);

-- Deployments Indexes
CREATE INDEX IF NOT EXISTS idx_deployments_app_env ON deployments(application_name, environment);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_deployments_started_at ON deployments(started_at);
CREATE INDEX IF NOT EXISTS idx_deployments_pipeline_id ON deployments(pipeline_execution_id);

-- Notifications Indexes
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- Analytics Aggregations Indexes
CREATE INDEX IF NOT EXISTS idx_analytics_aggregations_type_category ON analytics_aggregations(aggregation_type, metric_category);
CREATE INDEX IF NOT EXISTS idx_analytics_aggregations_time_bucket ON analytics_aggregations(time_bucket);

-- Audit Logs Indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor);

-- Create Functions for Common Operations

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_workflow_definitions_updated_at BEFORE UPDATE ON workflow_definitions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_quality_gates_updated_at BEFORE UPDATE ON quality_gates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cicd_integrations_updated_at BEFORE UPDATE ON cicd_integrations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pipeline_executions_updated_at BEFORE UPDATE ON pipeline_executions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deployments_updated_at BEFORE UPDATE ON deployments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_configuration_updated_at BEFORE UPDATE ON system_configuration FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate workflow execution duration
CREATE OR REPLACE FUNCTION calculate_workflow_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for duration calculation
CREATE TRIGGER calculate_workflow_execution_duration BEFORE INSERT OR UPDATE ON workflow_executions FOR EACH ROW EXECUTE FUNCTION calculate_workflow_duration();
CREATE TRIGGER calculate_stage_result_duration BEFORE INSERT OR UPDATE ON workflow_stage_results FOR EACH ROW EXECUTE FUNCTION calculate_workflow_duration();
CREATE TRIGGER calculate_quality_gate_duration BEFORE INSERT OR UPDATE ON quality_gate_executions FOR EACH ROW EXECUTE FUNCTION calculate_workflow_duration();
CREATE TRIGGER calculate_pipeline_duration BEFORE INSERT OR UPDATE ON pipeline_executions FOR EACH ROW EXECUTE FUNCTION calculate_workflow_duration();
CREATE TRIGGER calculate_deployment_duration BEFORE INSERT OR UPDATE ON deployments FOR EACH ROW EXECUTE FUNCTION calculate_workflow_duration();

-- Views for Common Queries

-- Active Workflows View
CREATE OR REPLACE VIEW active_workflows AS
SELECT 
    we.id,
    we.execution_id,
    wd.name as workflow_name,
    wd.version,
    we.status,
    we.started_at,
    we.duration_seconds,
    we.triggered_by,
    we.environment,
    COUNT(wsr.id) as total_stages,
    COUNT(CASE WHEN wsr.status = 'completed' THEN 1 END) as completed_stages,
    COUNT(CASE WHEN wsr.status = 'failed' THEN 1 END) as failed_stages
FROM workflow_executions we
JOIN workflow_definitions wd ON we.workflow_definition_id = wd.id
LEFT JOIN workflow_stage_results wsr ON we.id = wsr.workflow_execution_id
WHERE we.status IN ('pending', 'running')
GROUP BY we.id, wd.name, wd.version;

-- Workflow Performance Summary View
CREATE OR REPLACE VIEW workflow_performance_summary AS
SELECT 
    wd.name as workflow_name,
    wd.version,
    COUNT(we.id) as total_executions,
    COUNT(CASE WHEN we.status = 'completed' THEN 1 END) as successful_executions,
    COUNT(CASE WHEN we.status = 'failed' THEN 1 END) as failed_executions,
    ROUND(AVG(we.duration_seconds), 2) as avg_duration_seconds,
    ROUND(MIN(we.duration_seconds), 2) as min_duration_seconds,
    ROUND(MAX(we.duration_seconds), 2) as max_duration_seconds,
    ROUND(
        COUNT(CASE WHEN we.status = 'completed' THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(we.id), 0) * 100, 2
    ) as success_rate_percent
FROM workflow_definitions wd
LEFT JOIN workflow_executions we ON wd.id = we.workflow_definition_id
WHERE wd.is_active = true
GROUP BY wd.id, wd.name, wd.version;

-- Recent Metrics View
CREATE OR REPLACE VIEW recent_metrics AS
SELECT 
    metric_type,
    metric_name,
    source_type,
    source_name,
    timestamp,
    value,
    string_value,
    dimensions,
    tags
FROM devops_metrics
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Insert Initial Configuration
INSERT INTO system_configuration (config_key, config_value, description) VALUES
('workflow_retention_days', '30', 'Number of days to retain completed workflow executions'),
('metrics_retention_days', '90', 'Number of days to retain metrics data'),
('max_concurrent_workflows', '10', 'Maximum number of concurrent workflow executions'),
('notification_retry_attempts', '3', 'Maximum number of notification retry attempts'),
('quality_gate_timeout_seconds', '300', 'Default timeout for quality gate executions')
ON CONFLICT (config_key) DO NOTHING;