"""Failure Handling and Recovery System

Provides intelligent failure detection, analysis, and recovery mechanisms for workflow execution.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import traceback
import logging
from collections import defaultdict


class FailureType(Enum):
    """Types of failures that can occur"""
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    DATA_ERROR = "data_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure types"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SKIP = "skip"
    ROLLBACK = "rollback"
    COMPENSATE = "compensate"
    ESCALATE = "escalate"
    FAIL_FAST = "fail_fast"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class FailureContext:
    """Context information about a failure"""
    node_id: str
    failure_type: FailureType
    error_message: str
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attempt_number: int = 1
    previous_attempts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """Recovery action to be taken"""
    strategy: RecoveryStrategy
    delay_seconds: float = 0.0
    max_attempts: int = 3
    parameters: Dict[str, Any] = field(default_factory=dict)
    escalation_threshold: int = 5
    circuit_breaker_threshold: int = 10


@dataclass
class FailurePattern:
    """Pattern for matching and handling specific failure types"""
    name: str
    failure_type: FailureType
    error_patterns: List[str]  # Regex patterns to match error messages
    recovery_action: RecoveryAction
    priority: int = 1  # Higher priority patterns are checked first
    conditions: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker implementation for failure handling"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        elif self.state == "half_open":
            return True
        return False
    
    def record_success(self) -> None:
        """Record a successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self) -> None:
        """Record a failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half_open":
            self.state = "open"


class FailureHandler:
    """Intelligent failure handling and recovery system"""
    
    def __init__(self):
        """Initialize failure handler"""
        self.failure_patterns: List[FailurePattern] = []
        self.failure_history: List[FailureContext] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_callbacks: Dict[str, Callable] = {}
        self.escalation_handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize default failure patterns
        self._initialize_default_patterns()
    
    def _initialize_default_patterns(self) -> None:
        """Initialize default failure patterns and recovery strategies"""
        default_patterns = [
            FailurePattern(
                name="timeout_retry",
                failure_type=FailureType.TIMEOUT,
                error_patterns=[r"timeout", r"timed out", r"deadline exceeded"],
                recovery_action=RecoveryAction(
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    delay_seconds=5.0,
                    max_attempts=3
                ),
                priority=1
            ),
            FailurePattern(
                name="resource_exhaustion_wait",
                failure_type=FailureType.RESOURCE_EXHAUSTION,
                error_patterns=[r"out of memory", r"disk full", r"resource limit"],
                recovery_action=RecoveryAction(
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    delay_seconds=30.0,
                    max_attempts=2
                ),
                priority=1
            ),
            FailurePattern(
                name="network_error_retry",
                failure_type=FailureType.NETWORK_ERROR,
                error_patterns=[r"connection refused", r"network unreachable", r"dns resolution"],
                recovery_action=RecoveryAction(
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    delay_seconds=10.0,
                    max_attempts=5
                ),
                priority=1
            ),
            FailurePattern(
                name="authentication_escalate",
                failure_type=FailureType.AUTHENTICATION_ERROR,
                error_patterns=[r"unauthorized", r"authentication failed", r"invalid credentials"],
                recovery_action=RecoveryAction(
                    strategy=RecoveryStrategy.ESCALATE,
                    max_attempts=1
                ),
                priority=2
            ),
            FailurePattern(
                name="validation_skip",
                failure_type=FailureType.VALIDATION_ERROR,
                error_patterns=[r"validation failed", r"invalid input", r"schema error"],
                recovery_action=RecoveryAction(
                    strategy=RecoveryStrategy.SKIP,
                    max_attempts=1
                ),
                priority=1
            )
        ]
        
        self.failure_patterns.extend(default_patterns)
    
    def add_failure_pattern(self, pattern: FailurePattern) -> None:
        """Add a custom failure pattern"""
        self.failure_patterns.append(pattern)
        # Sort by priority (higher priority first)
        self.failure_patterns.sort(key=lambda p: p.priority, reverse=True)
    
    def add_recovery_callback(self, strategy: str, callback: Callable) -> None:
        """Add a custom recovery callback for a specific strategy"""
        self.recovery_callbacks[strategy] = callback
    
    def add_escalation_handler(self, handler: Callable) -> None:
        """Add an escalation handler for critical failures"""
        self.escalation_handlers.append(handler)
    
    async def handle_failure(self, node_id: str, error: Exception, 
                           context: Optional[Dict[str, Any]] = None) -> RecoveryAction:
        """Handle a failure and determine recovery action"""
        # Create failure context
        failure_context = self._create_failure_context(node_id, error, context)
        
        # Record failure in history
        self.failure_history.append(failure_context)
        
        # Update circuit breaker
        if node_id not in self.circuit_breakers:
            self.circuit_breakers[node_id] = CircuitBreaker()
        self.circuit_breakers[node_id].record_failure()
        
        # Analyze failure and determine recovery action
        recovery_action = await self._analyze_failure(failure_context)
        
        # Check circuit breaker
        if not self._check_circuit_breaker(node_id, recovery_action):
            recovery_action = RecoveryAction(
                strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                parameters={"reason": "Circuit breaker open"}
            )
        
        # Log failure and recovery action
        self.logger.error(
            f"Failure in node {node_id}: {failure_context.error_message}. "
            f"Recovery strategy: {recovery_action.strategy.value}"
        )
        
        return recovery_action
    
    def _create_failure_context(self, node_id: str, error: Exception, 
                              context: Optional[Dict[str, Any]] = None) -> FailureContext:
        """Create failure context from error information"""
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        # Classify failure type
        failure_type = self._classify_failure(error_message, error)
        
        # Get previous attempts for this node
        previous_attempts = [
            {
                "timestamp": fc.timestamp.isoformat(),
                "error_message": fc.error_message,
                "attempt_number": fc.attempt_number
            }
            for fc in self.failure_history
            if fc.node_id == node_id
        ]
        
        return FailureContext(
            node_id=node_id,
            failure_type=failure_type,
            error_message=error_message,
            stack_trace=stack_trace,
            attempt_number=len(previous_attempts) + 1,
            previous_attempts=previous_attempts,
            metadata=context or {}
        )
    
    def _classify_failure(self, error_message: str, error: Exception) -> FailureType:
        """Classify the type of failure based on error information"""
        error_message_lower = error_message.lower()
        
        # Check for specific error types
        if "timeout" in error_message_lower or "timed out" in error_message_lower:
            return FailureType.TIMEOUT
        elif "memory" in error_message_lower or "disk" in error_message_lower:
            return FailureType.RESOURCE_EXHAUSTION
        elif "connection" in error_message_lower or "network" in error_message_lower:
            return FailureType.NETWORK_ERROR
        elif "unauthorized" in error_message_lower or "authentication" in error_message_lower:
            return FailureType.AUTHENTICATION_ERROR
        elif "permission" in error_message_lower or "forbidden" in error_message_lower:
            return FailureType.PERMISSION_ERROR
        elif "validation" in error_message_lower or "invalid" in error_message_lower:
            return FailureType.VALIDATION_ERROR
        elif isinstance(error, (ValueError, TypeError)):
            return FailureType.DATA_ERROR
        else:
            return FailureType.UNKNOWN
    
    async def _analyze_failure(self, failure_context: FailureContext) -> RecoveryAction:
        """Analyze failure and determine appropriate recovery action"""
        # Check circuit breaker status first
        node_failures = [fc for fc in self.failure_history if fc.node_id == failure_context.node_id]
        if len(node_failures) >= 5:  # Circuit breaker threshold
            return RecoveryAction(
                strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                parameters={"reason": "Circuit breaker activated", "failure_count": len(node_failures)}
            )
        
        # Check for matching failure patterns
        for pattern in self.failure_patterns:
            if self._matches_pattern(failure_context, pattern):
                # Check if we've exceeded max attempts
                if failure_context.attempt_number > pattern.recovery_action.max_attempts:
                    return RecoveryAction(
                        strategy=RecoveryStrategy.ESCALATE,
                        parameters={"reason": "Max attempts exceeded", "original_strategy": pattern.recovery_action.strategy.value}
                    )
                
                return pattern.recovery_action
        
        # Default recovery action for unmatched failures
        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            delay_seconds=1.0,
            max_attempts=1
        )
    
    def _matches_pattern(self, failure_context: FailureContext, pattern: FailurePattern) -> bool:
        """Check if failure context matches a pattern"""
        # Check failure type
        if failure_context.failure_type != pattern.failure_type:
            return False
        
        # Check error message patterns
        import re
        for error_pattern in pattern.error_patterns:
            if re.search(error_pattern, failure_context.error_message, re.IGNORECASE):
                return True
        
        return False
    
    def _check_circuit_breaker(self, node_id: str, recovery_action: RecoveryAction) -> bool:
        """Check circuit breaker status for the node"""
        if node_id not in self.circuit_breakers:
            self.circuit_breakers[node_id] = CircuitBreaker(
                failure_threshold=recovery_action.circuit_breaker_threshold
            )
        
        circuit_breaker = self.circuit_breakers[node_id]
        return circuit_breaker.can_execute()
    
    async def execute_recovery(self, node_id: str, recovery_action: RecoveryAction, 
                             execution_func: Callable) -> Dict[str, Any]:
        """Execute the recovery action"""
        try:
            if recovery_action.strategy == RecoveryStrategy.RETRY:
                return await self._execute_retry(node_id, recovery_action, execution_func)
            
            elif recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                return await self._execute_retry_with_backoff(node_id, recovery_action, execution_func)
            
            elif recovery_action.strategy == RecoveryStrategy.SKIP:
                return await self._execute_skip(node_id, recovery_action)
            
            elif recovery_action.strategy == RecoveryStrategy.ESCALATE:
                return await self._execute_escalate(node_id, recovery_action)
            
            elif recovery_action.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                return await self._execute_circuit_breaker(node_id, recovery_action)
            
            else:
                # Check for custom recovery callbacks
                strategy_key = recovery_action.strategy.value if hasattr(recovery_action.strategy, 'value') else str(recovery_action.strategy)
                if strategy_key in self.recovery_callbacks:
                    callback = self.recovery_callbacks[strategy_key]
                    return await callback(node_id, recovery_action, execution_func)
                
                return {
                    "success": False,
                    "error": f"Unknown recovery strategy: {strategy_key}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Recovery execution failed: {str(e)}"
            }
    
    async def _execute_retry(self, node_id: str, recovery_action: RecoveryAction, 
                           execution_func: Callable) -> Dict[str, Any]:
        """Execute simple retry recovery"""
        last_error = None
        
        for attempt in range(recovery_action.max_attempts):
            if attempt > 0 and recovery_action.delay_seconds > 0:
                await asyncio.sleep(recovery_action.delay_seconds)
            
            try:
                result = await execution_func()
                self._record_recovery_success(node_id)
                return {"success": True, "result": result, "strategy": "retry", "attempts": attempt + 1}
            except Exception as e:
                last_error = e
                continue
        
        # All attempts failed
        self._record_recovery_failure(node_id)
        return {"success": False, "error": str(last_error), "strategy": "retry", "attempts": recovery_action.max_attempts}
    
    async def _execute_retry_with_backoff(self, node_id: str, recovery_action: RecoveryAction, 
                                        execution_func: Callable) -> Dict[str, Any]:
        """Execute retry with exponential backoff"""
        last_error = None
        max_delay = recovery_action.parameters.get("max_delay", 300)  # 5 minutes max
        
        for attempt in range(recovery_action.max_attempts):
            if attempt > 0:
                # Calculate backoff delay
                backoff_delay = recovery_action.delay_seconds * (2 ** (attempt - 1))
                delay = min(backoff_delay, max_delay)
                await asyncio.sleep(delay)
            
            try:
                result = await execution_func()
                self._record_recovery_success(node_id)
                return {"success": True, "result": result, "strategy": "retry_with_backoff", "attempts": attempt + 1}
            except Exception as e:
                last_error = e
                continue
        
        # All attempts failed
        self._record_recovery_failure(node_id)
        return {"success": False, "error": str(last_error), "strategy": "retry_with_backoff", "attempts": recovery_action.max_attempts}
    
    async def _execute_skip(self, node_id: str, recovery_action: RecoveryAction) -> Dict[str, Any]:
        """Execute skip recovery strategy"""
        self.logger.warning(f"Skipping failed node {node_id} due to recovery strategy")
        return {
            "success": True, 
            "result": {"skipped": True, "reason": "Recovery strategy: skip"}, 
            "strategy": "skip"
        }
    
    async def _execute_escalate(self, node_id: str, recovery_action: RecoveryAction) -> Dict[str, Any]:
        """Execute escalation recovery strategy"""
        escalation_info = {
            "node_id": node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "failure_count": len([fc for fc in self.failure_history if fc.node_id == node_id]),
            "recovery_action": recovery_action.parameters
        }
        
        # Notify escalation handlers
        for handler in self.escalation_handlers:
            try:
                await handler(escalation_info)
            except Exception as e:
                self.logger.error(f"Escalation handler failed: {str(e)}")
        
        return {
            "success": False, 
            "error": "Escalated to human intervention", 
            "strategy": "escalate",
            "escalation_info": escalation_info
        }
    
    async def _execute_circuit_breaker(self, node_id: str, recovery_action: RecoveryAction) -> Dict[str, Any]:
        """Execute circuit breaker recovery strategy"""
        return {
            "success": False,
            "error": "Circuit breaker is open - too many failures",
            "strategy": "circuit_breaker",
            "parameters": recovery_action.parameters
        }
    
    def _record_recovery_success(self, node_id: str) -> None:
        """Record successful recovery"""
        if node_id in self.circuit_breakers:
            self.circuit_breakers[node_id].record_success()
    
    def _record_recovery_failure(self, node_id: str) -> None:
        """Record failed recovery"""
        if node_id in self.circuit_breakers:
            self.circuit_breakers[node_id].record_failure()
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get comprehensive failure statistics"""
        if not self.failure_history:
            return {"total_failures": 0}
        
        # Group failures by type
        failures_by_type = defaultdict(int)
        failures_by_node = defaultdict(int)
        failures_by_hour = defaultdict(int)
        
        for failure in self.failure_history:
            failures_by_type[failure.failure_type.value] += 1
            failures_by_node[failure.node_id] += 1
            hour_key = failure.timestamp.strftime("%Y-%m-%d %H:00")
            failures_by_hour[hour_key] += 1
        
        # Calculate failure rates
        total_failures = len(self.failure_history)
        unique_nodes = len(set(fc.node_id for fc in self.failure_history))
        
        # Find most problematic nodes
        most_problematic = sorted(
            failures_by_node.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            "total_failures": total_failures,
            "unique_failed_nodes": unique_nodes,
            "failures_by_type": dict(failures_by_type),
            "failures_by_node": dict(failures_by_node),
            "failures_by_hour": dict(failures_by_hour),
            "most_problematic_nodes": most_problematic,
            "average_failures_per_node": total_failures / unique_nodes if unique_nodes > 0 else 0,
            "circuit_breakers_active": len([cb for cb in self.circuit_breakers.values() if cb.state == "open"])
        }
    
    def get_recovery_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving failure recovery"""
        recommendations = []
        stats = self.get_failure_statistics()
        
        # High failure rate recommendation
        if stats["total_failures"] > 100:
            recommendations.append({
                "type": "high_failure_rate",
                "priority": "high",
                "message": f"High failure rate detected ({stats['total_failures']} failures). Consider reviewing system stability.",
                "action": "Investigate root causes and improve error handling"
            })
        
        # Problematic nodes recommendation
        if stats["most_problematic_nodes"]:
            top_node, failure_count = stats["most_problematic_nodes"][0]
            if failure_count > 10:
                recommendations.append({
                    "type": "problematic_node",
                    "priority": "medium",
                    "message": f"Node '{top_node}' has {failure_count} failures. Consider optimization.",
                    "action": f"Review and optimize node '{top_node}' implementation"
                })
        
        # Circuit breaker recommendation
        if stats["circuit_breakers_active"] > 0:
            recommendations.append({
                "type": "circuit_breakers",
                "priority": "medium",
                "message": f"{stats['circuit_breakers_active']} circuit breakers are open.",
                "action": "Review and address underlying issues causing circuit breaker activation"
            })
        
        # Failure type analysis
        failures_by_type = stats["failures_by_type"]
        if failures_by_type.get("timeout", 0) > failures_by_type.get("network_error", 0) * 2:
            recommendations.append({
                "type": "timeout_issues",
                "priority": "medium",
                "message": "High number of timeout failures detected.",
                "action": "Consider increasing timeout values or optimizing slow operations"
            })
        
        return recommendations
    
    def reset_circuit_breaker(self, node_id: str) -> bool:
        """Manually reset a circuit breaker"""
        if node_id in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[node_id]
            circuit_breaker.failure_count = 0
            circuit_breaker.state = "closed"
            circuit_breaker.last_failure_time = None
            return True
        return False
    
    def clear_failure_history(self, node_id: Optional[str] = None, 
                            older_than: Optional[datetime] = None) -> int:
        """Clear failure history with optional filters"""
        original_count = len(self.failure_history)
        
        if node_id and older_than:
            self.failure_history = [
                fc for fc in self.failure_history 
                if fc.node_id != node_id or fc.timestamp >= older_than
            ]
        elif node_id:
            self.failure_history = [
                fc for fc in self.failure_history 
                if fc.node_id != node_id
            ]
        elif older_than:
            self.failure_history = [
                fc for fc in self.failure_history 
                if fc.timestamp >= older_than
            ]
        else:
            self.failure_history.clear()
        
        cleared_count = original_count - len(self.failure_history)
        return cleared_count