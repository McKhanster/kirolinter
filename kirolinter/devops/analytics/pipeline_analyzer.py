"""
Advanced Pipeline Analytics and Optimization Engine

Provides AI-powered pipeline analysis, optimization recommendations, 
and predictive analytics for CI/CD workflows.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

from ..orchestration.universal_pipeline_manager import UniversalPipelineManager, PipelineRegistry
from ..integrations.cicd.base_connector import WorkflowStatus

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of pipeline optimizations."""
    PERFORMANCE = "performance"
    COST = "cost"
    RELIABILITY = "reliability"
    RESOURCE = "resource"


class PredictionType(Enum):
    """Types of pipeline predictions."""
    FAILURE = "failure"
    DURATION = "duration"
    RESOURCE_DEMAND = "resource_demand"
    QUALITY_IMPACT = "quality_impact"


@dataclass
class BottleneckInfo:
    """Information about identified pipeline bottlenecks."""
    stage_name: str
    average_duration: float
    impact_score: float
    optimization_potential: float
    recommendations: List[str]


@dataclass
class OptimizationRecommendation:
    """Pipeline optimization recommendation."""
    type: OptimizationType
    priority: int  # 1-5, 5 being highest
    description: str
    expected_improvement: float
    implementation_effort: str  # low, medium, high
    technical_details: Dict[str, Any]


@dataclass
class PredictionResult:
    """Result of a pipeline prediction."""
    prediction_type: PredictionType
    confidence: float
    predicted_value: Union[float, bool, str]
    explanation: str
    contributing_factors: List[str]


