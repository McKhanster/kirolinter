"""
Risk Assessment Engine

AI-powered risk assessment for deployments and code changes using
machine learning models and historical data analysis.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """Individual risk factor in assessment"""
    name: str
    category: str  # code, infrastructure, process, external
    severity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    description: str
    mitigation_suggestions: List[str] = field(default_factory=list)
    historical_impact: Optional[float] = None


@dataclass
class MitigationStrategy:
    """Risk mitigation strategy"""
    name: str
    description: str
    effort_level: str  # low, medium, high
    time_estimate_hours: int
    effectiveness: float  # 0.0 to 1.0
    prerequisites: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Complete risk assessment result"""
    deployment_id: str
    overall_risk_score: float  # 0.0 to 1.0
    risk_level: str  # low, medium, high, critical
    risk_factors: List[RiskFactor] = field(default_factory=list)
    mitigation_strategies: List[MitigationStrategy] = field(default_factory=list)
    confidence_level: float = 0.0
    assessment_timestamp: datetime = field(default_factory=datetime.utcnow)
    historical_context: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def critical_factors(self) -> List[RiskFactor]:
        """Get critical risk factors (severity > 0.7)"""
        return [factor for factor in self.risk_factors if factor.severity > 0.7]
    
    @property
    def high_confidence_factors(self) -> List[RiskFactor]:
        """Get high confidence risk factors (confidence > 0.8)"""
        return [factor for factor in self.risk_factors if factor.confidence > 0.8]


