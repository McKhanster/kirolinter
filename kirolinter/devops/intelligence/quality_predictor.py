"""
Quality Predictor

AI-powered quality trend prediction and analysis for proactive
code quality management and early warning systems.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import statistics

logger = logging.getLogger(__name__)


@dataclass
class QualityTrend:
    """Quality trend analysis result"""
    metric_name: str
    current_value: float
    trend_direction: str  # improving, declining, stable
    trend_strength: float  # 0.0 to 1.0
    predicted_value_30d: float
    confidence: float
    historical_data: List[Tuple[datetime, float]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QualityPrediction:
    """Quality prediction result"""
    application: str
    prediction_date: datetime
    time_horizon_days: int
    overall_quality_forecast: str  # improving, declining, stable
    trends: List[QualityTrend] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class QualityAlert:
    """Quality degradation alert"""
    id: str
    metric_name: str
    alert_type: str  # threshold, trend, anomaly
    severity: str  # low, medium, high, critical
    current_value: float
    threshold_value: float
    description: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    recommendations: List[str] = field(default_factory=list)


class QualityPredictor:
    """AI-powered quality trend prediction and analysis"""
    
    def __init__(self, historical_data_store=None, ml_models=None):
        """
        Initialize quality predictor
        
        Args:
            historical_data_store: Storage for historical quality data
            ml_models: Pre-trained ML models for prediction
        """
        self.historical_data = historical_data_store
        self.ml_models = ml_models or {}
        
        # Quality thresholds for alerts
        self.quality_thresholds = {
            "code_coverage": {"warning": 0.7, "critical": 0.5},
            "test_pass_rate": {"warning": 0.9, "critical": 0.8},
            "bug_density": {"warning": 5.0, "critical": 10.0},
            "technical_debt_ratio": {"warning": 0.3, "critical": 0.5},
            "maintainability_index": {"warning": 60, "critical": 40},
            "security_hotspots": {"warning": 5, "critical": 10}
        }
        
        # Trend analysis parameters
        self.trend_window_days = 30
        self.anomaly_threshold = 2.0  # Standard deviations
    
    async def predict_quality_trends(self, application: str, 
                                   time_horizon_days: int = 30) -> QualityPrediction:
        """
        Predict quality trends for an application
        
        Args:
            application: Application name
            time_horizon_days: Prediction time horizon
            
        Returns:
            QualityPrediction: Comprehensive quality prediction
        """
        logger.info(f"Predicting quality trends for {application} over {time_horizon_days} days")
        
        # Get historical quality data
        historical_data = await self._get_historical_quality_data(application)
        
        # Analyze trends for each metric
        trends = []
        for metric_name, data_points in historical_data.items():
            trend = await self._analyze_metric_trend(metric_name, data_points, time_horizon_days)
            trends.append(trend)
        
        # Determine overall quality forecast
        overall_forecast = self._determine_overall_forecast(trends)
        
        # Generate risk alerts
        risk_alerts = self._generate_risk_alerts(trends)
        
        # Generate recommendations
        recommendations = self._generate_quality_recommendations(trends, risk_alerts)
        
        # Calculate confidence score
        confidence_score = self._calculate_prediction_confidence(trends)
        
        return QualityPrediction(
            application=application,
            prediction_date=datetime.utcnow(),
            time_horizon_days=time_horizon_days,
            trends=trends,
            overall_quality_forecast=overall_forecast,
            risk_alerts=risk_alerts,
            recommendations=recommendations,
            confidence_score=confidence_score
        )
    
    async def detect_quality_anomalies(self, application: str, 
                                     current_metrics: Dict[str, float]) -> List[QualityAlert]:
        """
        Detect quality anomalies in current metrics
        
        Args:
            application: Application name
            current_metrics: Current quality metrics
            
        Returns:
            List of quality alerts for detected anomalies
        """
        alerts = []
        
        for metric_name, current_value in current_metrics.items():
            # Check threshold-based alerts
            threshold_alert = self._check_threshold_alert(metric_name, current_value)
            if threshold_alert:
                alerts.append(threshold_alert)
            
            # Check trend-based alerts
            trend_alert = await self._check_trend_alert(application, metric_name, current_value)
            if trend_alert:
                alerts.append(trend_alert)
            
            # Check anomaly-based alerts
            anomaly_alert = await self._check_anomaly_alert(application, metric_name, current_value)
            if anomaly_alert:
                alerts.append(anomaly_alert)
        
        return alerts
    
    async def generate_quality_forecast(self, application: str, 
                                      scenarios: List[Dict[str, Any]]) -> Dict[str, QualityPrediction]:
        """
        Generate quality forecasts for different scenarios
        
        Args:
            application: Application name
            scenarios: List of scenario configurations
            
        Returns:
            Dict mapping scenario names to quality predictions
        """
        forecasts = {}
        
        for scenario in scenarios:
            scenario_name = scenario.get("name", "unnamed")
            
            # Modify prediction parameters based on scenario
            modified_prediction = await self._predict_with_scenario(application, scenario)
            forecasts[scenario_name] = modified_prediction
        
        return forecasts
    
    async def _get_historical_quality_data(self, application: str) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get historical quality data for an application"""
        # Mock historical data - would query actual data store
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        # Generate mock data with trends
        historical_data = {}
        
        # Code coverage with slight decline
        coverage_data = []
        base_coverage = 0.85
        for i in range(90):
            date = start_date + timedelta(days=i)
            # Add slight decline with noise
            value = base_coverage - (i * 0.001) + (hash(str(date)) % 100 - 50) * 0.001
            value = max(0.0, min(1.0, value))
            coverage_data.append((date, value))
        historical_data["code_coverage"] = coverage_data
        
        # Test pass rate with stability
        test_data = []
        base_test_rate = 0.95
        for i in range(90):
            date = start_date + timedelta(days=i)
            # Stable with occasional dips
            value = base_test_rate + (hash(str(date)) % 100 - 50) * 0.0005
            if i % 20 == 0:  # Occasional dip
                value -= 0.05
            value = max(0.0, min(1.0, value))
            test_data.append((date, value))
        historical_data["test_pass_rate"] = test_data
        
        # Bug density with improvement
        bug_data = []
        base_bugs = 8.0
        for i in range(90):
            date = start_date + timedelta(days=i)
            # Gradual improvement
            value = base_bugs - (i * 0.02) + (hash(str(date)) % 100 - 50) * 0.01
            value = max(0.0, value)
            bug_data.append((date, value))
        historical_data["bug_density"] = bug_data
        
        return historical_data
    
    async def _analyze_metric_trend(self, metric_name: str, 
                                  data_points: List[Tuple[datetime, float]], 
                                  prediction_days: int) -> QualityTrend:
        """Analyze trend for a specific metric"""
        if len(data_points) < 7:
            # Not enough data for trend analysis
            return QualityTrend(
                metric_name=metric_name,
                current_value=data_points[-1][1] if data_points else 0.0,
                trend_direction="stable",
                trend_strength=0.0,
                predicted_value_30d=data_points[-1][1] if data_points else 0.0,
                confidence=0.1,
                historical_data=data_points
            )
        
        # Extract values and calculate trend
        values = [point[1] for point in data_points]
        current_value = values[-1]
        
        # Simple linear trend calculation
        x_values = list(range(len(values)))
        trend_slope = self._calculate_linear_trend(x_values, values)
        
        # Determine trend direction and strength
        if abs(trend_slope) < 0.001:
            trend_direction = "stable"
            trend_strength = 0.0
        elif trend_slope > 0:
            trend_direction = "improving" if self._is_higher_better(metric_name) else "declining"
            trend_strength = min(abs(trend_slope) * 1000, 1.0)
        else:
            trend_direction = "declining" if self._is_higher_better(metric_name) else "improving"
            trend_strength = min(abs(trend_slope) * 1000, 1.0)
        
        # Predict future value
        predicted_value = current_value + (trend_slope * prediction_days)
        predicted_value = max(0.0, predicted_value)
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_trend_confidence(values)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(data_points)
        
        return QualityTrend(
            metric_name=metric_name,
            current_value=current_value,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            predicted_value_30d=predicted_value,
            confidence=confidence,
            historical_data=data_points,
            anomalies=anomalies
        )
    
    def _calculate_linear_trend(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate linear trend slope using least squares"""
        n = len(x_values)
        if n < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _is_higher_better(self, metric_name: str) -> bool:
        """Determine if higher values are better for a metric"""
        higher_better_metrics = {
            "code_coverage", "test_pass_rate", "maintainability_index"
        }
        return metric_name in higher_better_metrics
    
    def _calculate_trend_confidence(self, values: List[float]) -> float:
        """Calculate confidence in trend analysis"""
        if len(values) < 3:
            return 0.1
        
        # Calculate R-squared for trend line fit
        x_values = list(range(len(values)))
        slope = self._calculate_linear_trend(x_values, values)
        
        y_mean = statistics.mean(values)
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        
        if ss_tot == 0:
            return 0.5
        
        # Calculate predicted values
        predicted = [slope * x + (y_mean - slope * statistics.mean(x_values)) for x in x_values]
        ss_res = sum((y - pred) ** 2 for y, pred in zip(values, predicted))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        return max(0.1, min(0.9, r_squared))
    
    def _detect_anomalies(self, data_points: List[Tuple[datetime, float]]) -> List[Dict[str, Any]]:
        """Detect anomalies in the data"""
        if len(data_points) < 10:
            return []
        
        values = [point[1] for point in data_points]
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        
        anomalies = []
        for i, (date, value) in enumerate(data_points):
            if std_val > 0 and abs(value - mean_val) > self.anomaly_threshold * std_val:
                anomalies.append({
                    "date": date,
                    "value": value,
                    "deviation": abs(value - mean_val) / std_val,
                    "type": "outlier"
                })
        
        return anomalies
    
    def _determine_overall_forecast(self, trends: List[QualityTrend]) -> str:
        """Determine overall quality forecast from individual trends"""
        if not trends:
            return "stable"
        
        improving_count = sum(1 for trend in trends if trend.trend_direction == "improving")
        declining_count = sum(1 for trend in trends if trend.trend_direction == "declining")
        
        if improving_count > declining_count * 1.5:
            return "improving"
        elif declining_count > improving_count * 1.5:
            return "declining"
        else:
            return "stable"
    
    def _generate_risk_alerts(self, trends: List[QualityTrend]) -> List[str]:
        """Generate risk alerts based on trends"""
        alerts = []
        
        for trend in trends:
            if trend.trend_direction == "declining" and trend.trend_strength > 0.5:
                alerts.append(f"Declining trend detected in {trend.metric_name}")
            
            if trend.predicted_value_30d < self.quality_thresholds.get(trend.metric_name, {}).get("warning", 0):
                alerts.append(f"{trend.metric_name} predicted to fall below warning threshold")
        
        return alerts
    
    def _generate_quality_recommendations(self, trends: List[QualityTrend], 
                                        risk_alerts: List[str]) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        for trend in trends:
            if trend.trend_direction == "declining":
                if trend.metric_name == "code_coverage":
                    recommendations.append("Increase test coverage by adding unit and integration tests")
                elif trend.metric_name == "test_pass_rate":
                    recommendations.append("Investigate and fix failing tests")
                elif trend.metric_name == "bug_density":
                    recommendations.append("Implement more thorough code review process")
        
        if len(risk_alerts) > 2:
            recommendations.append("Consider implementing quality gates in CI/CD pipeline")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _calculate_prediction_confidence(self, trends: List[QualityTrend]) -> float:
        """Calculate overall prediction confidence"""
        if not trends:
            return 0.0
        
        avg_confidence = sum(trend.confidence for trend in trends) / len(trends)
        return avg_confidence
    
    def _check_threshold_alert(self, metric_name: str, current_value: float) -> Optional[QualityAlert]:
        """Check if metric exceeds threshold"""
        thresholds = self.quality_thresholds.get(metric_name)
        if not thresholds:
            return None
        
        if current_value < thresholds.get("critical", 0):
            return QualityAlert(
                id=f"threshold_{metric_name}_{int(datetime.utcnow().timestamp())}",
                metric_name=metric_name,
                alert_type="threshold",
                severity="critical",
                current_value=current_value,
                threshold_value=thresholds["critical"],
                description=f"{metric_name} is below critical threshold",
                recommendations=[f"Immediate action required to improve {metric_name}"]
            )
        elif current_value < thresholds.get("warning", 0):
            return QualityAlert(
                id=f"threshold_{metric_name}_{int(datetime.utcnow().timestamp())}",
                metric_name=metric_name,
                alert_type="threshold",
                severity="warning",
                current_value=current_value,
                threshold_value=thresholds["warning"],
                description=f"{metric_name} is below warning threshold",
                recommendations=[f"Consider improving {metric_name}"]
            )
        
        return None
    
    async def _check_trend_alert(self, application: str, metric_name: str, 
                               current_value: float) -> Optional[QualityAlert]:
        """Check for trend-based alerts"""
        # Mock trend check - would analyze actual historical data
        return None
    
    async def _check_anomaly_alert(self, application: str, metric_name: str, 
                                 current_value: float) -> Optional[QualityAlert]:
        """Check for anomaly-based alerts"""
        # Mock anomaly check - would use statistical analysis
        return None
    
    async def _predict_with_scenario(self, application: str, 
                                   scenario: Dict[str, Any]) -> QualityPrediction:
        """Generate prediction with scenario modifications"""
        # Mock scenario-based prediction
        base_prediction = await self.predict_quality_trends(application)
        
        # Modify prediction based on scenario
        scenario_type = scenario.get("type", "baseline")
        if scenario_type == "increased_testing":
            # Improve test-related metrics
            for trend in base_prediction.trends:
                if "test" in trend.metric_name or "coverage" in trend.metric_name:
                    trend.predicted_value_30d *= 1.1
        
        return base_prediction