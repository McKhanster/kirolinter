"""
Tests for Advanced Pipeline Analytics and Optimization Engine
"""

import asyncio
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from kirolinter.devops.analytics.pipeline_analyzer import (
    PipelineAnalyzer,
    OptimizationEngine,
    PipelinePredictor,
    OptimizationType,
    PredictionType,
    BottleneckInfo,
    OptimizationRecommendation,
    PredictionResult
)
from kirolinter.devops.orchestration.universal_pipeline_manager import UniversalPipelineManager


class TestPipelineAnalyzer:
    """Test suite for PipelineAnalyzer."""

    @pytest.fixture
    def mock_pipeline_manager(self):
        """Create mock universal pipeline manager."""
        manager = Mock(spec=UniversalPipelineManager)
        manager.pipeline_registry = Mock()
        return manager

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        return redis_mock

    @pytest.fixture
    def analyzer(self, mock_pipeline_manager, mock_redis):
        """Create PipelineAnalyzer instance."""
        return PipelineAnalyzer(mock_pipeline_manager, mock_redis)

    @pytest.fixture
    def sample_executions(self):
        """Create sample pipeline execution data."""
        executions = []
        base_date = datetime.now()
        
        for i in range(20):
            execution_date = base_date - timedelta(days=i)
            duration = 300 + np.random.normal(0, 60)  # ~5 minutes ± 1 minute
            status = "failed" if i % 10 == 0 else "success"  # 10% failure rate
            
            execution = {
                "id": f"exec_{i}",
                "date": execution_date.isoformat(),
                "duration": max(60, duration),
                "status": status,
                "stages": [
                    {"name": "build", "duration": duration * 0.3},
                    {"name": "test", "duration": duration * 0.4},
                    {"name": "deploy", "duration": duration * 0.3}
                ],
                "resource_usage": {
                    "cpu_seconds": duration * np.random.uniform(0.5, 1.5),
                    "memory_mb": np.random.uniform(512, 2048)
                }
            }
            executions.append(execution)
        
        return executions

    @pytest.mark.asyncio
    async def test_analyze_pipeline_performance(self, analyzer, sample_executions):
        """Test pipeline performance analysis."""
        with patch.object(analyzer, '_get_pipeline_history', return_value=sample_executions):
            result = await analyzer.analyze_pipeline_performance("github_actions", "test_pipeline", 30)
            
            assert "pipeline_id" in result
            assert "platform" in result
            assert "performance_metrics" in result
            assert "bottlenecks" in result
            assert "trends" in result
            assert "reliability" in result
            
            # Check performance metrics
            metrics = result["performance_metrics"]
            assert "average_duration" in metrics
            assert "success_rate" in metrics
            assert "failure_rate" in metrics
            assert metrics["success_rate"] + metrics["failure_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_analyze_pipeline_performance_no_data(self, analyzer):
        """Test pipeline performance analysis with no data."""
        with patch.object(analyzer, '_get_pipeline_history', return_value=[]):
            result = await analyzer.analyze_pipeline_performance("github_actions", "test_pipeline", 30)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_identify_bottlenecks(self, analyzer, sample_executions):
        """Test bottleneck identification."""
        with patch.object(analyzer, '_get_pipeline_history', return_value=sample_executions):
            bottlenecks = await analyzer.identify_bottlenecks("github_actions", "test_pipeline")
            
            assert isinstance(bottlenecks, list)
            assert len(bottlenecks) > 0
            
            # Check bottleneck structure
            for bottleneck in bottlenecks:
                assert isinstance(bottleneck, BottleneckInfo)
                assert bottleneck.stage_name in ["build", "test", "deploy"]
                assert bottleneck.average_duration > 0
                assert 0 <= bottleneck.optimization_potential <= 1.0
                assert isinstance(bottleneck.recommendations, list)

    @pytest.mark.asyncio
    async def test_generate_optimization_recommendations(self, analyzer, sample_executions):
        """Test optimization recommendation generation."""
        # Mock performance analysis
        mock_performance = {
            "performance_metrics": {
                "average_duration": 800,  # Long duration to trigger recommendations
                "failure_rate": 0.15  # High failure rate
            },
            "bottlenecks": [
                BottleneckInfo(
                    stage_name="test",
                    average_duration=300,
                    impact_score=100,
                    optimization_potential=0.3,
                    recommendations=["Add test parallelization"]
                )
            ],
            "resource_utilization": {
                "cpu_efficiency": 0.5  # Low efficiency
            }
        }
        
        with patch.object(analyzer, 'analyze_pipeline_performance', return_value=mock_performance):
            with patch.object(analyzer, '_find_parallelizable_stages', return_value=["test", "deploy"]):
                recommendations = await analyzer.generate_optimization_recommendations(
                    "github_actions", "test_pipeline"
                )
                
                assert isinstance(recommendations, list)
                assert len(recommendations) > 0
                
                # Check recommendation structure
                for rec in recommendations:
                    assert isinstance(rec, OptimizationRecommendation)
                    assert isinstance(rec.type, OptimizationType)
                    assert 1 <= rec.priority <= 5
                    assert rec.expected_improvement > 0
                    assert rec.implementation_effort in ["low", "medium", "high"]
                
                # Should be sorted by priority
                priorities = [rec.priority for rec in recommendations]
                assert priorities == sorted(priorities, reverse=True)

    @pytest.mark.asyncio
    async def test_predict_pipeline_failure(self, analyzer):
        """Test pipeline failure prediction."""
        with patch.object(analyzer, '_ensure_models_trained'):
            with patch.object(analyzer, '_extract_prediction_features', return_value=[1, 2, 3, 4, 5, 6, 7, 8, 9]):
                # Mock trained model
                analyzer.failure_model = Mock()
                analyzer.failure_model.predict_proba.return_value = [[0.3, 0.7]]  # 70% failure probability
                analyzer.failure_model.feature_importances_ = [0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.05, 0.05, 0.1]
                analyzer.scaler = Mock()
                analyzer.scaler.transform.return_value = [[1, 2, 3, 4, 5, 6, 7, 8, 9]]
                
                with patch.object(analyzer, '_identify_contributing_factors', return_value=["high_failure_rate"]):
                    result = await analyzer.predict_pipeline_failure("github_actions", "test_pipeline")
                    
                    assert isinstance(result, PredictionResult)
                    assert result.prediction_type == PredictionType.FAILURE
                    assert result.predicted_value is True  # 70% > 50%
                    assert result.confidence > 0
                    assert isinstance(result.contributing_factors, list)

    @pytest.mark.asyncio
    async def test_predict_pipeline_failure_no_model(self, analyzer):
        """Test pipeline failure prediction without trained model."""
        with patch.object(analyzer, '_ensure_models_trained'):
            analyzer.failure_model = None
            
            result = await analyzer.predict_pipeline_failure("github_actions", "test_pipeline")
            
            assert isinstance(result, PredictionResult)
            assert result.prediction_type == PredictionType.FAILURE
            assert result.confidence == 0.0
            assert result.predicted_value is False

    @pytest.mark.asyncio
    async def test_predict_execution_duration(self, analyzer):
        """Test execution duration prediction."""
        with patch.object(analyzer, '_ensure_models_trained'):
            with patch.object(analyzer, '_extract_prediction_features', return_value=[1, 2, 3, 4, 5, 6, 7, 8, 9]):
                with patch.object(analyzer, '_get_historical_durations', return_value=[300, 320, 290, 310]):
                    # Mock trained model
                    analyzer.duration_model = Mock()
                    analyzer.duration_model.predict.return_value = [305]  # Predicted duration
                    analyzer.scaler = Mock()
                    analyzer.scaler.transform.return_value = [[1, 2, 3, 4, 5, 6, 7, 8, 9]]
                    
                    with patch.object(analyzer, '_identify_duration_factors', return_value=["consistent_performance"]):
                        result = await analyzer.predict_execution_duration("github_actions", "test_pipeline")
                        
                        assert isinstance(result, PredictionResult)
                        assert result.prediction_type == PredictionType.DURATION
                        assert result.predicted_value == 305
                        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_predict_execution_duration_fallback(self, analyzer):
        """Test execution duration prediction fallback to historical average."""
        with patch.object(analyzer, '_ensure_models_trained'):
            analyzer.duration_model = None
            
            with patch.object(analyzer, '_get_historical_durations', return_value=[300, 320, 290, 310]):
                result = await analyzer.predict_execution_duration("github_actions", "test_pipeline")
                
                assert isinstance(result, PredictionResult)
                assert result.prediction_type == PredictionType.DURATION
                assert result.predicted_value == 305  # Average of [300, 320, 290, 310]
                assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_analyze_cross_platform_performance(self, analyzer):
        """Test cross-platform performance analysis."""
        pipeline_configs = {
            "github_actions": "pipeline_1",
            "gitlab_ci": "pipeline_2"
        }
        
        mock_github_analysis = {
            "performance_metrics": {
                "average_duration": 300,
                "success_rate": 0.95
            }
        }
        
        mock_gitlab_analysis = {
            "performance_metrics": {
                "average_duration": 250,
                "success_rate": 0.92
            }
        }
        
        async def mock_analyze(platform, pipeline_id, days):
            if platform == "github_actions":
                return mock_github_analysis
            else:
                return mock_gitlab_analysis
        
        with patch.object(analyzer, 'analyze_pipeline_performance', side_effect=mock_analyze):
            result = await analyzer.analyze_cross_platform_performance(pipeline_configs)
            
            assert "platform_comparison" in result
            assert "best_performers" in result
            assert "optimization_opportunities" in result
            
            # Check comparison structure
            comparison = result["platform_comparison"]
            assert "average_duration" in comparison
            assert "success_rate" in comparison

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, analyzer, sample_executions):
        """Test performance metrics calculation."""
        metrics = await analyzer._calculate_performance_metrics(sample_executions)
        
        assert "average_duration" in metrics
        assert "median_duration" in metrics
        assert "success_rate" in metrics
        assert "failure_rate" in metrics
        assert "throughput_per_day" in metrics
        
        # Validate ranges
        assert 0 <= metrics["success_rate"] <= 1
        assert 0 <= metrics["failure_rate"] <= 1
        assert metrics["success_rate"] + metrics["failure_rate"] == 1.0
        assert metrics["average_duration"] > 0
        assert metrics["throughput_per_day"] > 0

    @pytest.mark.asyncio
    async def test_identify_bottlenecks_analysis(self, analyzer, sample_executions):
        """Test detailed bottleneck analysis."""
        bottlenecks = await analyzer._identify_bottlenecks(sample_executions)
        
        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) == 3  # build, test, deploy stages
        
        # Check each bottleneck
        for bottleneck in bottlenecks:
            assert isinstance(bottleneck, BottleneckInfo)
            assert bottleneck.average_duration > 0
            assert bottleneck.impact_score > 0
            assert 0 <= bottleneck.optimization_potential <= 1.0
        
        # Should be sorted by impact score
        impact_scores = [b.impact_score for b in bottlenecks]
        assert impact_scores == sorted(impact_scores, reverse=True)

    @pytest.mark.asyncio
    async def test_analyze_trends(self, analyzer):
        """Test trend analysis."""
        # Create executions with improving trend
        executions = []
        base_date = datetime.now()
        
        for i in range(20):
            duration = 400 - i * 5  # Improving trend (decreasing duration)
            execution = {
                "date": (base_date - timedelta(days=i)).isoformat(),
                "duration": duration
            }
            executions.append(execution)
        
        trends = await analyzer._analyze_trends(executions)
        
        assert "trend" in trends
        assert trends["trend"] in ["improving", "degrading", "stable"]
        assert "slope_seconds_per_execution" in trends
        assert "trend_confidence" in trends
        assert 0 <= trends["trend_confidence"] <= 1

    @pytest.mark.asyncio
    async def test_analyze_trends_insufficient_data(self, analyzer):
        """Test trend analysis with insufficient data."""
        executions = [{"date": datetime.now().isoformat(), "duration": 300}]
        
        trends = await analyzer._analyze_trends(executions)
        
        assert trends["trend"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_calculate_reliability_metrics(self, analyzer, sample_executions):
        """Test reliability metrics calculation."""
        reliability = await analyzer._calculate_reliability_metrics(sample_executions)
        
        assert "mttr_seconds" in reliability
        assert "mtbf_seconds" in reliability
        assert "failure_frequency" in reliability
        assert "consecutive_failures_max" in reliability
        
        assert reliability["mttr_seconds"] >= 0
        assert reliability["mtbf_seconds"] >= 0
        assert reliability["failure_frequency"] >= 0
        assert reliability["consecutive_failures_max"] >= 0

    @pytest.mark.asyncio
    async def test_analyze_resource_usage(self, analyzer, sample_executions):
        """Test resource usage analysis."""
        resource_analysis = await analyzer._analyze_resource_usage(sample_executions)
        
        assert "cpu_efficiency" in resource_analysis
        assert "average_memory_mb" in resource_analysis
        assert "peak_memory_mb" in resource_analysis
        assert "resource_consistency" in resource_analysis
        
        assert resource_analysis["cpu_efficiency"] >= 0
        assert resource_analysis["average_memory_mb"] >= 0
        assert resource_analysis["peak_memory_mb"] >= resource_analysis["average_memory_mb"]
        assert 0 <= resource_analysis["resource_consistency"] <= 1

    @pytest.mark.asyncio
    async def test_train_models(self, analyzer):
        """Test ML model training."""
        # Mock sufficient training data
        mock_executions = []
        for i in range(50):  # Sufficient data for training
            execution = {
                "duration": 300 + i,
                "status": "success" if i % 5 != 0 else "failed",
                "date": datetime.now().isoformat(),
                "stages": [{"name": "test", "duration": 100}],
                "resource_usage": {"cpu_seconds": 200, "memory_mb": 1000}
            }
            mock_executions.append(execution)
        
        with patch.object(analyzer, '_get_pipeline_history', return_value=mock_executions):
            await analyzer._train_models()
            
            # Check that models were created
            assert analyzer.failure_model is not None
            assert analyzer.duration_model is not None
            assert analyzer.scaler is not None

    @pytest.mark.asyncio
    async def test_extract_prediction_features(self, analyzer, sample_executions):
        """Test prediction feature extraction."""
        with patch.object(analyzer, '_get_pipeline_history', return_value=sample_executions):
            features = await analyzer._extract_prediction_features(
                "github_actions", "test_pipeline", {"changed_files": ["file1.py"], "commit_size": 100}
            )
            
            assert features is not None
            assert isinstance(features, list)
            assert len(features) == 9  # Expected number of features

    @pytest.mark.asyncio
    async def test_caching_mechanism(self, analyzer, mock_redis):
        """Test analysis caching mechanism."""
        cache_key = "test_cache_key"
        test_data = {"test": "data"}
        
        # Test cache miss
        result = await analyzer._get_cached_analysis(cache_key)
        assert result is None
        
        # Test cache set
        await analyzer._cache_analysis(cache_key, test_data)
        
        # Test cache hit
        result = await analyzer._get_cached_analysis(cache_key)
        assert result == test_data


class TestOptimizationEngine:
    """Test suite for OptimizationEngine."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock pipeline analyzer."""
        analyzer = Mock(spec=PipelineAnalyzer)
        return analyzer

    @pytest.fixture
    def optimization_engine(self, mock_analyzer):
        """Create OptimizationEngine instance."""
        return OptimizationEngine(mock_analyzer)

    @pytest.mark.asyncio
    async def test_optimize_pipeline_automatically(self, optimization_engine, mock_analyzer):
        """Test automatic pipeline optimization."""
        # Mock recommendations
        mock_recommendations = [
            OptimizationRecommendation(
                type=OptimizationType.PERFORMANCE,
                priority=5,
                description="Enable parallel execution",
                expected_improvement=0.3,
                implementation_effort="low",
                technical_details={}
            ),
            OptimizationRecommendation(
                type=OptimizationType.COST,
                priority=3,
                description="Right-size resources",
                expected_improvement=0.15,
                implementation_effort="high",  # Won't be applied
                technical_details={}
            )
        ]
        
        mock_analyzer.generate_optimization_recommendations.return_value = mock_recommendations
        
        result = await optimization_engine.optimize_pipeline_automatically(
            "github_actions", "test_pipeline", [OptimizationType.PERFORMANCE]
        )
        
        assert "total_recommendations" in result
        assert "applied_optimizations" in result
        assert result["total_recommendations"] == 2
        assert len(result["applied_optimizations"]) == 1  # Only low-effort optimization applied

    @pytest.mark.asyncio
    async def test_optimize_pipeline_no_recommendations(self, optimization_engine, mock_analyzer):
        """Test optimization with no recommendations."""
        mock_analyzer.generate_optimization_recommendations.return_value = []
        
        result = await optimization_engine.optimize_pipeline_automatically(
            "github_actions", "test_pipeline"
        )
        
        assert result["total_recommendations"] == 0
        assert len(result["applied_optimizations"]) == 0

    @pytest.mark.asyncio
    async def test_apply_optimization_success(self, optimization_engine):
        """Test successful optimization application."""
        recommendation = OptimizationRecommendation(
            type=OptimizationType.PERFORMANCE,
            priority=5,
            description="Test optimization",
            expected_improvement=0.2,
            implementation_effort="low",
            technical_details={}
        )
        
        result = await optimization_engine._apply_optimization(
            "github_actions", "test_pipeline", recommendation
        )
        
        assert result["success"] is True
        assert result["optimization_type"] == OptimizationType.PERFORMANCE.value
        assert "actual_improvement" in result
        assert "applied_at" in result


class TestPipelinePredictor:
    """Test suite for PipelinePredictor."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock pipeline analyzer."""
        analyzer = Mock(spec=PipelineAnalyzer)
        return analyzer

    @pytest.fixture
    def predictor(self, mock_analyzer):
        """Create PipelinePredictor instance."""
        return PipelinePredictor(mock_analyzer)

    @pytest.fixture
    def sample_executions_with_dates(self):
        """Create sample executions with proper date grouping."""
        executions = []
        base_date = datetime.now()
        
        for i in range(30):
            execution_date = base_date - timedelta(days=i)
            execution = {
                "date": execution_date.isoformat(),
                "resource_usage": {
                    "cpu_seconds": 200 + i * 5,
                    "memory_mb": 1000 + i * 10
                }
            }
            executions.append(execution)
        
        return executions

    @pytest.mark.asyncio
    async def test_predict_resource_demand(self, predictor, mock_analyzer, sample_executions_with_dates):
        """Test resource demand prediction."""
        mock_analyzer._get_pipeline_history.return_value = sample_executions_with_dates
        
        result = await predictor.predict_resource_demand("github_actions", "test_pipeline", 7)
        
        assert "platform" in result
        assert "pipeline_id" in result
        assert "forecast_days" in result
        assert "predictions" in result
        assert "confidence" in result
        
        # Check predictions structure
        predictions = result["predictions"]
        assert len(predictions) == 7  # 7 days forecast
        
        for prediction in predictions.values():
            assert "predicted_cpu_seconds" in prediction
            assert "predicted_memory_mb" in prediction
            assert "predicted_executions" in prediction
            assert prediction["predicted_cpu_seconds"] >= 0
            assert prediction["predicted_memory_mb"] >= 0
            assert prediction["predicted_executions"] >= 0

    @pytest.mark.asyncio
    async def test_predict_resource_demand_insufficient_data(self, predictor, mock_analyzer):
        """Test resource demand prediction with insufficient data."""
        mock_analyzer._get_pipeline_history.return_value = []
        
        result = await predictor.predict_resource_demand("github_actions", "test_pipeline", 7)
        
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_quality_impact(self, predictor, mock_analyzer):
        """Test quality impact analysis."""
        quality_metrics = {
            "code_quality": 0.8,
            "test_coverage": 0.7,
            "complexity": 0.6
        }
        
        mock_performance = {
            "performance_metrics": {
                "average_duration": 300,
                "failure_rate": 0.1
            }
        }
        
        mock_analyzer.analyze_pipeline_performance.return_value = mock_performance
        
        result = await predictor.analyze_quality_impact(
            "github_actions", "test_pipeline", quality_metrics
        )
        
        assert "current_quality_score" in result
        assert "performance_correlation" in result
        assert "improvement_potential" in result
        assert "recommendations" in result
        
        # Check quality score calculation
        expected_quality_score = sum(quality_metrics.values()) / len(quality_metrics)
        assert abs(result["current_quality_score"] - expected_quality_score) < 0.01
        
        # Check correlation structure
        correlation = result["performance_correlation"]
        assert "duration_impact" in correlation
        assert "failure_rate_impact" in correlation
        assert "reliability_impact" in correlation

    @pytest.mark.asyncio
    async def test_analyze_quality_impact_high_quality(self, predictor, mock_analyzer):
        """Test quality impact analysis with high quality code."""
        quality_metrics = {
            "code_quality": 0.95,
            "test_coverage": 0.90,
            "complexity": 0.85
        }
        
        mock_performance = {
            "performance_metrics": {
                "average_duration": 200,
                "failure_rate": 0.02
            }
        }
        
        mock_analyzer.analyze_pipeline_performance.return_value = mock_performance
        
        result = await predictor.analyze_quality_impact(
            "github_actions", "test_pipeline", quality_metrics
        )
        
        # High quality should show minimal improvement potential
        improvement = result["improvement_potential"]
        assert improvement["duration_reduction"] < 0.1
        assert improvement["failure_rate_reduction"] < 0.1
        
        # Should recommend maintaining standards
        recommendations = result["recommendations"]
        assert any("maintain" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_quality_impact_calculations(self, predictor):
        """Test quality impact calculation methods."""
        # Test duration impact
        high_quality_impact = predictor._calculate_quality_duration_impact(0.9)
        low_quality_impact = predictor._calculate_quality_duration_impact(0.3)
        
        assert low_quality_impact > high_quality_impact
        assert high_quality_impact >= 0
        assert low_quality_impact <= 0.2  # Maximum base impact
        
        # Test failure rate impact
        high_quality_failure = predictor._calculate_quality_failure_impact(0.9)
        low_quality_failure = predictor._calculate_quality_failure_impact(0.3)
        
        assert low_quality_failure > high_quality_failure
        assert high_quality_failure >= 0
        assert low_quality_failure <= 0.3  # Maximum base impact
        
        # Test reliability impact
        high_quality_reliability = predictor._calculate_quality_reliability_impact(0.9)
        low_quality_reliability = predictor._calculate_quality_reliability_impact(0.3)
        
        assert high_quality_reliability > low_quality_reliability
        assert 0 <= high_quality_reliability <= 0.4
        assert 0 <= low_quality_reliability <= 0.4


# Integration Tests

@pytest.mark.asyncio
async def test_analyzer_optimization_integration():
    """Test integration between analyzer and optimization engine."""
    # Create mock pipeline manager
    mock_manager = Mock(spec=UniversalPipelineManager)
    mock_manager.pipeline_registry = Mock()
    
    # Create analyzer and optimization engine
    analyzer = PipelineAnalyzer(mock_manager)
    optimization_engine = OptimizationEngine(analyzer)
    
    # Mock pipeline history
    sample_executions = [
        {
            "id": "exec_1",
            "date": datetime.now().isoformat(),
            "duration": 600,  # Long duration
            "status": "failed",  # Failed execution
            "stages": [{"name": "test", "duration": 400}],
            "resource_usage": {"cpu_seconds": 300, "memory_mb": 1000}
        }
    ]
    
    with patch.object(analyzer, '_get_pipeline_history', return_value=sample_executions):
        # Get recommendations from analyzer
        recommendations = await analyzer.generate_optimization_recommendations(
            "github_actions", "test_pipeline"
        )
        
        # Apply optimizations through engine
        result = await optimization_engine.optimize_pipeline_automatically(
            "github_actions", "test_pipeline"
        )
        
        # Should have generated recommendations and applied some
        assert len(recommendations) > 0
        assert "applied_optimizations" in result


@pytest.mark.asyncio
async def test_analyzer_predictor_integration():
    """Test integration between analyzer and predictor."""
    # Create mock pipeline manager
    mock_manager = Mock(spec=UniversalPipelineManager)
    mock_manager.pipeline_registry = Mock()
    
    # Create analyzer and predictor
    analyzer = PipelineAnalyzer(mock_manager)
    predictor = PipelinePredictor(analyzer)
    
    # Test resource prediction integration
    sample_executions = [
        {
            "date": (datetime.now() - timedelta(days=i)).isoformat(),
            "resource_usage": {"cpu_seconds": 200, "memory_mb": 1000}
        } for i in range(10)
    ]
    
    with patch.object(analyzer, '_get_pipeline_history', return_value=sample_executions):
        result = await predictor.predict_resource_demand("github_actions", "test_pipeline", 3)
        
        assert "predictions" in result
        assert len(result["predictions"]) == 3


if __name__ == "__main__":
    # Run tests with asyncio support
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])