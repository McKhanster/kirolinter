"""
Failure Recovery System

Provides intelligent failure recovery strategies and execution.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from ..models.workflow import WorkflowDefinition, WorkflowResult, WorkflowStatus, StageResult

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Types of workflow failures"""
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    """Recovery strategies"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SKIP_STAGE = "skip_stage"
    ROLLBACK = "rollback"
    MANUAL_INTERVENTION = "manual_intervention"
    FAIL_FAST = "fail_fast"


@dataclass
class FailureContext:
    """Context information about a failure"""
    workflow_id: str
    execution_id: str
    stage_id: Optional[str] = None
    failure_type: FailureType = FailureType.UNKNOWN
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    previous_failures: List[str] = field(default_factory=list)


@dataclass
class RecoveryAction:
    """Recovery action to be taken"""
    strategy: RecoveryStrategy
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_duration_seconds: int = 0
    success_probability: float = 0.0
    requires_approval: bool = False


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    action: RecoveryAction
    success: bool
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    executed_at: datetime = field(default_factory=datetime.utcnow)


class FailureRecoveryEngine:
    """Intelligent failure recovery engine"""
    
    def __init__(self, redis_client=None, ai_provider=None):
        """
        Initialize failure recovery engine
        
        Args:
            redis_client: Redis client for storing recovery history
            ai_provider: AI provider for intelligent recovery decisions
        """
        self.redis = redis_client
        self.ai = ai_provider
        
        # Recovery configuration
        self.max_retry_attempts = 3
        self.retry_backoff_multiplier = 2.0
        self.max_backoff_seconds = 300
        
        # Recovery history
        self.recovery_history: Dict[str, List[RecoveryResult]] = {}
        
        # Failure patterns
        self.failure_patterns = self._initialize_failure_patterns()
    
    async def analyze_failure(self, failure_context: FailureContext) -> FailureType:
        """
        Analyze failure and determine failure type
        
        Args:
            failure_context: Context about the failure
            
        Returns:
            FailureType: Classified failure type
        """
        error_message = failure_context.error_message.lower()
        
        # Pattern matching for failure classification
        if any(keyword in error_message for keyword in ["timeout", "timed out", "deadline"]):
            return FailureType.TIMEOUT
        elif any(keyword in error_message for keyword in ["memory", "disk", "cpu", "resource"]):
            return FailureType.RESOURCE_EXHAUSTION
        elif any(keyword in error_message for keyword in ["auth", "permission", "unauthorized", "forbidden"]):
            return FailureType.AUTHENTICATION
        elif any(keyword in error_message for keyword in ["network", "connection", "dns", "unreachable"]):
            return FailureType.NETWORK
        elif any(keyword in error_message for keyword in ["dependency", "import", "module", "package"]):
            return FailureType.DEPENDENCY
        elif any(keyword in error_message for keyword in ["validation", "invalid", "malformed", "syntax"]):
            return FailureType.VALIDATION
        else:
            return FailureType.UNKNOWN
    
    async def generate_recovery_strategy(self, failure_context: FailureContext) -> RecoveryAction:
        """
        Generate intelligent recovery strategy
        
        Args:
            failure_context: Context about the failure
            
        Returns:
            RecoveryAction: Recommended recovery action
        """
        failure_type = await self.analyze_failure(failure_context)
        failure_context.failure_type = failure_type
        
        # Get historical success rates for this failure type
        historical_success = await self._get_historical_success_rate(failure_type, failure_context)
        
        # Generate strategy based on failure type and history
        if failure_type == FailureType.TIMEOUT:
            return await self._handle_timeout_failure(failure_context, historical_success)
        elif failure_type == FailureType.RESOURCE_EXHAUSTION:
            return await self._handle_resource_failure(failure_context, historical_success)
        elif failure_type == FailureType.AUTHENTICATION:
            return await self._handle_auth_failure(failure_context, historical_success)
        elif failure_type == FailureType.NETWORK:
            return await self._handle_network_failure(failure_context, historical_success)
        elif failure_type == FailureType.DEPENDENCY:
            return await self._handle_dependency_failure(failure_context, historical_success)
        elif failure_type == FailureType.VALIDATION:
            return await self._handle_validation_failure(failure_context, historical_success)
        else:
            return await self._handle_unknown_failure(failure_context, historical_success)
    
    async def execute_recovery(self, recovery_action: RecoveryAction,
                             failure_context: FailureContext) -> RecoveryResult:
        """
        Execute recovery action
        
        Args:
            recovery_action: Recovery action to execute
            failure_context: Original failure context
            
        Returns:
            RecoveryResult: Result of recovery attempt
        """
        start_time = datetime.utcnow()
        
        try:
            if recovery_action.strategy == RecoveryStrategy.RETRY:
                success = await self._execute_retry(recovery_action, failure_context)
            elif recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                success = await self._execute_retry_with_backoff(recovery_action, failure_context)
            elif recovery_action.strategy == RecoveryStrategy.SKIP_STAGE:
                success = await self._execute_skip_stage(recovery_action, failure_context)
            elif recovery_action.strategy == RecoveryStrategy.ROLLBACK:
                success = await self._execute_rollback(recovery_action, failure_context)
            elif recovery_action.strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                success = await self._request_manual_intervention(recovery_action, failure_context)
            else:
                success = False
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = RecoveryResult(
                action=recovery_action,
                success=success,
                duration_seconds=duration
            )
            
            # Store recovery result
            await self._store_recovery_result(failure_context, result)
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = RecoveryResult(
                action=recovery_action,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
            
            await self._store_recovery_result(failure_context, result)
            return result
    
    async def _handle_timeout_failure(self, context: FailureContext,
                                    historical_success: float) -> RecoveryAction:
        """Handle timeout failures"""
        if context.retry_count < self.max_retry_attempts and historical_success > 0.3:
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                description=f"Retry with exponential backoff (attempt {context.retry_count + 1})",
                parameters={
                    "backoff_seconds": min(
                        self.retry_backoff_multiplier ** context.retry_count * 10,
                        self.max_backoff_seconds
                    ),
                    "timeout_multiplier": 1.5
                },
                estimated_duration_seconds=60,
                success_probability=historical_success * 0.8
            )
        else:
            return RecoveryAction(
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                description="Timeout persists, manual intervention required",
                requires_approval=True,
                success_probability=0.9
            )
    
    async def _handle_resource_failure(self, context: FailureContext,
                                     historical_success: float) -> RecoveryAction:
        """Handle resource exhaustion failures"""
        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            description="Wait for resources to become available",
            parameters={
                "backoff_seconds": 30,
                "resource_check": True
            },
            estimated_duration_seconds=60,
            success_probability=0.7
        )
    
    async def _handle_auth_failure(self, context: FailureContext,
                                 historical_success: float) -> RecoveryAction:
        """Handle authentication failures"""
        return RecoveryAction(
            strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            description="Authentication failure requires manual credential update",
            requires_approval=True,
            success_probability=0.95
        )
    
    async def _handle_network_failure(self, context: FailureContext,
                                    historical_success: float) -> RecoveryAction:
        """Handle network failures"""
        if context.retry_count < 2:
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                description="Retry after network connectivity issue",
                parameters={
                    "backoff_seconds": 15,
                    "network_check": True
                },
                estimated_duration_seconds=30,
                success_probability=0.6
            )
        else:
            return RecoveryAction(
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                description="Persistent network issues require investigation",
                requires_approval=True,
                success_probability=0.8
            )
    
    async def _handle_dependency_failure(self, context: FailureContext,
                                       historical_success: float) -> RecoveryAction:
        """Handle dependency failures"""
        return RecoveryAction(
            strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            description="Dependency issue requires manual resolution",
            parameters={"dependency_check": True},
            requires_approval=True,
            success_probability=0.85
        )
    
    async def _handle_validation_failure(self, context: FailureContext,
                                       historical_success: float) -> RecoveryAction:
        """Handle validation failures"""
        return RecoveryAction(
            strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            description="Validation failure requires code or configuration fix",
            requires_approval=True,
            success_probability=0.9
        )
    
    async def _handle_unknown_failure(self, context: FailureContext,
                                    historical_success: float) -> RecoveryAction:
        """Handle unknown failures"""
        if context.retry_count < 1:
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Single retry for unknown failure",
                estimated_duration_seconds=30,
                success_probability=0.3
            )
        else:
            return RecoveryAction(
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                description="Unknown failure requires investigation",
                requires_approval=True,
                success_probability=0.7
            )
    
    async def _execute_retry(self, action: RecoveryAction, context: FailureContext) -> bool:
        """Execute simple retry"""
        logger.info(f"Executing retry for {context.workflow_id}")
        # In real implementation, this would re-execute the failed stage
        await asyncio.sleep(1)  # Simulate retry delay
        return True  # Mock success
    
    async def _execute_retry_with_backoff(self, action: RecoveryAction,
                                        context: FailureContext) -> bool:
        """Execute retry with backoff"""
        backoff_seconds = action.parameters.get("backoff_seconds", 10)
        logger.info(f"Executing retry with {backoff_seconds}s backoff for {context.workflow_id}")
        
        await asyncio.sleep(min(backoff_seconds, 5))  # Simulate backoff (capped for testing)
        return True  # Mock success
    
    async def _execute_skip_stage(self, action: RecoveryAction, context: FailureContext) -> bool:
        """Execute stage skip"""
        logger.info(f"Skipping failed stage {context.stage_id} for {context.workflow_id}")
        return True
    
    async def _execute_rollback(self, action: RecoveryAction, context: FailureContext) -> bool:
        """Execute rollback"""
        logger.info(f"Executing rollback for {context.workflow_id}")
        # In real implementation, this would rollback changes
        await asyncio.sleep(2)  # Simulate rollback time
        return True
    
    async def _request_manual_intervention(self, action: RecoveryAction,
                                         context: FailureContext) -> bool:
        """Request manual intervention"""
        logger.warning(f"Manual intervention requested for {context.workflow_id}: {action.description}")
        # In real implementation, this would create a ticket or notification
        return False  # Manual intervention pending
    
    async def _get_historical_success_rate(self, failure_type: FailureType,
                                         context: FailureContext) -> float:
        """Get historical success rate for failure type"""
        # Mock historical data - in real implementation, this would query Redis/database
        success_rates = {
            FailureType.TIMEOUT: 0.6,
            FailureType.RESOURCE_EXHAUSTION: 0.7,
            FailureType.AUTHENTICATION: 0.1,
            FailureType.NETWORK: 0.5,
            FailureType.DEPENDENCY: 0.3,
            FailureType.VALIDATION: 0.2,
            FailureType.UNKNOWN: 0.3
        }
        
        return success_rates.get(failure_type, 0.3)
    
    async def _store_recovery_result(self, context: FailureContext, result: RecoveryResult):
        """Store recovery result for future analysis"""
        key = f"{context.workflow_id}:{context.execution_id}"
        
        if key not in self.recovery_history:
            self.recovery_history[key] = []
        
        self.recovery_history[key].append(result)
        
        # In real implementation, this would store to Redis
        logger.debug(f"Stored recovery result for {key}: {result.success}")
    
    def _initialize_failure_patterns(self) -> Dict[str, Any]:
        """Initialize failure pattern recognition"""
        return {
            "timeout_keywords": ["timeout", "timed out", "deadline", "expired"],
            "resource_keywords": ["memory", "disk", "cpu", "resource", "quota", "limit"],
            "auth_keywords": ["auth", "permission", "unauthorized", "forbidden", "token"],
            "network_keywords": ["network", "connection", "dns", "unreachable", "refused"],
            "dependency_keywords": ["dependency", "import", "module", "package", "not found"],
            "validation_keywords": ["validation", "invalid", "malformed", "syntax", "format"]
        }
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        total_recoveries = sum(len(results) for results in self.recovery_history.values())
        successful_recoveries = sum(
            sum(1 for result in results if result.success)
            for results in self.recovery_history.values()
        )
        
        success_rate = (successful_recoveries / total_recoveries) if total_recoveries > 0 else 0
        
        return {
            "total_recovery_attempts": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "success_rate": success_rate,
            "active_workflows": len(self.recovery_history)
        }