"""
Tests for Failure Handler

Comprehensive tests for failure detection, analysis, and recovery functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from kirolinter.devops.orchestration.failure_handler import (
    FailureHandler, FailureContext, RecoveryAction, FailurePattern,
    CircuitBreaker, FailureType, RecoveryStrategy
)


class TestFailureHandler:
    """Test cases for FailureHandler"""
    
    @pytest.fixture
    def failure_handler(self):
        """Create a failure handler instance for testing"""
        return FailureHandler()
    
    @pytest.fixture
    def sample_failure_context(self):
        """Create a sample failure context"""
        return FailureContext(
            node_id="test_node_1",
            failure_type=FailureType.TIMEOUT,
            error_message="Operation timed out after 300 seconds",
            stack_trace="Traceback...",
            attempt_number=1,
            metadata={"timeout_seconds": 300}
        )
    
    def test_initialization(self, failure_handler):
        """Test failure handler initialization"""
        assert len(failure_handler.failure_patterns) > 0
        assert len(failure_handler.failure_history) == 0
        assert len(failure_handler.circuit_breakers) == 0
        
        # Check default patterns are loaded
        pattern_types = [p.failure_type for p in failure_handler.failure_patterns]
        assert FailureType.TIMEOUT in pattern_types
        assert FailureType.NETWORK_ERROR in pattern_types
        assert FailureType.AUTHENTICATION_ERROR in pattern_types
    
    def test_add_failure_pattern(self, failure_handler):
        """Test adding custom failure patterns"""
        custom_pattern = FailurePattern(
            name="custom_database_error",
            failure_type=FailureType.DATA_ERROR,
            error_patterns=[r"database connection failed", r"sql error"],
            recovery_action=RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                delay_seconds=10.0,
                max_attempts=3
            ),
            priority=2
        )
        
        initial_count = len(failure_handler.failure_patterns)
        failure_handler.add_failure_pattern(custom_pattern)
        
        assert len(failure_handler.failure_patterns) == initial_count + 1
        
        # Verify patterns are sorted by priority
        priorities = [p.priority for p in failure_handler.failure_patterns]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_add_recovery_callback(self, failure_handler):
        """Test adding custom recovery callbacks"""
        mock_callback = AsyncMock()
        
        failure_handler.add_recovery_callback("custom_strategy", mock_callback)
        
        assert "custom_strategy" in failure_handler.recovery_callbacks
        assert failure_handler.recovery_callbacks["custom_strategy"] == mock_callback
    
    def test_add_escalation_handler(self, failure_handler):
        """Test adding escalation handlers"""
        mock_handler = AsyncMock()
        
        failure_handler.add_escalation_handler(mock_handler)
        
        assert len(failure_handler.escalation_handlers) == 1
        assert failure_handler.escalation_handlers[0] == mock_handler
    
    @pytest.mark.asyncio
    async def test_handle_failure_timeout(self, failure_handler):
        """Test handling timeout failures"""
        timeout_error = TimeoutError("Operation timed out")
        
        recovery_action = await failure_handler.handle_failure(
            "timeout_node", timeout_error, {"operation": "data_processing"}
        )
        
        assert recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert recovery_action.delay_seconds > 0
        assert recovery_action.max_attempts > 0
        
        # Verify failure is recorded
        assert len(failure_handler.failure_history) == 1
        assert failure_handler.failure_history[0].failure_type == FailureType.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_handle_failure_network_error(self, failure_handler):
        """Test handling network errors"""
        network_error = ConnectionError("Connection refused")
        
        recovery_action = await failure_handler.handle_failure(
            "network_node", network_error, {"endpoint": "api.example.com"}
        )
        
        assert recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert recovery_action.delay_seconds >= 10.0  # Network errors have longer delay
        
        # Verify failure classification
        failure_record = failure_handler.failure_history[-1]
        assert failure_record.failure_type == FailureType.NETWORK_ERROR
    
    @pytest.mark.asyncio
    async def test_handle_failure_authentication_error(self, failure_handler):
        """Test handling authentication errors"""
        auth_error = PermissionError("Authentication failed")
        
        recovery_action = await failure_handler.handle_failure(
            "auth_node", auth_error, {"service": "oauth_provider"}
        )
        
        assert recovery_action.strategy == RecoveryStrategy.ESCALATE
        assert recovery_action.max_attempts == 1  # Don't retry auth errors
        
        # Verify failure classification
        failure_record = failure_handler.failure_history[-1]
        assert failure_record.failure_type == FailureType.AUTHENTICATION_ERROR
    
    @pytest.mark.asyncio
    async def test_handle_failure_unknown_error(self, failure_handler):
        """Test handling unknown error types"""
        unknown_error = RuntimeError("Something went wrong")
        
        recovery_action = await failure_handler.handle_failure(
            "unknown_node", unknown_error, {}
        )
        
        # Should default to simple retry
        assert recovery_action.strategy == RecoveryStrategy.RETRY
        assert recovery_action.max_attempts >= 1
        
        # Verify failure classification
        failure_record = failure_handler.failure_history[-1]
        assert failure_record.failure_type == FailureType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_execute_recovery_retry(self, failure_handler):
        """Test executing retry recovery strategy"""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            delay_seconds=0.1,  # Short delay for testing
            max_attempts=2
        )
        
        # Mock execution function that succeeds on retry
        call_count = 0
        async def mock_execution():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return {"success": True, "attempt": call_count}
        
        result = await failure_handler.execute_recovery(
            "retry_node", recovery_action, mock_execution
        )
        
        assert result["success"] is True
        assert result["strategy"] == "retry"
        assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_execute_recovery_retry_with_backoff(self, failure_handler):
        """Test executing retry with backoff recovery strategy"""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            delay_seconds=0.1,
            max_attempts=3
        )
        
        # Mock execution function that eventually succeeds
        call_count = 0
        async def mock_execution():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} fails")
            return {"success": True, "attempt": call_count}
        
        # Record start time to verify backoff delay
        start_time = datetime.utcnow()
        
        result = await failure_handler.execute_recovery(
            "backoff_node", recovery_action, mock_execution
        )
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        assert result["success"] is True
        assert result["strategy"] == "retry_with_backoff"
        assert call_count == 3
        # Should have some delay due to backoff
        assert execution_time > 0.1
    
    @pytest.mark.asyncio
    async def test_execute_recovery_skip(self, failure_handler):
        """Test executing skip recovery strategy"""
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.SKIP,
            max_attempts=1
        )
        
        # Mock execution function (should not be called)
        async def mock_execution():
            raise Exception("Should not be called")
        
        result = await failure_handler.execute_recovery(
            "skip_node", recovery_action, mock_execution
        )
        
        assert result["success"] is True
        assert result["strategy"] == "skip"
        assert result["result"]["skipped"] is True
    
    @pytest.mark.asyncio
    async def test_execute_recovery_escalate(self, failure_handler):
        """Test executing escalation recovery strategy"""
        # Add mock escalation handler
        mock_handler = AsyncMock()
        failure_handler.add_escalation_handler(mock_handler)
        
        recovery_action = RecoveryAction(
            strategy=RecoveryStrategy.ESCALATE,
            max_attempts=1
        )
        
        result = await failure_handler.execute_recovery(
            "escalate_node", recovery_action, lambda: None
        )
        
        assert result["success"] is False
        assert result["strategy"] == "escalate"
        assert "escalation_info" in result
        
        # Verify escalation handler was called
        mock_handler.assert_called_once()
    
    def test_failure_classification(self, failure_handler):
        """Test failure type classification"""
        test_cases = [
            ("timeout occurred", FailureType.TIMEOUT),
            ("connection refused", FailureType.NETWORK_ERROR),
            ("unauthorized access", FailureType.AUTHENTICATION_ERROR),
            ("permission denied", FailureType.PERMISSION_ERROR),
            ("validation failed", FailureType.VALIDATION_ERROR),
            ("out of memory", FailureType.RESOURCE_EXHAUSTION),
            ("random error", FailureType.UNKNOWN)
        ]
        
        for error_message, expected_type in test_cases:
            error = Exception(error_message)
            classified_type = failure_handler._classify_failure(error_message, error)
            assert classified_type == expected_type
    
    def test_pattern_matching(self, failure_handler, sample_failure_context):
        """Test failure pattern matching"""
        # Find timeout pattern
        timeout_pattern = None
        for pattern in failure_handler.failure_patterns:
            if pattern.failure_type == FailureType.TIMEOUT:
                timeout_pattern = pattern
                break
        
        assert timeout_pattern is not None
        
        # Test pattern matching
        matches = failure_handler._matches_pattern(sample_failure_context, timeout_pattern)
        assert matches is True
        
        # Test non-matching pattern
        network_pattern = FailurePattern(
            name="network_test",
            failure_type=FailureType.NETWORK_ERROR,
            error_patterns=[r"connection", r"network"],
            recovery_action=RecoveryAction(RecoveryStrategy.RETRY)
        )
        
        matches = failure_handler._matches_pattern(sample_failure_context, network_pattern)
        assert matches is False
    
    def test_get_failure_statistics(self, failure_handler):
        """Test failure statistics generation"""
        # Add some mock failures
        for i in range(5):
            failure_handler.failure_history.append(
                FailureContext(
                    node_id=f"node_{i % 2}",  # Two different nodes
                    failure_type=FailureType.TIMEOUT if i % 2 == 0 else FailureType.NETWORK_ERROR,
                    error_message=f"Error {i}",
                    timestamp=datetime.utcnow() - timedelta(hours=i)
                )
            )
        
        stats = failure_handler.get_failure_statistics()
        
        assert stats["total_failures"] == 5
        assert stats["unique_failed_nodes"] == 2
        assert "failures_by_type" in stats
        assert "failures_by_node" in stats
        assert "failures_by_hour" in stats
        assert "most_problematic_nodes" in stats
        assert stats["failures_by_type"]["timeout"] == 3
        assert stats["failures_by_type"]["network_error"] == 2
    
    def test_get_recovery_recommendations(self, failure_handler):
        """Test recovery recommendations generation"""
        # Add many failures to trigger recommendations
        for i in range(150):
            failure_handler.failure_history.append(
                FailureContext(
                    node_id="problematic_node",
                    failure_type=FailureType.TIMEOUT,
                    error_message="Timeout error",
                    timestamp=datetime.utcnow()
                )
            )
        
        recommendations = failure_handler.get_recovery_recommendations()
        
        assert len(recommendations) > 0
        
        # Should recommend investigating high failure rate
        high_failure_rec = next(
            (r for r in recommendations if r["type"] == "high_failure_rate"),
            None
        )
        assert high_failure_rec is not None
        assert high_failure_rec["priority"] == "high"
        
        # Should recommend investigating problematic node
        problematic_node_rec = next(
            (r for r in recommendations if r["type"] == "problematic_node"),
            None
        )
        assert problematic_node_rec is not None
    
    def test_reset_circuit_breaker(self, failure_handler):
        """Test circuit breaker reset"""
        node_id = "circuit_test_node"
        
        # Create a circuit breaker by triggering failures
        circuit_breaker = CircuitBreaker(failure_threshold=2)
        failure_handler.circuit_breakers[node_id] = circuit_breaker
        
        # Trigger failures to open circuit breaker
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "open"
        
        # Reset circuit breaker
        success = failure_handler.reset_circuit_breaker(node_id)
        assert success is True
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
    
    def test_clear_failure_history(self, failure_handler):
        """Test clearing failure history"""
        # Add some failures
        for i in range(10):
            failure_handler.failure_history.append(
                FailureContext(
                    node_id=f"node_{i % 3}",
                    failure_type=FailureType.TIMEOUT,
                    error_message=f"Error {i}",
                    timestamp=datetime.utcnow() - timedelta(hours=i)
                )
            )
        
        initial_count = len(failure_handler.failure_history)
        assert initial_count == 10
        
        # Clear history for specific node
        cleared_count = failure_handler.clear_failure_history(node_id="node_0")
        assert cleared_count > 0
        assert len(failure_handler.failure_history) < initial_count
        
        # Clear old history
        old_time = datetime.utcnow() - timedelta(hours=5)
        cleared_count = failure_handler.clear_failure_history(older_than=old_time)
        assert cleared_count > 0
        
        # Clear all history
        cleared_count = failure_handler.clear_failure_history()
        assert len(failure_handler.failure_history) == 0


class TestCircuitBreaker:
    """Test cases for CircuitBreaker"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing"""
        return CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    
    def test_initial_state(self, circuit_breaker):
        """Test circuit breaker initial state"""
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.can_execute() is True
    
    def test_failure_recording(self, circuit_breaker):
        """Test recording failures"""
        # Record failures below threshold
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.can_execute() is True
        
        # Record failure that exceeds threshold
        circuit_breaker.record_failure()
        
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.state == "open"
        assert circuit_breaker.can_execute() is False
    
    def test_success_recording(self, circuit_breaker):
        """Test recording successes"""
        # Record some failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        # Record success
        circuit_breaker.record_success()
        
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.can_execute() is True
    
    def test_half_open_state(self, circuit_breaker):
        """Test half-open state behavior"""
        # Open the circuit breaker
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "open"
        
        # Simulate recovery timeout passing
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=61)
        
        # Should allow execution (half-open state)
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == "half_open"
        
        # Success in half-open state should close circuit
        circuit_breaker.record_success()
        assert circuit_breaker.state == "closed"
    
    def test_half_open_failure(self, circuit_breaker):
        """Test failure in half-open state"""
        # Open the circuit breaker
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Simulate recovery timeout
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=61)
        circuit_breaker.can_execute()  # Transitions to half-open
        
        # Failure in half-open state should reopen circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "open"