class PipelineAnalyzer:
    """
    Advanced pipeline analytics engine with ML-powered insights,
    optimization recommendations, and predictive capabilities.
    """

    def __init__(self, pipeline_manager: UniversalPipelineManager, redis_client=None):
        """Initialize the pipeline analyzer.
        
        Args:
            pipeline_manager: Universal pipeline manager instance
            redis_client: Redis client for data storage
        """
        self.pipeline_manager = pipeline_manager
        self.redis = redis_client
        self.pipeline_registry = pipeline_manager.pipeline_registry
        
        # ML Models
        self.failure_model = None
        self.duration_model = None
        self.resource_model = None
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        
        # Analytics cache
        self._analytics_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Model training data
        self._training_data = {
            'features': [],
            'failure_labels': [],
            'duration_labels': [],
            'resource_labels': []
        }

    async def analyze_pipeline_performance(self, platform: str, pipeline_id: str, 
                                         days: int = 30) -> Dict[str, Any]:
        """Analyze pipeline performance over a time period.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            days: Number of days to analyze
            
        Returns:
            Comprehensive performance analysis
        """
        cache_key = f"performance:{platform}:{pipeline_id}:{days}"
        cached = await self._get_cached_analysis(cache_key)
        if cached:
            return cached

        try:
            # Get pipeline execution history
            executions = await self._get_pipeline_history(platform, pipeline_id, days)
            
            if not executions:
                return {"error": "No execution data found"}

            analysis = {
                "pipeline_id": pipeline_id,
                "platform": platform,
                "analysis_period": f"{days} days",
                "total_executions": len(executions),
                "performance_metrics": await self._calculate_performance_metrics(executions),
                "bottlenecks": await self._identify_bottlenecks(executions),
                "trends": await self._analyze_trends(executions),
                "reliability": await self._calculate_reliability_metrics(executions),
                "resource_utilization": await self._analyze_resource_usage(executions),
                "quality_correlation": await self._analyze_quality_correlation(executions)
            }

            await self._cache_analysis(cache_key, analysis)
            return analysis

        except Exception as e:
            logger.error(f"Pipeline performance analysis failed: {e}")
            return {"error": str(e)}

    async def identify_bottlenecks(self, platform: str, pipeline_id: str) -> List[BottleneckInfo]:
        """Identify performance bottlenecks in a pipeline.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            
        Returns:
            List of identified bottlenecks with optimization potential
        """
        try:
            executions = await self._get_pipeline_history(platform, pipeline_id, 14)
            return await self._identify_bottlenecks(executions)
        except Exception as e:
            logger.error(f"Bottleneck identification failed: {e}")
            return []

    async def generate_optimization_recommendations(self, platform: str, 
                                                  pipeline_id: str) -> List[OptimizationRecommendation]:
        """Generate AI-powered optimization recommendations.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            
        Returns:
            List of optimization recommendations
        """
        try:
            # Get comprehensive pipeline analysis
            performance = await self.analyze_pipeline_performance(platform, pipeline_id)
            bottlenecks = performance.get('bottlenecks', [])
            metrics = performance.get('performance_metrics', {})
            
            recommendations = []
            
            # Performance optimizations
            if metrics.get('average_duration', 0) > 600:  # > 10 minutes
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.PERFORMANCE,
                    priority=5,
                    description="Enable parallel execution for independent stages",
                    expected_improvement=0.35,  # 35% improvement
                    implementation_effort="medium",
                    technical_details={
                        "stages_to_parallelize": await self._find_parallelizable_stages(platform, pipeline_id),
                        "expected_time_savings": metrics.get('average_duration', 0) * 0.35
                    }
                ))

            # Bottleneck-based recommendations
            for bottleneck in bottlenecks:
                if bottleneck.optimization_potential > 0.2:  # > 20% improvement potential
                    recommendations.append(OptimizationRecommendation(
                        type=OptimizationType.PERFORMANCE,
                        priority=4,
                        description=f"Optimize {bottleneck.stage_name} stage",
                        expected_improvement=bottleneck.optimization_potential,
                        implementation_effort="low" if bottleneck.optimization_potential < 0.3 else "medium",
                        technical_details={
                            "stage": bottleneck.stage_name,
                            "current_duration": bottleneck.average_duration,
                            "recommendations": bottleneck.recommendations
                        }
                    ))

            # Reliability optimizations
            failure_rate = metrics.get('failure_rate', 0)
            if failure_rate > 0.1:  # > 10% failure rate
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.RELIABILITY,
                    priority=5,
                    description="Implement retry mechanisms for flaky stages",
                    expected_improvement=failure_rate * 0.6,  # 60% failure reduction
                    implementation_effort="low",
                    technical_details={
                        "current_failure_rate": failure_rate,
                        "retry_strategy": "exponential_backoff",
                        "max_retries": 3
                    }
                ))

            # Cost optimizations
            resource_usage = performance.get('resource_utilization', {})
            if resource_usage.get('cpu_efficiency', 1.0) < 0.6:  # < 60% CPU efficiency
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.COST,
                    priority=3,
                    description="Right-size compute resources to reduce costs",
                    expected_improvement=0.25,  # 25% cost reduction
                    implementation_effort="low",
                    technical_details={
                        "current_cpu_efficiency": resource_usage.get('cpu_efficiency'),
                        "recommended_instance_size": "smaller",
                        "estimated_cost_savings": 0.25
                    }
                ))

            # Sort by priority
            recommendations.sort(key=lambda r: r.priority, reverse=True)
            return recommendations

        except Exception as e:
            logger.error(f"Optimization recommendation generation failed: {e}")
            return []

    async def predict_pipeline_failure(self, platform: str, pipeline_id: str, 
                                     context: Dict[str, Any] = None) -> PredictionResult:
        """Predict likelihood of pipeline failure.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            context: Additional context (branch, commit info, etc.)
            
        Returns:
            Failure prediction with confidence score
        """
        try:
            # Ensure model is trained
            await self._ensure_models_trained()
            
            # Extract features for prediction
            features = await self._extract_prediction_features(platform, pipeline_id, context)
            
            if self.failure_model and features:
                # Normalize features
                features_scaled = self.scaler.transform([features])
                
                # Predict failure probability
                failure_prob = self.failure_model.predict_proba(features_scaled)[0][1]
                
                # Analyze contributing factors
                feature_importance = self.failure_model.feature_importances_
                contributing_factors = await self._identify_contributing_factors(
                    features, feature_importance
                )
                
                return PredictionResult(
                    prediction_type=PredictionType.FAILURE,
                    confidence=max(failure_prob, 1 - failure_prob),
                    predicted_value=failure_prob > 0.5,
                    explanation=f"Failure probability: {failure_prob:.2%}",
                    contributing_factors=contributing_factors
                )
            
            return PredictionResult(
                prediction_type=PredictionType.FAILURE,
                confidence=0.0,
                predicted_value=False,
                explanation="Insufficient data for prediction",
                contributing_factors=[]
            )

        except Exception as e:
            logger.error(f"Pipeline failure prediction failed: {e}")
            return PredictionResult(
                prediction_type=PredictionType.FAILURE,
                confidence=0.0,
                predicted_value=False,
                explanation=f"Prediction failed: {str(e)}",
                contributing_factors=[]
            )

    async def predict_execution_duration(self, platform: str, pipeline_id: str,
                                       context: Dict[str, Any] = None) -> PredictionResult:
        """Predict pipeline execution duration.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            context: Additional context for prediction
            
        Returns:
            Duration prediction in seconds
        """
        try:
            await self._ensure_models_trained()
            
            features = await self._extract_prediction_features(platform, pipeline_id, context)
            
            if self.duration_model and features:
                features_scaled = self.scaler.transform([features])
                predicted_duration = self.duration_model.predict(features_scaled)[0]
                
                # Calculate confidence based on model performance
                historical_durations = await self._get_historical_durations(platform, pipeline_id)
                confidence = min(0.9, 1.0 / (1.0 + np.std(historical_durations) / 100))
                
                return PredictionResult(
                    prediction_type=PredictionType.DURATION,
                    confidence=confidence,
                    predicted_value=max(0, predicted_duration),
                    explanation=f"Predicted duration: {predicted_duration:.0f} seconds",
                    contributing_factors=await self._identify_duration_factors(features)
                )
            
            # Fallback to historical average
            avg_duration = np.mean(await self._get_historical_durations(platform, pipeline_id))
            return PredictionResult(
                prediction_type=PredictionType.DURATION,
                confidence=0.5,
                predicted_value=avg_duration,
                explanation=f"Historical average: {avg_duration:.0f} seconds",
                contributing_factors=["historical_average"]
            )

        except Exception as e:
            logger.error(f"Duration prediction failed: {e}")
            return PredictionResult(
                prediction_type=PredictionType.DURATION,
                confidence=0.0,
                predicted_value=0,
                explanation=f"Prediction failed: {str(e)}",
                contributing_factors=[]
            )

    async def analyze_cross_platform_performance(self, pipeline_configs: Dict[str, str]) -> Dict[str, Any]:
        """Analyze performance across multiple CI/CD platforms.
        
        Args:
            pipeline_configs: Dict mapping platform to pipeline_id
            
        Returns:
            Cross-platform performance comparison
        """
        try:
            platform_analyses = {}
            
            # Analyze each platform
            for platform, pipeline_id in pipeline_configs.items():
                analysis = await self.analyze_pipeline_performance(platform, pipeline_id, 30)
                platform_analyses[platform] = analysis
            
            # Compare platforms
            comparison = {
                "platform_comparison": await self._compare_platforms(platform_analyses),
                "best_performers": await self._identify_best_performers(platform_analyses),
                "optimization_opportunities": await self._cross_platform_optimizations(platform_analyses),
                "cost_analysis": await self._cross_platform_cost_analysis(platform_analyses),
                "reliability_comparison": await self._compare_reliability(platform_analyses)
            }
            
            return comparison

        except Exception as e:
            logger.error(f"Cross-platform analysis failed: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _get_pipeline_history(self, platform: str, pipeline_id: str, days: int) -> List[Dict]:
        """Get pipeline execution history."""
        try:
            if self.redis:
                # Get from Redis cache
                key = f"pipeline_history:{platform}:{pipeline_id}"
                cached_data = self.redis.get(key)
                if cached_data:
                    return json.loads(cached_data)
            
            # Generate mock historical data for demonstration
            # In production, this would fetch from the actual CI/CD platform
            executions = []
            end_date = datetime.now()
            
            for i in range(days * 2):  # ~2 executions per day
                execution_date = end_date - timedelta(days=i/2)
                
                # Simulate realistic execution data
                base_duration = 300 + np.random.normal(0, 60)  # ~5 minutes ± 1 minute
                duration = max(60, base_duration)  # Minimum 1 minute
                
                # Simulate failure probability based on various factors
                failure_prob = 0.05 + (0.1 if i % 10 == 0 else 0)  # 5% base + 10% on weekends
                status = "failed" if np.random.random() < failure_prob else "success"
                
                execution = {
                    "id": f"exec_{i}",
                    "date": execution_date.isoformat(),
                    "duration": duration,
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
            
            # Cache the data
            if self.redis:
                self.redis.setex(key, 3600, json.dumps(executions))  # 1 hour cache
            
            return executions

        except Exception as e:
            logger.error(f"Failed to get pipeline history: {e}")
            return []

    async def _calculate_performance_metrics(self, executions: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        if not executions:
            return {}
        
        durations = [e['duration'] for e in executions]
        successful_executions = [e for e in executions if e['status'] == 'success']
        failed_executions = [e for e in executions if e['status'] == 'failed']
        
        return {
            "average_duration": statistics.mean(durations),
            "median_duration": statistics.median(durations),
            "duration_stddev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "min_duration": min(durations),
            "max_duration": max(durations),
            "success_rate": len(successful_executions) / len(executions),
            "failure_rate": len(failed_executions) / len(executions),
            "throughput_per_day": len(executions) / 30,  # Assuming 30 days of data
            "p95_duration": np.percentile(durations, 95),
            "p99_duration": np.percentile(durations, 99)
        }

    async def _identify_bottlenecks(self, executions: List[Dict]) -> List[BottleneckInfo]:
        """Identify pipeline bottlenecks."""
        stage_stats = {}
        
        # Aggregate stage performance
        for execution in executions:
            for stage in execution.get('stages', []):
                stage_name = stage['name']
                if stage_name not in stage_stats:
                    stage_stats[stage_name] = []
                stage_stats[stage_name].append(stage['duration'])
        
        bottlenecks = []
        
        for stage_name, durations in stage_stats.items():
            avg_duration = statistics.mean(durations)
            duration_variance = statistics.variance(durations) if len(durations) > 1 else 0
            
            # Calculate impact score (higher duration + higher variance = higher impact)
            impact_score = avg_duration * (1 + duration_variance / avg_duration)
            
            # Estimate optimization potential based on variance
            optimization_potential = min(0.5, duration_variance / avg_duration)
            
            recommendations = []
            if avg_duration > 120:  # > 2 minutes
                recommendations.append("Consider caching dependencies")
                recommendations.append("Optimize resource allocation")
            
            if duration_variance / avg_duration > 0.3:  # High variance
                recommendations.append("Investigate intermittent issues")
                recommendations.append("Add retry mechanisms")
            
            bottlenecks.append(BottleneckInfo(
                stage_name=stage_name,
                average_duration=avg_duration,
                impact_score=impact_score,
                optimization_potential=optimization_potential,
                recommendations=recommendations
            ))
        
        # Sort by impact score
        bottlenecks.sort(key=lambda b: b.impact_score, reverse=True)
        return bottlenecks

    async def _analyze_trends(self, executions: List[Dict]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        if len(executions) < 10:
            return {"trend": "insufficient_data"}
        
        # Sort by date
        executions_sorted = sorted(executions, key=lambda e: e['date'])
        
        # Analyze duration trend
        durations = [e['duration'] for e in executions_sorted]
        x = np.arange(len(durations)).reshape(-1, 1)
        y = np.array(durations)
        
        model = LinearRegression()
        model.fit(x, y)
        
        trend_slope = model.coef_[0]
        r2 = r2_score(y, model.predict(x))
        
        # Determine trend direction
        if abs(trend_slope) < 1:  # Less than 1 second change per execution
            trend_direction = "stable"
        elif trend_slope > 0:
            trend_direction = "degrading"
        else:
            trend_direction = "improving"
        
        return {
            "trend": trend_direction,
            "slope_seconds_per_execution": trend_slope,
            "trend_confidence": r2,
            "recent_avg": statistics.mean(durations[-10:]),  # Last 10 executions
            "historical_avg": statistics.mean(durations[:-10]) if len(durations) > 10 else 0
        }

    async def _calculate_reliability_metrics(self, executions: List[Dict]) -> Dict[str, Any]:
        """Calculate reliability metrics."""
        if not executions:
            return {}
        
        # Calculate MTTR (Mean Time To Recovery)
        failure_recovery_times = []
        for i, execution in enumerate(executions[:-1]):
            if execution['status'] == 'failed':
                # Look for next successful execution
                for j in range(i + 1, len(executions)):
                    if executions[j]['status'] == 'success':
                        recovery_time = abs((datetime.fromisoformat(executions[j]['date']) - 
                                       datetime.fromisoformat(execution['date'])).total_seconds())
                        failure_recovery_times.append(recovery_time)
                        break
        
        # Calculate MTBF (Mean Time Between Failures)
        failure_intervals = []
        last_failure = None
        for execution in executions:
            if execution['status'] == 'failed':
                if last_failure:
                    interval = abs((datetime.fromisoformat(execution['date']) - 
                              datetime.fromisoformat(last_failure['date'])).total_seconds())
                    failure_intervals.append(interval)
                last_failure = execution
        
        return {
            "mttr_seconds": statistics.mean(failure_recovery_times) if failure_recovery_times else 0,
            "mtbf_seconds": statistics.mean(failure_intervals) if failure_intervals else float('inf'),
            "failure_frequency": len([e for e in executions if e['status'] == 'failed']) / 30,  # per day
            "consecutive_failures_max": await self._calculate_max_consecutive_failures(executions)
        }

    async def _calculate_max_consecutive_failures(self, executions: List[Dict]) -> int:
        """Calculate maximum consecutive failures."""
        max_consecutive = 0
        current_consecutive = 0
        
        for execution in executions:
            if execution['status'] == 'failed':
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive

    async def _analyze_resource_usage(self, executions: List[Dict]) -> Dict[str, Any]:
        """Analyze resource utilization patterns."""
        cpu_usage = []
        memory_usage = []
        
        for execution in executions:
            resource_usage = execution.get('resource_usage', {})
            if 'cpu_seconds' in resource_usage:
                cpu_efficiency = resource_usage['cpu_seconds'] / execution['duration']
                cpu_usage.append(cpu_efficiency)
            
            if 'memory_mb' in resource_usage:
                memory_usage.append(resource_usage['memory_mb'])
        
        return {
            "cpu_efficiency": statistics.mean(cpu_usage) if cpu_usage else 0,
            "average_memory_mb": statistics.mean(memory_usage) if memory_usage else 0,
            "peak_memory_mb": max(memory_usage) if memory_usage else 0,
            "resource_consistency": 1 - (statistics.stdev(cpu_usage) if len(cpu_usage) > 1 and cpu_usage else 0)
        }

    async def _analyze_quality_correlation(self, executions: List[Dict]) -> Dict[str, Any]:
        """Analyze correlation between pipeline performance and code quality."""
        # This would integrate with KiroLinter's quality metrics
        # For now, return placeholder analysis
        return {
            "quality_impact_on_duration": 0.15,  # 15% correlation
            "quality_impact_on_failure_rate": 0.25,  # 25% correlation
            "high_quality_performance_boost": 0.20  # 20% better performance
        }

    async def _ensure_models_trained(self):
        """Ensure ML models are trained with available data."""
        if self.failure_model is None or self.duration_model is None:
            await self._train_models()

    async def _train_models(self):
        """Train ML models for predictions."""
        try:
            # Collect training data from all pipelines
            training_features = []
            failure_labels = []
            duration_labels = []
            
            # Get data from pipeline registry
            platforms = ['github_actions', 'gitlab_ci']  # Available platforms
            
            for platform in platforms:
                # Get sample pipeline IDs (in production, get from registry)
                pipeline_ids = [f"pipeline_{i}" for i in range(5)]
                
                for pipeline_id in pipeline_ids:
                    executions = await self._get_pipeline_history(platform, pipeline_id, 30)
                    
                    for execution in executions:
                        features = await self._extract_training_features(execution)
                        if features:
                            training_features.append(features)
                            failure_labels.append(1 if execution['status'] == 'failed' else 0)
                            duration_labels.append(execution['duration'])
            
            if len(training_features) > 10:  # Minimum data for training
                X = np.array(training_features)
                
                # Fit scaler
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                
                # Train failure prediction model
                from sklearn.ensemble import RandomForestClassifier
                self.failure_model = RandomForestClassifier(n_estimators=100, random_state=42)
                self.failure_model.fit(X_scaled, failure_labels)
                
                # Train duration prediction model
                self.duration_model = RandomForestRegressor(n_estimators=100, random_state=42)
                self.duration_model.fit(X_scaled, duration_labels)
                
                # Train anomaly detector
                self.anomaly_detector.fit(X_scaled)
                
                logger.info(f"Models trained with {len(training_features)} samples")
            else:
                logger.warning("Insufficient data for model training")

        except Exception as e:
            logger.error(f"Model training failed: {e}")

    async def _extract_training_features(self, execution: Dict) -> Optional[List[float]]:
        """Extract features for model training."""
        try:
            features = [
                execution['duration'],
                len(execution.get('stages', [])),
                sum(stage['duration'] for stage in execution.get('stages', [])),
                execution.get('resource_usage', {}).get('cpu_seconds', 0),
                execution.get('resource_usage', {}).get('memory_mb', 0),
                # Time-based features
                datetime.fromisoformat(execution['date']).hour,  # Hour of day
                datetime.fromisoformat(execution['date']).weekday(),  # Day of week
            ]
            return features
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    async def _extract_prediction_features(self, platform: str, pipeline_id: str, 
                                         context: Dict[str, Any] = None) -> Optional[List[float]]:
        """Extract features for prediction."""
        try:
            # Get recent executions for feature calculation
            recent_executions = await self._get_pipeline_history(platform, pipeline_id, 7)
            
            if not recent_executions:
                return None
            
            # Calculate aggregate features
            recent_durations = [e['duration'] for e in recent_executions]
            recent_failures = len([e for e in recent_executions if e['status'] == 'failed'])
            
            features = [
                statistics.mean(recent_durations),
                statistics.stdev(recent_durations) if len(recent_durations) > 1 else 0,
                recent_failures / len(recent_executions),  # Recent failure rate
                len(recent_executions),  # Execution frequency
                datetime.now().hour,  # Current hour
                datetime.now().weekday(),  # Current day of week
            ]
            
            # Add context features if available
            if context:
                features.extend([
                    len(context.get('changed_files', [])),
                    context.get('commit_size', 0),
                    1 if context.get('branch', '') == 'main' else 0,
                ])
            else:
                features.extend([0, 0, 0])  # Default values
            
            return features

        except Exception as e:
            logger.error(f"Prediction feature extraction failed: {e}")
            return None

    async def _identify_contributing_factors(self, features: List[float], 
                                           importance: List[float]) -> List[str]:
        """Identify factors contributing to predictions."""
        feature_names = [
            "average_duration", "duration_variance", "recent_failure_rate",
            "execution_frequency", "hour_of_day", "day_of_week",
            "changed_files_count", "commit_size", "is_main_branch"
        ]
        
        # Get top 3 most important features
        feature_importance = list(zip(feature_names, importance, features))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        factors = []
        for name, importance_score, value in feature_importance[:3]:
            if importance_score > 0.1:  # Only include significant factors
                factors.append(f"{name} (value: {value:.2f}, importance: {importance_score:.2f})")
        
        return factors

    async def _identify_duration_factors(self, features: List[float]) -> List[str]:
        """Identify factors affecting duration prediction."""
        factors = []
        
        if len(features) >= 6:
            if features[0] > 600:  # Average duration > 10 minutes
                factors.append("historically_slow_pipeline")
            if features[1] > 100:  # High variance
                factors.append("inconsistent_performance")
            if features[4] < 8 or features[4] > 18:  # Off-hours execution
                factors.append("off_peak_execution")
        
        return factors if factors else ["historical_patterns"]

    async def _get_historical_durations(self, platform: str, pipeline_id: str) -> List[float]:
        """Get historical execution durations."""
        try:
            executions = await self._get_pipeline_history(platform, pipeline_id, 30)
            return [e['duration'] for e in executions if e['status'] == 'success']
        except Exception:
            return [300.0]  # Default 5-minute duration

    async def _find_parallelizable_stages(self, platform: str, pipeline_id: str) -> List[str]:
        """Find stages that can be executed in parallel."""
        try:
            executions = await self._get_pipeline_history(platform, pipeline_id, 7)
            if executions:
                # Analyze stage dependencies (simplified)
                stages = executions[0].get('stages', [])
                # In a real implementation, this would analyze actual dependencies
                parallelizable = [stage['name'] for stage in stages[1:]]  # Skip first stage
                return parallelizable
            return []
        except Exception:
            return []

    async def _compare_platforms(self, platform_analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Compare performance across platforms."""
        comparison = {}
        
        for metric in ['average_duration', 'success_rate', 'throughput_per_day']:
            values = {}
            for platform, analysis in platform_analyses.items():
                metrics = analysis.get('performance_metrics', {})
                if metric in metrics:
                    values[platform] = metrics[metric]
            
            if values:
                best_platform = max(values, key=values.get) if metric != 'average_duration' else min(values, key=values.get)
                comparison[metric] = {
                    'values': values,
                    'best_platform': best_platform,
                    'best_value': values[best_platform]
                }
        
        return comparison

    async def _identify_best_performers(self, platform_analyses: Dict[str, Dict]) -> Dict[str, str]:
        """Identify best performing platforms by category."""
        performers = {}
        
        # Speed
        speed_scores = {}
        for platform, analysis in platform_analyses.items():
            metrics = analysis.get('performance_metrics', {})
            if 'average_duration' in metrics:
                speed_scores[platform] = 1 / metrics['average_duration']  # Inverse for speed
        
        if speed_scores:
            performers['speed'] = max(speed_scores, key=speed_scores.get)
        
        # Reliability
        reliability_scores = {}
        for platform, analysis in platform_analyses.items():
            metrics = analysis.get('performance_metrics', {})
            if 'success_rate' in metrics:
                reliability_scores[platform] = metrics['success_rate']
        
        if reliability_scores:
            performers['reliability'] = max(reliability_scores, key=reliability_scores.get)
        
        return performers

    async def _cross_platform_optimizations(self, platform_analyses: Dict[str, Dict]) -> List[str]:
        """Identify cross-platform optimization opportunities."""
        optimizations = []
        
        # Check for resource usage differences
        resource_usage = {}
        for platform, analysis in platform_analyses.items():
            resource_data = analysis.get('resource_utilization', {})
            if 'cpu_efficiency' in resource_data:
                resource_usage[platform] = resource_data['cpu_efficiency']
        
        if len(resource_usage) >= 2:
            max_efficiency = max(resource_usage.values())
            min_efficiency = min(resource_usage.values())
            
            if max_efficiency - min_efficiency > 0.2:  # 20% difference
                optimizations.append("Standardize resource allocation across platforms")
        
        # Check for performance differences
        durations = {}
        for platform, analysis in platform_analyses.items():
            metrics = analysis.get('performance_metrics', {})
            if 'average_duration' in metrics:
                durations[platform] = metrics['average_duration']
        
        if len(durations) >= 2:
            max_duration = max(durations.values())
            min_duration = min(durations.values())
            
            if max_duration / min_duration > 1.5:  # 50% difference
                optimizations.append("Migrate workloads to faster platforms")
        
        return optimizations

    async def _cross_platform_cost_analysis(self, platform_analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Analyze costs across platforms."""
        # Simplified cost analysis - in production, integrate with actual billing APIs
        return {
            "estimated_monthly_costs": {
                platform: np.random.uniform(100, 500)  # Mock data
                for platform in platform_analyses.keys()
            },
            "cost_per_execution": {
                platform: np.random.uniform(0.10, 2.00)  # Mock data
                for platform in platform_analyses.keys()
            },
            "optimization_potential": 0.25  # 25% potential savings
        }

    async def _compare_reliability(self, platform_analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Compare reliability across platforms."""
        reliability_comparison = {}
        
        for platform, analysis in platform_analyses.items():
            reliability = analysis.get('reliability', {})
            reliability_comparison[platform] = {
                'mttr_hours': reliability.get('mttr_seconds', 0) / 3600,
                'mtbf_hours': reliability.get('mtbf_seconds', float('inf')) / 3600,
                'failure_frequency_per_day': reliability.get('failure_frequency', 0)
            }
        
        return reliability_comparison

    async def _get_cached_analysis(self, cache_key: str) -> Optional[Dict]:
        """Get cached analysis result."""
        if cache_key in self._analytics_cache:
            cached_data, timestamp = self._analytics_cache[cache_key]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                return cached_data
            else:
                del self._analytics_cache[cache_key]
        return None

    async def _cache_analysis(self, cache_key: str, analysis: Dict):
        """Cache analysis result."""
        self._analytics_cache[cache_key] = (analysis, datetime.now().timestamp())
        
        # Clean up old cache entries
        current_time = datetime.now().timestamp()
        expired_keys = [
            key for key, (_, timestamp) in self._analytics_cache.items()
            if current_time - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._analytics_cache[key]


class OptimizationEngine:
    """
    Optimization engine for automatic pipeline improvements.
    """

    def __init__(self, pipeline_analyzer: PipelineAnalyzer):
        """Initialize optimization engine.
        
        Args:
            pipeline_analyzer: Pipeline analyzer instance
        """
        self.analyzer = pipeline_analyzer
        self.optimization_history = {}

    async def optimize_pipeline_automatically(self, platform: str, pipeline_id: str,
                                           optimization_types: List[OptimizationType] = None) -> Dict[str, Any]:
        """Automatically apply safe optimizations to a pipeline.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            optimization_types: Types of optimizations to apply
            
        Returns:
            Results of applied optimizations
        """
        if optimization_types is None:
            optimization_types = [OptimizationType.PERFORMANCE, OptimizationType.RELIABILITY]

        try:
            # Get recommendations
            recommendations = await self.analyzer.generate_optimization_recommendations(
                platform, pipeline_id
            )
            
            # Filter by requested types
            filtered_recommendations = [
                rec for rec in recommendations 
                if rec.type in optimization_types
            ]
            
            # Apply safe optimizations (low effort, high impact)
            applied_optimizations = []
            
            for recommendation in filtered_recommendations:
                if (recommendation.implementation_effort == "low" and 
                    recommendation.expected_improvement > 0.1):  # > 10% improvement
                    
                    result = await self._apply_optimization(platform, pipeline_id, recommendation)
                    applied_optimizations.append(result)
            
            return {
                "total_recommendations": len(recommendations),
                "filtered_recommendations": len(filtered_recommendations),
                "applied_optimizations": applied_optimizations,
                "estimated_total_improvement": sum(
                    opt.get('actual_improvement', 0) for opt in applied_optimizations
                )
            }

        except Exception as e:
            logger.error(f"Automatic optimization failed: {e}")
            return {"error": str(e), "applied_optimizations": []}

    async def _apply_optimization(self, platform: str, pipeline_id: str, 
                                recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Apply a specific optimization recommendation."""
        try:
            # Record optimization attempt
            optimization_key = f"{platform}:{pipeline_id}:{recommendation.type.value}"
            
            # Simulate optimization application
            # In production, this would make actual changes to CI/CD configurations
            await asyncio.sleep(0.1)  # Simulate work
            
            # Mock successful application
            actual_improvement = recommendation.expected_improvement * np.random.uniform(0.8, 1.2)
            
            result = {
                "optimization_type": recommendation.type.value,
                "description": recommendation.description,
                "expected_improvement": recommendation.expected_improvement,
                "actual_improvement": actual_improvement,
                "success": True,
                "applied_at": datetime.now().isoformat()
            }
            
            # Store in history
            if optimization_key not in self.optimization_history:
                self.optimization_history[optimization_key] = []
            self.optimization_history[optimization_key].append(result)
            
            return result

        except Exception as e:
            logger.error(f"Optimization application failed: {e}")
            return {
                "optimization_type": recommendation.type.value,
                "description": recommendation.description,
                "success": False,
                "error": str(e),
                "applied_at": datetime.now().isoformat()
            }


class PipelinePredictor:
    """
    Advanced pipeline prediction system using machine learning.
    """

    def __init__(self, pipeline_analyzer: PipelineAnalyzer):
        """Initialize predictor.
        
        Args:
            pipeline_analyzer: Pipeline analyzer instance
        """
        self.analyzer = pipeline_analyzer
        self.prediction_cache = {}

    async def predict_resource_demand(self, platform: str, pipeline_id: str,
                                    forecast_days: int = 7) -> Dict[str, Any]:
        """Predict future resource demand.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            forecast_days: Number of days to forecast
            
        Returns:
            Resource demand forecast
        """
        try:
            # Get historical resource usage
            executions = await self.analyzer._get_pipeline_history(platform, pipeline_id, 30)
            
            if len(executions) < 7:
                return {"error": "Insufficient historical data"}

            # Extract resource usage patterns
            daily_usage = {}
            for execution in executions:
                date = datetime.fromisoformat(execution['date']).date()
                if date not in daily_usage:
                    daily_usage[date] = {'cpu': 0, 'memory': 0, 'executions': 0}
                
                resource_usage = execution.get('resource_usage', {})
                daily_usage[date]['cpu'] += resource_usage.get('cpu_seconds', 0)
                daily_usage[date]['memory'] += resource_usage.get('memory_mb', 0)
                daily_usage[date]['executions'] += 1

            # Calculate trends and forecast
            dates = sorted(daily_usage.keys())
            cpu_usage = [daily_usage[date]['cpu'] for date in dates]
            memory_usage = [daily_usage[date]['memory'] for date in dates]
            execution_counts = [daily_usage[date]['executions'] for date in dates]

            # Simple linear trend forecasting
            forecast = {}
            current_date = datetime.now().date()
            
            for days_ahead in range(1, forecast_days + 1):
                forecast_date = current_date + timedelta(days=days_ahead)
                
                # Simple trend-based prediction
                cpu_trend = np.polyfit(range(len(cpu_usage)), cpu_usage, 1)
                memory_trend = np.polyfit(range(len(memory_usage)), memory_usage, 1)
                exec_trend = np.polyfit(range(len(execution_counts)), execution_counts, 1)
                
                forecast[forecast_date.isoformat()] = {
                    'predicted_cpu_seconds': max(0, np.polyval(cpu_trend, len(cpu_usage) + days_ahead)),
                    'predicted_memory_mb': max(0, np.polyval(memory_trend, len(memory_usage) + days_ahead)),
                    'predicted_executions': max(0, int(np.polyval(exec_trend, len(execution_counts) + days_ahead)))
                }

            return {
                "platform": platform,
                "pipeline_id": pipeline_id,
                "forecast_days": forecast_days,
                "predictions": forecast,
                "confidence": 0.7,  # Static confidence for demo
                "historical_period_days": len(dates)
            }

        except Exception as e:
            logger.error(f"Resource demand prediction failed: {e}")
            return {"error": str(e)}

    async def analyze_quality_impact(self, platform: str, pipeline_id: str,
                                   quality_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Analyze impact of code quality on pipeline performance.
        
        Args:
            platform: CI/CD platform name
            pipeline_id: Pipeline identifier
            quality_metrics: Current quality metrics from KiroLinter
            
        Returns:
            Quality impact analysis
        """
        try:
            # Get recent pipeline performance
            performance = await self.analyzer.analyze_pipeline_performance(platform, pipeline_id, 14)
            
            if 'error' in performance:
                return performance

            # Analyze correlation between quality metrics and performance
            metrics = performance.get('performance_metrics', {})
            
            # Simulate quality impact analysis
            # In production, this would use historical data to find correlations
            quality_score = sum(quality_metrics.values()) / len(quality_metrics)
            
            impact_analysis = {
                "current_quality_score": quality_score,
                "performance_correlation": {
                    "duration_impact": self._calculate_quality_duration_impact(quality_score),
                    "failure_rate_impact": self._calculate_quality_failure_impact(quality_score),
                    "reliability_impact": self._calculate_quality_reliability_impact(quality_score)
                },
                "improvement_potential": {
                    "duration_reduction": max(0, (0.8 - quality_score) * 0.3),  # Up to 30% improvement
                    "failure_rate_reduction": max(0, (0.8 - quality_score) * 0.5),  # Up to 50% improvement
                    "reliability_improvement": max(0, (0.8 - quality_score) * 0.4)  # Up to 40% improvement
                },
                "recommendations": await self._generate_quality_recommendations(quality_score, quality_metrics)
            }

            return impact_analysis

        except Exception as e:
            logger.error(f"Quality impact analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_quality_duration_impact(self, quality_score: float) -> float:
        """Calculate impact of quality score on execution duration."""
        # Higher quality = faster execution (fewer issues to resolve)
        base_impact = 0.2  # 20% base impact
        quality_factor = max(0, 1 - quality_score)  # Inverse relationship
        return base_impact * quality_factor

    def _calculate_quality_failure_impact(self, quality_score: float) -> float:
        """Calculate impact of quality score on failure rate."""
        # Higher quality = lower failure rate
        base_impact = 0.3  # 30% base impact
        quality_factor = max(0, 1 - quality_score)  # Inverse relationship
        return base_impact * quality_factor

    def _calculate_quality_reliability_impact(self, quality_score: float) -> float:
        """Calculate impact of quality score on reliability."""
        # Higher quality = better reliability
        return quality_score * 0.4  # Direct relationship

    async def _generate_quality_recommendations(self, quality_score: float, 
                                              quality_metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on quality analysis."""
        recommendations = []
        
        if quality_score < 0.6:
            recommendations.append("Implement automated code quality gates")
            recommendations.append("Increase test coverage to reduce pipeline failures")
        
        if quality_score < 0.8:
            recommendations.append("Add static analysis checks to catch issues early")
        
        # Analyze specific metrics
        for metric, value in quality_metrics.items():
            if value < 0.7:
                recommendations.append(f"Improve {metric} metric (current: {value:.2f})")
        
        if not recommendations:
            recommendations.append("Maintain current quality standards")
        
        return recommendations