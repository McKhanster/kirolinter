"""
Quality Gate System

Intelligent quality gates that adapt to project needs and team practices
with contextual analysis and dynamic criteria adjustment.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class GateType(str, Enum):
    """Quality gate types"""
    PRE_COMMIT = "pre_commit"
    PRE_MERGE = "pre_merge"
    PRE_DEPLOY = "pre_deploy"
    POST_DEPLOY = "post_deploy"


class GateStatus(str, Enum):
    """Quality gate execution status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class GateContext:
    """Context for quality gate execution"""
    gate_type: GateType
    project_name: str
    branch: str = "main"
    commit_sha: str = ""
    environment: str = "development"
    triggered_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateCriteria:
    """Quality gate criteria definition"""
    name: str
    description: str
    threshold: float
    operator: str  # >=, <=, >, <, ==
    weight: float = 1.0
    required: bool = True
    adaptive: bool = False  # Whether threshold can be adjusted


@dataclass
class GateResult:
    """Quality gate execution result"""
    gate_id: str
    gate_type: GateType
    status: GateStatus
    overall_score: float
    criteria_results: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    message: str = ""
    recommendations: List[str] = field(default_factory=list)
    bypass_reason: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


class QualityGateSystem:
    """Intelligent quality gate system with contextual analysis"""
    
    def __init__(self, ai_provider=None, pattern_memory=None):
        """
        Initialize quality gate system
        
        Args:
            ai_provider: AI provider for intelligent analysis
            pattern_memory: Pattern memory for team-specific adaptations
        """
        self.ai = ai_provider
        self.memory = pattern_memory
        
        # Gate configurations
        self.gate_configs: Dict[GateType, Dict[str, Any]] = {}
        self.criteria_templates: Dict[str, GateCriteria] = {}
        
        # Historical data for adaptation
        self.execution_history: List[GateResult] = []
        
        # Initialize default configurations
        self._initialize_default_gates()
    
    async def execute_gate(self, gate_type: GateType, context: GateContext,
                          analysis_data: Dict[str, Any] = None) -> GateResult:
        """
        Execute a quality gate with contextual analysis
        
        Args:
            gate_type: Type of quality gate to execute
            context: Execution context
            analysis_data: Analysis data to evaluate against criteria
            
        Returns:
            GateResult: Complete gate execution result
        """
        logger.info(f"Executing {gate_type} quality gate for {context.project_name}")
        
        start_time = datetime.utcnow()
        
        # Get gate configuration
        gate_config = self.gate_configs.get(gate_type, {})
        if not gate_config:
            return GateResult(
                gate_id=f"{gate_type}_{int(start_time.timestamp())}",
                gate_type=gate_type,
                status=GateStatus.FAILED,
                overall_score=0.0,
                message=f"No configuration found for gate type: {gate_type}"
            )
        
        # Adapt criteria based on context and history
        adapted_criteria = await self._adapt_criteria(gate_type, context)
        
        # Execute criteria evaluation
        criteria_results = []
        total_score = 0.0
        total_weight = 0.0
        failed_required = False
        
        for criteria in adapted_criteria:
            result = await self._evaluate_criteria(criteria, analysis_data or {}, context)
            criteria_results.append(result)
            
            if result["passed"]:
                total_score += result["score"] * criteria.weight
            elif criteria.required:
                failed_required = True
            
            total_weight += criteria.weight
        
        # Calculate overall score
        overall_score = (total_score / total_weight) if total_weight > 0 else 0.0
        
        # Determine gate status
        if failed_required:
            status = GateStatus.FAILED
        elif overall_score >= gate_config.get("pass_threshold", 0.8):
            status = GateStatus.PASSED
        elif overall_score >= gate_config.get("warning_threshold", 0.6):
            status = GateStatus.WARNING
        else:
            status = GateStatus.FAILED
        
        # Generate recommendations
        recommendations = self._generate_recommendations(criteria_results, status)
        
        # Create result
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        result = GateResult(
            gate_id=f"{gate_type}_{context.project_name}_{int(start_time.timestamp())}",
            gate_type=gate_type,
            status=status,
            overall_score=overall_score,
            criteria_results=criteria_results,
            execution_time_seconds=execution_time,
            message=self._generate_status_message(status, overall_score, len(criteria_results)),
            recommendations=recommendations
        )
        
        # Store result for future adaptation
        self.execution_history.append(result)
        
        logger.info(f"Quality gate {gate_type} completed: {status} (score: {overall_score:.2f})")
        return result
    
    async def adapt_criteria(self, gate_type: GateType, 
                           historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Adapt quality gate criteria based on historical performance
        
        Args:
            gate_type: Gate type to adapt
            historical_data: Historical gate execution data
            
        Returns:
            Dict containing adaptation results
        """
        if not historical_data:
            return {"adapted": False, "reason": "No historical data available"}
        
        logger.info(f"Adapting criteria for {gate_type} based on {len(historical_data)} historical executions")
        
        # Analyze historical performance
        pass_rate = sum(1 for d in historical_data if d.get("status") == "passed") / len(historical_data)
        avg_score = sum(d.get("overall_score", 0) for d in historical_data) / len(historical_data)
        
        adaptations = []
        
        # Adjust thresholds based on performance
        if pass_rate < 0.5:  # Less than 50% pass rate
            # Criteria might be too strict
            adaptations.append({
                "type": "threshold_relaxation",
                "reason": f"Low pass rate ({pass_rate:.1%}) suggests overly strict criteria",
                "adjustment": "Relax thresholds by 10%"
            })
        elif pass_rate > 0.95:  # More than 95% pass rate
            # Criteria might be too lenient
            adaptations.append({
                "type": "threshold_tightening",
                "reason": f"High pass rate ({pass_rate:.1%}) suggests criteria could be more rigorous",
                "adjustment": "Tighten thresholds by 5%"
            })
        
        # Analyze specific criteria performance
        criteria_performance = {}
        for execution in historical_data:
            for criteria_result in execution.get("criteria_results", []):
                criteria_name = criteria_result.get("name", "unknown")
                if criteria_name not in criteria_performance:
                    criteria_performance[criteria_name] = []
                criteria_performance[criteria_name].append(criteria_result.get("passed", False))
        
        # Identify problematic criteria
        for criteria_name, results in criteria_performance.items():
            criteria_pass_rate = sum(results) / len(results) if results else 0
            if criteria_pass_rate < 0.3:  # Less than 30% pass rate
                adaptations.append({
                    "type": "criteria_adjustment",
                    "criteria": criteria_name,
                    "reason": f"Criteria '{criteria_name}' has low pass rate ({criteria_pass_rate:.1%})",
                    "adjustment": "Consider relaxing or reviewing this criteria"
                })
        
        return {
            "adapted": len(adaptations) > 0,
            "adaptations": adaptations,
            "historical_pass_rate": pass_rate,
            "historical_avg_score": avg_score,
            "recommendations": self._generate_adaptation_recommendations(adaptations)
        }
    
    def configure_gate(self, gate_type: GateType, configuration: Dict[str, Any]):
        """Configure a quality gate"""
        self.gate_configs[gate_type] = configuration
        logger.info(f"Configured quality gate: {gate_type}")
    
    def add_criteria_template(self, criteria: GateCriteria):
        """Add a criteria template"""
        self.criteria_templates[criteria.name] = criteria
        logger.info(f"Added criteria template: {criteria.name}")
    
    async def _adapt_criteria(self, gate_type: GateType, context: GateContext) -> List[GateCriteria]:
        """Adapt criteria based on context and historical data"""
        base_criteria = self._get_base_criteria(gate_type)
        
        # Apply team-specific adaptations if pattern memory is available
        if self.memory:
            # Mock team pattern adaptation - would use actual pattern data
            team_patterns = await self._get_team_patterns(context.project_name)
            if team_patterns:
                base_criteria = self._apply_team_patterns(base_criteria, team_patterns)
        
        return base_criteria
    
    def _get_base_criteria(self, gate_type: GateType) -> List[GateCriteria]:
        """Get base criteria for a gate type"""
        if gate_type == GateType.PRE_COMMIT:
            return [
                GateCriteria("code_coverage", "Code coverage percentage", 0.8, ">=", 1.0, True),
                GateCriteria("complexity", "Cyclomatic complexity", 10.0, "<=", 0.8, False),
                GateCriteria("security_issues", "Number of security issues", 0, "==", 1.2, True)
            ]
        elif gate_type == GateType.PRE_MERGE:
            return [
                GateCriteria("code_coverage", "Code coverage percentage", 0.85, ">=", 1.0, True),
                GateCriteria("test_pass_rate", "Test pass rate", 0.95, ">=", 1.2, True),
                GateCriteria("code_smells", "Number of code smells", 5, "<=", 0.8, False),
                GateCriteria("duplication", "Code duplication percentage", 0.05, "<=", 0.6, False)
            ]
        elif gate_type == GateType.PRE_DEPLOY:
            return [
                GateCriteria("code_coverage", "Code coverage percentage", 0.9, ">=", 1.0, True),
                GateCriteria("test_pass_rate", "Test pass rate", 0.98, ">=", 1.5, True),
                GateCriteria("security_issues", "Number of security issues", 0, "==", 1.5, True),
                GateCriteria("performance_regression", "Performance regression", 0.1, "<=", 1.0, True)
            ]
        elif gate_type == GateType.POST_DEPLOY:
            return [
                GateCriteria("deployment_success", "Deployment success rate", 1.0, "==", 2.0, True),
                GateCriteria("error_rate", "Error rate", 0.01, "<=", 1.5, True),
                GateCriteria("response_time", "Response time (ms)", 500, "<=", 1.0, False)
            ]
        else:
            return []
    
    async def _evaluate_criteria(self, criteria: GateCriteria, analysis_data: Dict[str, Any],
                               context: GateContext) -> Dict[str, Any]:
        """Evaluate a single criteria"""
        # Get value from analysis data
        value = analysis_data.get(criteria.name, 0)
        
        # Evaluate against threshold
        passed = False
        if criteria.operator == ">=":
            passed = value >= criteria.threshold
        elif criteria.operator == "<=":
            passed = value <= criteria.threshold
        elif criteria.operator == ">":
            passed = value > criteria.threshold
        elif criteria.operator == "<":
            passed = value < criteria.threshold
        elif criteria.operator == "==":
            passed = abs(value - criteria.threshold) < 0.001
        
        # Calculate score (0.0 to 1.0)
        if passed:
            score = 1.0
        else:
            # Partial score based on how close to threshold
            if criteria.operator in [">=", ">"]:
                score = max(0.0, value / criteria.threshold) if criteria.threshold > 0 else 0.0
            elif criteria.operator in ["<=", "<"]:
                score = max(0.0, 1.0 - (value - criteria.threshold) / criteria.threshold) if criteria.threshold > 0 else 0.0
            else:
                score = 0.0
        
        return {
            "name": criteria.name,
            "description": criteria.description,
            "value": value,
            "threshold": criteria.threshold,
            "operator": criteria.operator,
            "passed": passed,
            "score": score,
            "weight": criteria.weight,
            "required": criteria.required
        }
    
    def _generate_recommendations(self, criteria_results: List[Dict[str, Any]], 
                                status: GateStatus) -> List[str]:
        """Generate recommendations based on criteria results"""
        recommendations = []
        
        if status == GateStatus.FAILED:
            failed_criteria = [c for c in criteria_results if not c["passed"] and c["required"]]
            for criteria in failed_criteria:
                if criteria["name"] == "code_coverage":
                    recommendations.append(f"Increase code coverage to at least {criteria['threshold']:.1%}")
                elif criteria["name"] == "test_pass_rate":
                    recommendations.append("Fix failing tests before proceeding")
                elif criteria["name"] == "security_issues":
                    recommendations.append("Resolve all security issues before deployment")
                else:
                    recommendations.append(f"Address {criteria['name']}: {criteria['description']}")
        
        elif status == GateStatus.WARNING:
            warning_criteria = [c for c in criteria_results if not c["passed"]]
            for criteria in warning_criteria:
                recommendations.append(f"Consider improving {criteria['name']}: current {criteria['value']}, target {criteria['threshold']}")
        
        return recommendations
    
    def _generate_status_message(self, status: GateStatus, score: float, 
                               criteria_count: int) -> str:
        """Generate status message for gate result"""
        if status == GateStatus.PASSED:
            return f"Quality gate passed with score {score:.1%} ({criteria_count} criteria evaluated)"
        elif status == GateStatus.WARNING:
            return f"Quality gate passed with warnings (score: {score:.1%})"
        elif status == GateStatus.FAILED:
            return f"Quality gate failed (score: {score:.1%})"
        else:
            return f"Quality gate {status.value}"
    
    async def _get_team_patterns(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get team patterns from memory"""
        # Mock team pattern retrieval - would use actual pattern memory
        return {
            "preferred_coverage_threshold": 0.85,
            "complexity_tolerance": 12.0,
            "test_reliability": 0.96
        }
    
    def _apply_team_patterns(self, criteria: List[GateCriteria], 
                           patterns: Dict[str, Any]) -> List[GateCriteria]:
        """Apply team patterns to criteria"""
        adapted_criteria = []
        
        for c in criteria:
            adapted = GateCriteria(
                name=c.name,
                description=c.description,
                threshold=c.threshold,
                operator=c.operator,
                weight=c.weight,
                required=c.required,
                adaptive=c.adaptive
            )
            
            # Apply team-specific adjustments
            if c.name == "code_coverage" and "preferred_coverage_threshold" in patterns:
                adapted.threshold = patterns["preferred_coverage_threshold"]
            elif c.name == "complexity" and "complexity_tolerance" in patterns:
                adapted.threshold = patterns["complexity_tolerance"]
            elif c.name == "test_pass_rate" and "test_reliability" in patterns:
                adapted.threshold = patterns["test_reliability"]
            
            adapted_criteria.append(adapted)
        
        return adapted_criteria
    
    def _generate_adaptation_recommendations(self, adaptations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on adaptations"""
        recommendations = []
        
        for adaptation in adaptations:
            if adaptation["type"] == "threshold_relaxation":
                recommendations.append("Consider reviewing team processes to improve quality gate pass rates")
            elif adaptation["type"] == "threshold_tightening":
                recommendations.append("Quality standards could be raised to drive further improvement")
            elif adaptation["type"] == "criteria_adjustment":
                recommendations.append(f"Review criteria '{adaptation['criteria']}' for relevance and achievability")
        
        return recommendations
    
    def _initialize_default_gates(self):
        """Initialize default gate configurations"""
        self.gate_configs = {
            GateType.PRE_COMMIT: {
                "pass_threshold": 0.8,
                "warning_threshold": 0.6,
                "timeout_seconds": 300
            },
            GateType.PRE_MERGE: {
                "pass_threshold": 0.85,
                "warning_threshold": 0.7,
                "timeout_seconds": 600
            },
            GateType.PRE_DEPLOY: {
                "pass_threshold": 0.9,
                "warning_threshold": 0.8,
                "timeout_seconds": 900
            },
            GateType.POST_DEPLOY: {
                "pass_threshold": 0.95,
                "warning_threshold": 0.85,
                "timeout_seconds": 1200
            }
        }