class TestFailurePattern:
    """Test cases for FailurePattern"""
    
    def test_failure_pattern_creation(self):
        """Test creating failure patterns"""
        pattern = FailurePattern(
            name="test_pattern",
            failure_type=FailureType.TIMEOUT,
            error_patterns=[r"timeout", r"timed out"],
            recovery_action=RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                delay_seconds=5.0,
                max_attempts=3
            ),
            priority=2,
            conditions={"environment": "production"}
        )
        
        assert pattern.name == "test_pattern"
        assert pattern.failure_type == FailureType.TIMEOUT
        assert len(pattern.error_patterns) == 2
        assert pattern.recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert pattern.priority == 2
        assert pattern.conditions["environment"] == "production"


class TestRecoveryAction:
    """Test cases for RecoveryAction"""
    
    def test_recovery_action_creation(self):
        """Test creating recovery actions"""
        action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            delay_seconds=10.0,
            max_attempts=5,
            parameters={"max_delay": 300},
            escalation_threshold=3,
            circuit_breaker_threshold=10
        )
        
        assert action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert action.delay_seconds == 10.0
        assert action.max_attempts == 5
        assert action.parameters["max_delay"] == 300
        assert action.escalation_threshold == 3
        assert action.circuit_breaker_threshold == 10


