"""
Phase 1, Task 1.1 Tests

Tests for DevOps module structure and base interfaces implementation.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDevOpsModuleStructure:
    """Test DevOps module structure and base interfaces"""
    
    def test_devops_module_exists(self):
        """Test that the DevOps module exists"""
        try:
            import kirolinter.devops
            assert True
        except ImportError:
            pytest.fail("DevOps module not found")
    
    def test_orchestration_module_exists(self):
        """Test that orchestration module exists"""
        try:
            from kirolinter.devops.orchestration import WorkflowEngine, PipelineManager, QualityGateSystem
            assert WorkflowEngine is not None
            assert PipelineManager is not None
            assert QualityGateSystem is not None
        except ImportError as e:
            pytest.fail(f"Orchestration module import failed: {e}")
    
    def test_models_module_exists(self):
        """Test that models module exists"""
        try:
            from kirolinter.devops.models import (
                WorkflowDefinition, PipelineIntegration, DeploymentPlan, QualityMetrics
            )
            assert WorkflowDefinition is not None
            assert PipelineIntegration is not None
            assert DeploymentPlan is not None
            assert QualityMetrics is not None
        except ImportError as e:
            pytest.fail(f"Models module import failed: {e}")
    
    def test_integrations_module_exists(self):
        """Test that integrations module exists"""
        try:
            from kirolinter.devops.integrations import BaseCICDConnector, CICDConnectorFactory
            assert BaseCICDConnector is not None
            assert CICDConnectorFactory is not None
        except ImportError as e:
            pytest.fail(f"Integrations module import failed: {e}")
    
    def test_intelligence_module_exists(self):
        """Test that intelligence module exists"""
        try:
            from kirolinter.devops.intelligence import RiskAssessmentEngine, QualityPredictor
            assert RiskAssessmentEngine is not None
            assert QualityPredictor is not None
        except ImportError as e:
            pytest.fail(f"Intelligence module import failed: {e}")
    
    def test_analytics_module_exists(self):
        """Test that analytics module exists"""
        try:
            from kirolinter.devops.analytics import MetricsCollector
            assert MetricsCollector is not None
        except ImportError as e:
            pytest.fail(f"Analytics module import failed: {e}")
    
    def test_communication_module_exists(self):
        """Test that communication module exists"""
        try:
            from kirolinter.devops.communication import NotificationHub
            assert NotificationHub is not None
        except ImportError as e:
            pytest.fail(f"Communication module import failed: {e}")
    
    def test_api_module_exists(self):
        """Test that API module exists"""
        try:
            from kirolinter.api import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"API module import failed: {e}")


class TestDataModels:
    """Test data model functionality"""
    
    def test_workflow_definition_creation(self):
        """Test WorkflowDefinition model creation"""
        from kirolinter.devops.models.workflow import WorkflowDefinition, WorkflowStage, StageType
        
        stage = WorkflowStage(
            id="test-stage",
            name="Test Stage",
            type=StageType.ANALYSIS
        )
        
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="Test workflow description",
            stages=[stage]
        )
        
        assert workflow.id == "test-workflow"
        assert workflow.name == "Test Workflow"
        assert len(workflow.stages) == 1
        assert workflow.stages[0].name == "Test Stage"
    
    def test_pipeline_integration_creation(self):
        """Test PipelineIntegration model creation"""
        from kirolinter.devops.models.pipeline import (
            PipelineIntegration, PipelineConfig, PlatformType, IntegrationStatus
        )
        
        config = PipelineConfig(
            platform=PlatformType.GITHUB_ACTIONS,
            repository_url="https://github.com/test/repo"
        )
        
        integration = PipelineIntegration(
            id="test-integration",
            name="Test Integration",
            platform=PlatformType.GITHUB_ACTIONS,
            configuration=config,
            status=IntegrationStatus.ACTIVE
        )
        
        assert integration.id == "test-integration"
        assert integration.platform == PlatformType.GITHUB_ACTIONS
        assert integration.status == IntegrationStatus.ACTIVE
        assert integration.configuration.repository_url == "https://github.com/test/repo"


class TestCoreComponents:
    """Test core component initialization"""
    
    def test_workflow_engine_initialization(self):
        """Test WorkflowEngine initialization"""
        from kirolinter.devops.orchestration.workflow_engine import WorkflowEngine
        
        engine = WorkflowEngine()
        assert engine is not None
        assert engine.active_executions == {}
        assert engine.execution_tasks == {}
    
    def test_pipeline_manager_initialization(self):
        """Test PipelineManager initialization"""
        from kirolinter.devops.orchestration.pipeline_manager import PipelineManager
        
        manager = PipelineManager()
        assert manager is not None
        assert manager.integrations == {}
        assert manager.connectors == {}
    
    def test_quality_gate_system_initialization(self):
        """Test QualityGateSystem initialization"""
        from kirolinter.devops.orchestration.quality_gates import QualityGateSystem
        
        system = QualityGateSystem()
        assert system is not None
        assert system.gate_configs is not None
        assert system.criteria_templates == {}
    
    def test_risk_assessment_engine_initialization(self):
        """Test RiskAssessmentEngine initialization"""
        from kirolinter.devops.intelligence.risk_assessor import RiskAssessmentEngine
        
        engine = RiskAssessmentEngine()
        assert engine is not None
        assert engine.risk_thresholds is not None
        assert engine.factor_weights is not None
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization"""
        from kirolinter.devops.analytics.metrics_collector import MetricsCollector
        
        collector = MetricsCollector()
        assert collector is not None
        assert collector.metric_sources == {}
        assert collector.active_collectors == {}
    
    def test_notification_hub_initialization(self):
        """Test NotificationHub initialization"""
        from kirolinter.devops.communication.notification_hub import NotificationHub
        
        hub = NotificationHub()
        assert hub is not None
        assert hub.templates is not None
        assert hub.rules == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])