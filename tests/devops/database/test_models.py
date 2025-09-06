"""
Tests for Database Models

Comprehensive tests for Pydantic models and data validation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from pydantic import ValidationError

from kirolinter.database.models import (
    WorkflowDefinition, WorkflowExecution, WorkflowStageResult,
    DevOpsMetric, QualityGate, QualityGateExecution,
    CICDIntegration, PipelineExecution, RiskAssessment,
    Deployment, Notification, AnalyticsAggregation,
    SystemConfiguration, AuditLog,
    WorkflowStatus, StageStatus, QualityGateType, QualityGateStatus,
    CICDPlatform, PipelineStatus, RiskLevel, DeploymentStatus,
    NotificationType, NotificationSeverity, NotificationStatus,
    WorkflowExecutionRequest, MetricsQueryRequest, PaginationParams
)


class TestWorkflowModels:
    """Test cases for workflow-related models"""
    
    def test_workflow_definition_creation(self):
        """Test creating a workflow definition"""
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="A test workflow for validation",
            version="1.2.3",
            definition={"stages": ["analysis", "build", "test"]},
            metadata={"author": "test_user", "priority": "high"},
            created_by="test_user"
        )
        
        assert workflow_def.name == "Test Workflow"
        assert workflow_def.version == "1.2.3"
        assert workflow_def.definition["stages"] == ["analysis", "build", "test"]
        assert workflow_def.metadata["author"] == "test_user"
        assert workflow_def.is_active is True
        assert isinstance(workflow_def.id, UUID)
        assert isinstance(workflow_def.created_at, datetime)
    
    def test_workflow_definition_validation(self):
        """Test workflow definition validation"""
        # Test empty name validation
        with pytest.raises(ValidationError, match="Workflow name cannot be empty"):
            WorkflowDefinition(
                name="",
                definition={"stages": []}
            )
        
        # Test invalid version format
        with pytest.raises(ValidationError, match="Version must follow semantic versioning"):
            WorkflowDefinition(
                name="Test Workflow",
                version="invalid_version",
                definition={"stages": []}
            )
        
        # Test valid version formats
        valid_versions = ["1.0.0", "2.1.5", "10.20.30"]
        for version in valid_versions:
            workflow_def = WorkflowDefinition(
                name="Test Workflow",
                version=version,
                definition={"stages": []}
            )
            assert workflow_def.version == version
    
    def test_workflow_execution_creation(self):
        """Test creating a workflow execution"""
        workflow_execution = WorkflowExecution(
            workflow_definition_id=uuid4(),
            execution_id="exec_123",
            status=WorkflowStatus.RUNNING,
            triggered_by="test_user",
            environment="staging",
            input_data={"param1": "value1"},
            metadata={"priority": "high"}
        )
        
        assert workflow_execution.execution_id == "exec_123"
        assert workflow_execution.status == WorkflowStatus.RUNNING
        assert workflow_execution.environment == "staging"
        assert workflow_execution.input_data["param1"] == "value1"
        assert isinstance(workflow_execution.workflow_definition_id, UUID)
    
    def test_workflow_execution_completion_validation(self):
        """Test workflow execution completion validation"""
        # Test that completed status sets completed_at automatically
        workflow_execution = WorkflowExecution(
            workflow_definition_id=uuid4(),
            execution_id="exec_completed",
            status=WorkflowStatus.COMPLETED
        )
        
        assert workflow_execution.completed_at is not None
        assert isinstance(workflow_execution.completed_at, datetime)
    
    def test_workflow_stage_result_creation(self):
        """Test creating a workflow stage result"""
        stage_result = WorkflowStageResult(
            workflow_execution_id=uuid4(),
            stage_id="stage_1",
            stage_name="Analysis Stage",
            stage_type="analysis",
            status=StageStatus.COMPLETED,
            output_data={"issues_found": 5, "quality_score": 85},
            duration_seconds=45.5,
            retry_count=1
        )
        
        assert stage_result.stage_id == "stage_1"
        assert stage_result.stage_name == "Analysis Stage"
        assert stage_result.status == StageStatus.COMPLETED
        assert stage_result.output_data["issues_found"] == 5
        assert stage_result.duration_seconds == 45.5
        assert stage_result.retry_count == 1


class TestMetricsModels:
    """Test cases for metrics-related models"""
    
    def test_devops_metric_creation(self):
        """Test creating a DevOps metric"""
        metric = DevOpsMetric(
            metric_type="build_duration",
            metric_name="average_build_time",
            source_type="ci_cd",
            source_name="github_actions",
            timestamp=datetime.utcnow(),
            value=125.5,
            dimensions={"branch": "main", "environment": "production"},
            tags={"team": "backend", "service": "api"}
        )
        
        assert metric.metric_type == "build_duration"
        assert metric.source_type == "ci_cd"
        assert metric.source_name == "github_actions"
        assert metric.value == 125.5
        assert metric.dimensions["branch"] == "main"
        assert metric.tags["team"] == "backend"
    
    def test_devops_metric_validation(self):
        """Test DevOps metric validation"""
        # Test that either value or string_value must be provided
        with pytest.raises(ValidationError, match="Either value or string_value must be provided"):
            DevOpsMetric(
                metric_type="status",
                metric_name="build_status",
                source_type="ci_cd",
                source_name="jenkins",
                timestamp=datetime.utcnow()
                # Neither value nor string_value provided
            )
        
        # Test valid metric with string_value
        metric = DevOpsMetric(
            metric_type="status",
            metric_name="build_status",
            source_type="ci_cd",
            source_name="jenkins",
            timestamp=datetime.utcnow(),
            string_value="success"
        )
        assert metric.string_value == "success"
        assert metric.value is None


class TestQualityGateModels:
    """Test cases for quality gate models"""
    
    def test_quality_gate_creation(self):
        """Test creating a quality gate"""
        quality_gate = QualityGate(
            name="Pre-Deploy Gate",
            description="Quality gate before deployment",
            gate_type=QualityGateType.PRE_DEPLOY,
            criteria={
                "code_coverage": {"min": 80, "weight": 0.3},
                "test_pass_rate": {"min": 95, "weight": 0.4},
                "security_score": {"min": 90, "weight": 0.3}
            },
            configuration={"timeout_seconds": 300, "auto_approve": False},
            created_by="devops_team"
        )
        
        assert quality_gate.name == "Pre-Deploy Gate"
        assert quality_gate.gate_type == QualityGateType.PRE_DEPLOY
        assert quality_gate.criteria["code_coverage"]["min"] == 80
        assert quality_gate.configuration["timeout_seconds"] == 300
        assert quality_gate.is_active is True
    
    def test_quality_gate_validation(self):
        """Test quality gate validation"""
        # Test empty criteria validation
        with pytest.raises(ValidationError, match="Quality gate criteria cannot be empty"):
            QualityGate(
                name="Invalid Gate",
                gate_type=QualityGateType.PRE_COMMIT,
                criteria={}  # Empty criteria
            )
    
    def test_quality_gate_execution_creation(self):
        """Test creating a quality gate execution"""
        gate_execution = QualityGateExecution(
            quality_gate_id=uuid4(),
            workflow_execution_id=uuid4(),
            execution_context={"branch": "main", "commit_sha": "abc123"},
            status=QualityGateStatus.PASSED,
            result={
                "code_coverage": 85.5,
                "test_pass_rate": 97.2,
                "security_score": 92.0
            },
            score=91.5,
            passed=True,
            duration_seconds=45.2
        )
        
        assert gate_execution.status == QualityGateStatus.PASSED
        assert gate_execution.score == 91.5
        assert gate_execution.passed is True
        assert gate_execution.result["code_coverage"] == 85.5
        assert gate_execution.duration_seconds == 45.2


class TestCICDModels:
    """Test cases for CI/CD integration models"""
    
    def test_cicd_integration_creation(self):
        """Test creating a CI/CD integration"""
        integration = CICDIntegration(
            name="GitHub Actions Integration",
            platform=CICDPlatform.GITHUB,
            configuration={
                "repository": "org/repo",
                "webhook_url": "https://api.github.com/webhooks/123",
                "events": ["push", "pull_request"]
            },
            credentials_encrypted="encrypted_token_data",
            is_active=True
        )
        
        assert integration.name == "GitHub Actions Integration"
        assert integration.platform == CICDPlatform.GITHUB
        assert integration.configuration["repository"] == "org/repo"
        assert integration.is_active is True
        assert integration.sync_status == "pending"
    
    def test_cicd_integration_validation(self):
        """Test CI/CD integration validation"""
        # Test empty configuration validation
        with pytest.raises(ValidationError, match="Integration configuration cannot be empty"):
            CICDIntegration(
                name="Invalid Integration",
                platform=CICDPlatform.GITLAB,
                configuration={}  # Empty configuration
            )
    
    def test_pipeline_execution_creation(self):
        """Test creating a pipeline execution"""
        pipeline_execution = PipelineExecution(
            cicd_integration_id=uuid4(),
            external_id="run_123456",
            pipeline_name="CI/CD Pipeline",
            branch="feature/new-feature",
            commit_sha="abc123def456",
            status=PipelineStatus.SUCCESS,
            started_at=datetime.utcnow() - timedelta(minutes=10),
            completed_at=datetime.utcnow(),
            duration_seconds=600.0,
            trigger_event="push",
            triggered_by="developer@example.com",
            pipeline_data={"job_count": 5, "parallel_jobs": 3},
            metrics={"cpu_time": 1200, "memory_peak": 2048}
        )
        
        assert pipeline_execution.external_id == "run_123456"
        assert pipeline_execution.pipeline_name == "CI/CD Pipeline"
        assert pipeline_execution.branch == "feature/new-feature"
        assert pipeline_execution.status == PipelineStatus.SUCCESS
        assert pipeline_execution.duration_seconds == 600.0
        assert pipeline_execution.pipeline_data["job_count"] == 5


class TestRiskAssessmentModels:
    """Test cases for risk assessment models"""
    
    def test_risk_assessment_creation(self):
        """Test creating a risk assessment"""
        risk_assessment = RiskAssessment(
            assessment_type="deployment",
            target_identifier="deploy_prod_v1.2.3",
            risk_score=75.5,
            risk_level=RiskLevel.MEDIUM,
            factors={
                "code_changes": {"score": 60, "weight": 0.3},
                "test_coverage": {"score": 85, "weight": 0.2},
                "deployment_frequency": {"score": 90, "weight": 0.2},
                "rollback_capability": {"score": 95, "weight": 0.3}
            },
            recommendations=[
                {"type": "testing", "description": "Increase test coverage to 90%"},
                {"type": "monitoring", "description": "Enable enhanced monitoring"}
            ],
            mitigation_strategies=[
                {"strategy": "canary_deployment", "description": "Deploy to 10% of traffic first"}
            ],
            confidence_score=88.0,
            model_version="v2.1.0"
        )
        
        assert risk_assessment.assessment_type == "deployment"
        assert risk_assessment.risk_score == 75.5
        assert risk_assessment.risk_level == RiskLevel.MEDIUM
        assert risk_assessment.factors["code_changes"]["score"] == 60
        assert len(risk_assessment.recommendations) == 2
        assert len(risk_assessment.mitigation_strategies) == 1
        assert risk_assessment.confidence_score == 88.0
    
    def test_risk_assessment_validation(self):
        """Test risk assessment validation"""
        # Test empty factors validation
        with pytest.raises(ValidationError, match="Risk factors cannot be empty"):
            RiskAssessment(
                assessment_type="deployment",
                target_identifier="test",
                risk_score=50.0,
                risk_level=RiskLevel.LOW,
                factors={}  # Empty factors
            )


class TestDeploymentModels:
    """Test cases for deployment models"""
    
    def test_deployment_creation(self):
        """Test creating a deployment"""
        deployment = Deployment(
            deployment_id="deploy_123",
            application_name="web-api",
            version="v1.2.3",
            environment="production",
            status=DeploymentStatus.SUCCESS,
            deployment_strategy="blue_green",
            started_at=datetime.utcnow() - timedelta(minutes=15),
            completed_at=datetime.utcnow(),
            duration_seconds=900.0,
            deployed_by="devops@example.com",
            commit_sha="abc123def456",
            deployment_data={"replicas": 3, "resources": {"cpu": "500m", "memory": "1Gi"}},
            health_checks={"readiness": "passed", "liveness": "passed"},
            metrics={"response_time": 150, "error_rate": 0.01}
        )
        
        assert deployment.deployment_id == "deploy_123"
        assert deployment.application_name == "web-api"
        assert deployment.version == "v1.2.3"
        assert deployment.environment == "production"
        assert deployment.status == DeploymentStatus.SUCCESS
        assert deployment.duration_seconds == 900.0
        assert deployment.deployment_data["replicas"] == 3
    
    def test_deployment_validation(self):
        """Test deployment validation"""
        # Test empty deployment_id validation
        with pytest.raises(ValidationError, match="Deployment ID cannot be empty"):
            Deployment(
                deployment_id="",  # Empty deployment ID
                application_name="test-app",
                version="v1.0.0",
                environment="test"
            )


class TestNotificationModels:
    """Test cases for notification models"""
    
    def test_notification_creation(self):
        """Test creating a notification"""
        notification = Notification(
            notification_type=NotificationType.WORKFLOW,
            title="Workflow Completed Successfully",
            content="The deployment workflow has completed successfully in production.",
            severity=NotificationSeverity.SUCCESS,
            target_platforms={
                "slack": {"channel": "#deployments", "webhook_url": "https://hooks.slack.com/..."},
                "email": {"recipients": ["team@example.com"], "smtp_server": "smtp.example.com"}
            },
            scheduled_at=datetime.utcnow(),
            status=NotificationStatus.SENT,
            sent_at=datetime.utcnow(),
            metadata={"workflow_id": "wf_123", "environment": "production"}
        )
        
        assert notification.notification_type == NotificationType.WORKFLOW
        assert notification.title == "Workflow Completed Successfully"
        assert notification.severity == NotificationSeverity.SUCCESS
        assert "slack" in notification.target_platforms
        assert "email" in notification.target_platforms
        assert notification.status == NotificationStatus.SENT
    
    def test_notification_validation(self):
        """Test notification validation"""
        # Test empty target_platforms validation
        with pytest.raises(ValidationError, match="Target platforms cannot be empty"):
            Notification(
                notification_type=NotificationType.ALERT,
                title="Test Alert",
                content="Test content",
                target_platforms={}  # Empty target platforms
            )


class TestAnalyticsModels:
    """Test cases for analytics models"""
    
    def test_analytics_aggregation_creation(self):
        """Test creating an analytics aggregation"""
        aggregation = AnalyticsAggregation(
            aggregation_type="daily",
            metric_category="workflow",
            time_bucket=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            aggregated_data={
                "total_executions": 150,
                "successful_executions": 142,
                "failed_executions": 8,
                "average_duration": 245.5,
                "success_rate": 0.947
            },
            record_count=150
        )
        
        assert aggregation.aggregation_type == "daily"
        assert aggregation.metric_category == "workflow"
        assert aggregation.aggregated_data["total_executions"] == 150
        assert aggregation.record_count == 150
    
    def test_analytics_aggregation_validation(self):
        """Test analytics aggregation validation"""
        # Test invalid aggregation_type
        with pytest.raises(ValidationError, match="Aggregation type must be one of"):
            AnalyticsAggregation(
                aggregation_type="invalid_type",
                metric_category="workflow",
                time_bucket=datetime.utcnow(),
                aggregated_data={"count": 10},
                record_count=10
            )


class TestSystemModels:
    """Test cases for system models"""
    
    def test_system_configuration_creation(self):
        """Test creating a system configuration"""
        config = SystemConfiguration(
            config_key="workflow_retention_days",
            config_value={"value": 30, "unit": "days"},
            description="Number of days to retain completed workflow executions",
            is_encrypted=False,
            updated_by="admin@example.com"
        )
        
        assert config.config_key == "workflow_retention_days"
        assert config.config_value["value"] == 30
        assert config.description is not None
        assert config.is_encrypted is False
    
    def test_system_configuration_validation(self):
        """Test system configuration validation"""
        # Test empty config_key validation
        with pytest.raises(ValidationError, match="Configuration key cannot be empty"):
            SystemConfiguration(
                config_key="",  # Empty config key
                config_value={"value": "test"}
            )
    
    def test_audit_log_creation(self):
        """Test creating an audit log"""
        audit_log = AuditLog(
            entity_type="workflow",
            entity_id=uuid4(),
            action="execute",
            actor="user@example.com",
            changes={
                "before": {"status": "pending"},
                "after": {"status": "running"}
            },
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            metadata={"session_id": "sess_123"}
        )
        
        assert audit_log.entity_type == "workflow"
        assert audit_log.action == "execute"
        assert audit_log.actor == "user@example.com"
        assert audit_log.changes["before"]["status"] == "pending"
        assert audit_log.ip_address == "192.168.1.100"
    
    def test_audit_log_validation(self):
        """Test audit log validation"""
        # Test invalid entity_type
        with pytest.raises(ValidationError, match="Entity type must be one of"):
            AuditLog(
                entity_type="invalid_entity",
                entity_id=uuid4(),
                action="create",
                actor="user@example.com"
            )
        
        # Test invalid action
        with pytest.raises(ValidationError, match="Action must be one of"):
            AuditLog(
                entity_type="workflow",
                entity_id=uuid4(),
                action="invalid_action",
                actor="user@example.com"
            )


class TestAPIModels:
    """Test cases for API request/response models"""
    
    def test_workflow_execution_request(self):
        """Test workflow execution request model"""
        request = WorkflowExecutionRequest(
            workflow_definition_id=uuid4(),
            input_data={"param1": "value1", "param2": 42},
            environment="staging",
            triggered_by="api_user",
            metadata={"source": "api", "priority": "high"}
        )
        
        assert isinstance(request.workflow_definition_id, UUID)
        assert request.input_data["param1"] == "value1"
        assert request.environment == "staging"
        assert request.triggered_by == "api_user"
    
    def test_metrics_query_request(self):
        """Test metrics query request model"""
        request = MetricsQueryRequest(
            metric_types=["build_duration", "test_coverage"],
            source_types=["ci_cd", "quality"],
            source_names=["github_actions", "sonarqube"],
            start_time=datetime.utcnow() - timedelta(days=7),
            end_time=datetime.utcnow(),
            dimensions={"environment": "production"},
            tags={"team": "backend"},
            limit=500,
            offset=0
        )
        
        assert len(request.metric_types) == 2
        assert "build_duration" in request.metric_types
        assert request.limit == 500
        assert request.offset == 0
        assert request.dimensions["environment"] == "production"
    
    def test_pagination_params(self):
        """Test pagination parameters model"""
        pagination = PaginationParams(page=3, page_size=25)
        
        assert pagination.page == 3
        assert pagination.page_size == 25
        assert pagination.offset == 50  # (3-1) * 25
        assert pagination.limit == 25
    
    def test_pagination_params_validation(self):
        """Test pagination parameters validation"""
        # Test invalid page number
        with pytest.raises(ValidationError):
            PaginationParams(page=0)  # Page must be >= 1
        
        # Test invalid page size
        with pytest.raises(ValidationError):
            PaginationParams(page_size=0)  # Page size must be >= 1
        
        with pytest.raises(ValidationError):
            PaginationParams(page_size=2000)  # Page size must be <= 1000


class TestModelSerialization:
    """Test cases for model serialization and deserialization"""
    
    def test_workflow_definition_serialization(self):
        """Test workflow definition JSON serialization"""
        workflow_def = WorkflowDefinition(
            name="Test Workflow",
            description="Test description",
            version="1.0.0",
            definition={"stages": ["build", "test"]},
            metadata={"author": "test"}
        )
        
        # Test dict conversion
        workflow_dict = workflow_def.dict()
        assert workflow_dict["name"] == "Test Workflow"
        assert workflow_dict["version"] == "1.0.0"
        assert isinstance(workflow_dict["id"], str)  # UUID converted to string
        assert isinstance(workflow_dict["created_at"], str)  # datetime converted to ISO string
        
        # Test JSON serialization
        workflow_json = workflow_def.json()
        assert isinstance(workflow_json, str)
        assert "Test Workflow" in workflow_json
    
    def test_model_with_enums_serialization(self):
        """Test model serialization with enum values"""
        notification = Notification(
            notification_type=NotificationType.ALERT,
            title="Test Alert",
            content="Test content",
            severity=NotificationSeverity.WARNING,
            target_platforms={"slack": {"channel": "#alerts"}},
            status=NotificationStatus.PENDING
        )
        
        notification_dict = notification.dict()
        assert notification_dict["notification_type"] == "alert"
        assert notification_dict["severity"] == "warning"
        assert notification_dict["status"] == "pending"


if __name__ == "__main__":
    pytest.main([__file__])