@pytest.mark.asyncio
class TestFailureHandlerIntegration:
    """Integration tests for FailureHandler"""
    
    @pytest.fixture
    def failure_handler(self):
        """Create failure handler for integration testing"""
        return FailureHandler()
    
    async def test_end_to_end_failure_handling(self, failure_handler):
        """Test complete failure handling workflow"""
        node_id = "integration_test_node"
        
        # Simulate a timeout error
        timeout_error = TimeoutError("Operation timed out after 300 seconds")
        
        # Handle the failure
        recovery_action = await failure_handler.handle_failure(
            node_id, timeout_error, {"operation": "data_processing"}
        )
        
        # Verify recovery action
        assert recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        
        # Execute recovery with a mock function that succeeds on retry
        call_count = 0
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Still timing out")
            return {"success": True, "data": "processed"}
        
        recovery_result = await failure_handler.execute_recovery(
            node_id, recovery_action, mock_operation
        )
        
        # Verify successful recovery
        assert recovery_result["success"] is True
        assert call_count == 2  # Original + 1 retry
        
        # Verify failure statistics
        stats = failure_handler.get_failure_statistics()
        assert stats["total_failures"] == 1
        assert stats["failures_by_type"]["timeout"] == 1
    
    async def test_circuit_breaker_integration(self, failure_handler):
        """Test circuit breaker integration with failure handling"""
        node_id = "circuit_integration_node"
        
        # Trigger multiple failures to open circuit breaker
        for i in range(5):
            error = Exception(f"Failure {i}")
            recovery_action = await failure_handler.handle_failure(
                node_id, error, {"attempt": i}
            )
            
            # Try to execute recovery (will fail)
            async def failing_operation():
                raise Exception("Always fails")
            
            await failure_handler.execute_recovery(
                node_id, recovery_action, failing_operation
            )
        
        # Next failure should trigger circuit breaker
        final_error = Exception("Final failure")
        recovery_action = await failure_handler.handle_failure(
            node_id, final_error, {"final": True}
        )
        
        # Should get circuit breaker strategy
        assert recovery_action.strategy == RecoveryStrategy.CIRCUIT_BREAKER
        
        # Verify circuit breaker is open
        assert node_id in failure_handler.circuit_breakers
        circuit_breaker = failure_handler.circuit_breakers[node_id]
        assert circuit_breaker.state == "open"
    
    async def test_custom_recovery_callback(self, failure_handler):
        """Test custom recovery callback integration"""
        # Add custom recovery callback
        custom_callback_called = False
        custom_result = {"custom": True, "success": True}
        
        async def custom_recovery_callback(node_id, recovery_action, execution_func):
            nonlocal custom_callback_called
            custom_callback_called = True
            return custom_result
        
        failure_handler.add_recovery_callback("custom_strategy", custom_recovery_callback)
        
        # Create custom recovery action
        custom_recovery = RecoveryAction(strategy="custom_strategy")
        
        # Execute recovery
        result = await failure_handler.execute_recovery(
            "custom_node", custom_recovery, lambda: None
        )
        
        assert custom_callback_called is True
        assert result == custom_result


if __name__ == "__main__":
    pytest.main([__file__])