class RiskAssessmentEngine:
    """AI-powered risk assessment engine for deployments"""
    
    def __init__(self, historical_data_store=None, ml_models=None):
        """
        Initialize risk assessment engine
        
        Args:
            historical_data_store: Storage for historical deployment data
            ml_models: Pre-trained ML models for risk prediction
        """
        self.historical_data = historical_data_store
        self.ml_models = ml_models or {}
        self.risk_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.9
        }
        
        # Risk factor weights
        self.factor_weights = {
            "code_complexity": 0.15,
            "change_size": 0.12,
            "test_coverage": 0.18,
            "deployment_frequency": 0.10,
            "rollback_history": 0.15,
            "dependency_changes": 0.12,
            "infrastructure_changes": 0.08,
            "team_experience": 0.10
        }
    
    async def assess_deployment_risk(self, deployment_plan: Dict[str, Any]) -> RiskAssessment:
        """
        Assess risk for a planned deployment
        
        Args:
            deployment_plan: Deployment plan details
            
        Returns:
            RiskAssessment: Comprehensive risk assessment
        """
        logger.info(f"Assessing deployment risk for: {deployment_plan.get('name', 'unknown')}")
        
        # Extract deployment context
        deployment_id = deployment_plan.get("id", "unknown")
        application = deployment_plan.get("application", "unknown")
        version = deployment_plan.get("version", "unknown")
        targets = deployment_plan.get("targets", [])
        
        # Analyze various risk factors
        risk_factors = []
        
        # Code-related risks
        code_risks = await self._assess_code_risks(deployment_plan)
        risk_factors.extend(code_risks)
        
        # Infrastructure risks
        infra_risks = await self._assess_infrastructure_risks(deployment_plan)
        risk_factors.extend(infra_risks)
        
        # Process risks
        process_risks = await self._assess_process_risks(deployment_plan)
        risk_factors.extend(process_risks)
        
        # Historical risks
        historical_risks = await self._assess_historical_risks(application, version)
        risk_factors.extend(historical_risks)
        
        # Calculate overall risk score
        overall_risk = self._calculate_overall_risk(risk_factors)
        risk_level = self._determine_risk_level(overall_risk)
        
        # Generate mitigation strategies
        mitigation_strategies = self._generate_mitigation_strategies(risk_factors)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_factors, risk_level)
        
        # Get historical context
        historical_context = await self._get_historical_context(application)
        
        return RiskAssessment(
            deployment_id=deployment_id,
            overall_risk_score=overall_risk,
            risk_level=risk_level,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            confidence_level=self._calculate_confidence(risk_factors),
            historical_context=historical_context,
            recommendations=recommendations
        )
    
    async def predict_failure_probability(self, changes: List[Dict[str, Any]]) -> float:
        """
        Predict probability of deployment failure based on changes
        
        Args:
            changes: List of code/infrastructure changes
            
        Returns:
            float: Failure probability (0.0 to 1.0)
        """
        if not changes:
            return 0.1  # Base failure rate
        
        # Analyze change characteristics
        total_lines_changed = sum(change.get("lines_changed", 0) for change in changes)
        files_changed = len(set(change.get("file_path", "") for change in changes))
        critical_files_changed = sum(1 for change in changes 
                                   if self._is_critical_file(change.get("file_path", "")))
        
        # Simple heuristic-based prediction (would be ML model in production)
        base_risk = 0.1
        size_risk = min(total_lines_changed / 1000 * 0.2, 0.3)
        file_risk = min(files_changed / 50 * 0.15, 0.2)
        critical_risk = critical_files_changed * 0.1
        
        failure_probability = min(base_risk + size_risk + file_risk + critical_risk, 0.95)
        
        logger.info(f"Predicted failure probability: {failure_probability:.3f}")
        return failure_probability
    
    async def _assess_code_risks(self, deployment_plan: Dict[str, Any]) -> List[RiskFactor]:
        """Assess code-related risks"""
        risks = []
        
        # Mock code analysis - would integrate with actual code analysis
        code_metrics = deployment_plan.get("code_metrics", {})
        
        # Complexity risk
        complexity = code_metrics.get("cyclomatic_complexity", 5.0)
        if complexity > 10:
            risks.append(RiskFactor(
                name="high_code_complexity",
                category="code",
                severity=min(complexity / 20, 1.0),
                confidence=0.8,
                description=f"High cyclomatic complexity detected: {complexity}",
                mitigation_suggestions=[
                    "Refactor complex functions",
                    "Add comprehensive unit tests",
                    "Consider code review by senior developer"
                ]
            ))
        
        # Test coverage risk
        coverage = code_metrics.get("test_coverage", 0.8)
        if coverage < 0.7:
            risks.append(RiskFactor(
                name="low_test_coverage",
                category="code",
                severity=1.0 - coverage,
                confidence=0.9,
                description=f"Low test coverage: {coverage*100:.1f}%",
                mitigation_suggestions=[
                    "Increase test coverage to at least 80%",
                    "Add integration tests",
                    "Implement automated testing in CI/CD"
                ]
            ))
        
        return risks
    
    async def _assess_infrastructure_risks(self, deployment_plan: Dict[str, Any]) -> List[RiskFactor]:
        """Assess infrastructure-related risks"""
        risks = []
        
        targets = deployment_plan.get("targets", [])
        
        # Multi-environment deployment risk
        if len(targets) > 1:
            risks.append(RiskFactor(
                name="multi_environment_deployment",
                category="infrastructure",
                severity=0.4,
                confidence=0.7,
                description=f"Deploying to {len(targets)} environments simultaneously",
                mitigation_suggestions=[
                    "Consider staged deployment",
                    "Implement canary deployment",
                    "Ensure rollback procedures are tested"
                ]
            ))
        
        # Production deployment risk
        prod_targets = [t for t in targets if t.get("environment") == "production"]
        if prod_targets:
            risks.append(RiskFactor(
                name="production_deployment",
                category="infrastructure",
                severity=0.6,
                confidence=0.9,
                description="Deploying to production environment",
                mitigation_suggestions=[
                    "Ensure staging deployment was successful",
                    "Have rollback plan ready",
                    "Monitor key metrics during deployment"
                ]
            ))
        
        return risks
    
    async def _assess_process_risks(self, deployment_plan: Dict[str, Any]) -> List[RiskFactor]:
        """Assess process-related risks"""
        risks = []
        
        strategy = deployment_plan.get("strategy", {})
        
        # Approval process risk
        if not strategy.get("approval_required", False):
            risks.append(RiskFactor(
                name="no_approval_process",
                category="process",
                severity=0.5,
                confidence=0.8,
                description="No approval process configured for deployment",
                mitigation_suggestions=[
                    "Implement approval workflow",
                    "Require peer review",
                    "Add automated quality gates"
                ]
            ))
        
        # Rollback strategy risk
        rollback_strategy = deployment_plan.get("rollback_strategy", {})
        if not rollback_strategy.get("automatic", False):
            risks.append(RiskFactor(
                name="manual_rollback_only",
                category="process",
                severity=0.4,
                confidence=0.7,
                description="Only manual rollback configured",
                mitigation_suggestions=[
                    "Enable automatic rollback",
                    "Configure health check triggers",
                    "Test rollback procedures"
                ]
            ))
        
        return risks
    
    async def _assess_historical_risks(self, application: str, version: str) -> List[RiskFactor]:
        """Assess risks based on historical data"""
        risks = []
        
        # Mock historical analysis - would query actual historical data
        if self.historical_data:
            # Simulate historical failure rate
            historical_failure_rate = 0.15  # 15% failure rate
            
            if historical_failure_rate > 0.1:
                risks.append(RiskFactor(
                    name="historical_failure_rate",
                    category="historical",
                    severity=historical_failure_rate,
                    confidence=0.9,
                    description=f"Application has {historical_failure_rate*100:.1f}% historical failure rate",
                    historical_impact=historical_failure_rate,
                    mitigation_suggestions=[
                        "Review previous failure causes",
                        "Implement additional testing",
                        "Consider gradual rollout"
                    ]
                ))
        
        return risks
    
    def _calculate_overall_risk(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall risk score from individual factors"""
        if not risk_factors:
            return 0.1  # Minimum base risk
        
        # Weighted average of risk factors
        total_weight = 0
        weighted_risk = 0
        
        for factor in risk_factors:
            weight = self.factor_weights.get(factor.name, 0.1)
            weighted_risk += factor.severity * factor.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.1
        
        overall_risk = weighted_risk / total_weight
        return min(max(overall_risk, 0.0), 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score >= self.risk_thresholds["critical"]:
            return "critical"
        elif risk_score >= self.risk_thresholds["high"]:
            return "high"
        elif risk_score >= self.risk_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def _calculate_confidence(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall confidence in the assessment"""
        if not risk_factors:
            return 0.5
        
        avg_confidence = sum(factor.confidence for factor in risk_factors) / len(risk_factors)
        return avg_confidence
    
    def _generate_mitigation_strategies(self, risk_factors: List[RiskFactor]) -> List[MitigationStrategy]:
        """Generate mitigation strategies based on risk factors"""
        strategies = []
        
        # Group risk factors by category
        categories = {}
        for factor in risk_factors:
            if factor.category not in categories:
                categories[factor.category] = []
            categories[factor.category].append(factor)
        
        # Generate strategies for each category
        for category, factors in categories.items():
            if category == "code":
                strategies.append(MitigationStrategy(
                    name="Enhanced Code Review",
                    description="Implement thorough code review process",
                    effort_level="medium",
                    time_estimate_hours=4,
                    effectiveness=0.7,
                    steps=[
                        "Assign senior developer for review",
                        "Check code complexity metrics",
                        "Verify test coverage requirements",
                        "Review security implications"
                    ]
                ))
            elif category == "infrastructure":
                strategies.append(MitigationStrategy(
                    name="Staged Deployment",
                    description="Deploy in stages with validation",
                    effort_level="low",
                    time_estimate_hours=2,
                    effectiveness=0.8,
                    steps=[
                        "Deploy to staging first",
                        "Run smoke tests",
                        "Monitor key metrics",
                        "Proceed to production if successful"
                    ]
                ))
        
        return strategies
    
    def _generate_recommendations(self, risk_factors: List[RiskFactor], risk_level: str) -> List[str]:
        """Generate recommendations based on risk assessment"""
        recommendations = []
        
        if risk_level == "critical":
            recommendations.extend([
                "Consider postponing deployment until risks are mitigated",
                "Implement comprehensive rollback plan",
                "Have incident response team on standby"
            ])
        elif risk_level == "high":
            recommendations.extend([
                "Implement additional testing before deployment",
                "Consider canary deployment strategy",
                "Monitor deployment closely"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Ensure rollback procedures are ready",
                "Monitor key metrics during deployment"
            ])
        
        # Add specific recommendations based on risk factors
        for factor in risk_factors:
            if factor.severity > 0.7:
                recommendations.extend(factor.mitigation_suggestions[:2])
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _get_historical_context(self, application: str) -> Dict[str, Any]:
        """Get historical context for the application"""
        # Mock historical context - would query actual data
        return {
            "total_deployments": 45,
            "successful_deployments": 38,
            "failed_deployments": 7,
            "average_deployment_time_minutes": 12,
            "last_failure_date": "2024-01-15",
            "common_failure_reasons": [
                "Database migration issues",
                "Configuration errors",
                "Dependency conflicts"
            ]
        }
    
    def _is_critical_file(self, file_path: str) -> bool:
        """Check if a file is considered critical"""
        critical_patterns = [
            "config", "database", "migration", "security", 
            "auth", "payment", "core", "main"
        ]
        return any(pattern in file_path.lower() for pattern in critical_patterns)