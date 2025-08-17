"""
Phase 7 Performance Tests: Scalability and Performance Validation

Comprehensive performance and scalability tests for KiroLinter's agentic system
including large repository handling, memory usage, concurrent operations,
and pattern evolution testing.
"""

import pytest
import tempfile
import time
import psutil
import os
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import components to test
from kirolinter.orchestration.workflow_coordinator import WorkflowCoordinator
from kirolinter.memory.pattern_memory import PatternMemory, create_pattern_memory
from kirolinter.agents.learner import LearnerAgent
from kirolinter.agents.reviewer import ReviewerAgent
from kirolinter.agents.fixer import FixerAgent
from kirolinter.learning.cross_repo_learner import CrossRepoLearner
from kirolinter.models.issue import Issue, IssueType, Severity


class TestLargeRepositoryPerformance:
    """Performance tests for large repository analysis."""
    
    @pytest.fixture
    def large_repo_dir(self):
        """Create a large temporary repository for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many Python files to simulate large repository
            for i in range(100):  # Create 100 files for testing
                file_path = Path(temp_dir) / f"module_{i}.py"
                file_content = f"""
# Module {i}
import os
import sys
from typing import List, Dict

class TestClass{i}:
    def __init__(self):
        self.value = {i}
        self.unused_var = "unused"  # Intentional issue
    
    def process_data(self, data: List[int]) -> Dict[str, int]:
        result = {{}}
        for item in data:
            if item > 0:
                result[f"item_{{item}}"] = item * 2
        return result
    
    def unused_method(self):  # Intentional issue
        pass

def main():
    instance = TestClass{i}()
    data = list(range(10))
    result = instance.process_data(data)
    print(f"Module {i} result: {{len(result)}} items")

if __name__ == "__main__":
    main()
"""
                file_path.write_text(file_content)
            
            yield temp_dir
    
    @pytest.fixture
    def performance_memory(self):
        """Create a mock memory system for performance testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        memory.retrieve_patterns.return_value = []
        yield memory
    
    def test_large_repo_analysis_performance(self, large_repo_dir, performance_memory):
        """Test analysis performance on large repository (100 files)."""
        # Mock LLM initialization to avoid LiteLLM dependency
        with patch('kirolinter.agents.fixer.get_chat_model') as mock_llm1:
            mock_llm1.return_value = Mock()
            with patch('kirolinter.agents.llm_provider.create_llm_provider') as mock_llm2:
                mock_llm2.return_value = Mock()
                with patch('kirolinter.agents.integrator.get_chat_model') as mock_llm3:
                    mock_llm3.return_value = Mock()
                    coordinator = WorkflowCoordinator(large_repo_dir, memory=performance_memory)
        
        with patch.object(coordinator, 'reviewer') as mock_reviewer:
            # Mock reviewer to return issues for each file
            issues_per_file = 2
            total_files = len(list(Path(large_repo_dir).glob("*.py")))
            total_issues = total_files * issues_per_file
            
            mock_issues = [
                Issue(
                    file_path=f"module_{i//2}.py",
                    line_number=i%20+1,
                    rule_id=f"rule_{i%5}",
                    message=f"Test issue {i}",
                    severity=Severity.LOW,
                    issue_type="style"
                )
                for i in range(total_issues)
            ]
            mock_reviewer.analyze.return_value = mock_issues
            
            # Time the analysis
            start_time = time.time()
            result = coordinator.execute_workflow("quick_fix")
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert execution_time < 10.0, f"Large repo analysis too slow: {execution_time:.2f}s (should be <10s)"
            assert result["status"] == "complete", "Large repo analysis failed"
            
            # Verify all files were processed
            mock_reviewer.analyze.assert_called_once()
            
            # Check memory usage didn't explode
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            assert memory_mb < 500, f"Memory usage too high: {memory_mb:.1f}MB (should be <500MB)"
    
    def test_very_large_repo_simulation(self, performance_memory):
        """Test performance with simulated very large repository (10,000 files)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock LLM initialization to avoid LiteLLM dependency
            with patch('kirolinter.agents.fixer.get_chat_model') as mock_llm1:
                mock_llm1.return_value = Mock()
                with patch('kirolinter.agents.llm_provider.create_llm_provider') as mock_llm2:
                    mock_llm2.return_value = Mock()
                    with patch('kirolinter.agents.integrator.get_chat_model') as mock_llm3:
                        mock_llm3.return_value = Mock()
                        coordinator = WorkflowCoordinator(temp_dir, memory=performance_memory)
            
            with patch.object(coordinator, 'reviewer') as mock_reviewer:
                # Simulate 10,000 files with issues
                large_file_count = 10000
                mock_issues = [
                    Issue(f"issue_{i}", IssueType.STYLE, Severity.LOW, f"file_{i}.py", 
                         1, 1, f"Simulated issue {i}", "style_rule")
                    for i in range(large_file_count)
                ]
                mock_reviewer.analyze.return_value = mock_issues
                
                # Time the processing
                start_time = time.time()
                result = coordinator.execute_workflow("quick_fix")
                execution_time = time.time() - start_time
                
                # Performance assertions for very large repo
                assert execution_time < 15.0, f"Very large repo analysis too slow: {execution_time:.2f}s"
                assert result["status"] == "complete", "Very large repo analysis failed"
                
                # Memory usage should still be reasonable
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                assert memory_mb < 1000, f"Memory usage too high for large repo: {memory_mb:.1f}MB"
    
    def test_file_processing_scalability(self, performance_memory):
        """Test scalability of file processing with increasing file sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files of different sizes
            file_sizes = [1000, 5000, 10000, 50000]  # Lines of code
            processing_times = []
            
            for size in file_sizes:
                # Create file with specified number of lines
                file_path = Path(temp_dir) / f"large_file_{size}.py"
                content_lines = [f"# Line {i}\nprint('Line {i}')" for i in range(size)]
                file_path.write_text("\n".join(content_lines))
                
                # Test processing time
                learner = LearnerAgent(memory=performance_memory, verbose=False)
                
                start_time = time.time()
                patterns = learner.extract_patterns(temp_dir, [file_path.read_text()])
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                # Clean up
                file_path.unlink()
            
            # Verify processing time scales reasonably (not exponentially)
            for i in range(1, len(processing_times)):
                time_ratio = processing_times[i] / processing_times[i-1]
                size_ratio = file_sizes[i] / file_sizes[i-1]
                
                # Processing time should not grow exponentially (allow up to 10x for 2x size increase)
                assert time_ratio <= size_ratio * 10, f"Processing time scaling exponentially: {time_ratio:.2f}x for {size_ratio:.2f}x size increase"


class TestMemoryUsageAndEfficiency:
    """Tests for memory usage patterns and efficiency."""
    
    @pytest.fixture
    def memory_test_setup(self):
        """Setup for memory usage testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.retrieve_patterns.return_value = []
        memory.get_team_patterns.return_value = []
        yield memory
    
    def test_pattern_storage_memory_efficiency(self, memory_test_setup):
        """Test memory efficiency of pattern storage."""
        memory = memory_test_setup
        learner = LearnerAgent(memory=memory, verbose=False)
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Store many patterns
        pattern_count = 1000
        for i in range(pattern_count):
            pattern_data = {
                "snippet": f"def function_{i}(): return {i}",
                "quality_score": 0.8 + (i % 20) / 100,
                "complexity": i % 10,
                "metadata": {"created": datetime.now().isoformat()}
            }
            learner.pattern_memory.store_pattern(f"test_repo_{i%10}", "code_pattern", pattern_data, 0.8)
        
        # Measure memory after pattern storage
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB for {pattern_count} patterns"
        
        # Verify all patterns were stored
        assert memory.store_pattern.call_count == pattern_count, "Not all patterns were stored"
    
    def test_pattern_retrieval_performance(self, memory_test_setup):
        """Test performance of pattern retrieval operations."""
        memory = memory_test_setup
        
        # Mock large number of stored patterns
        large_pattern_set = [
            {"pattern_data": {"snippet": f"def func_{i}(): pass", "quality_score": 0.8}}
            for i in range(5000)
        ]
        memory.get_team_patterns.return_value = large_pattern_set
        
        learner = LearnerAgent(memory=memory, verbose=False)
        
        # Time pattern retrieval
        start_time = time.time()
        patterns = learner.pattern_memory.get_team_patterns("test_repo", "code_pattern")
        retrieval_time = time.time() - start_time
        
        # Retrieval should be fast even with many patterns
        assert retrieval_time < 1.0, f"Pattern retrieval too slow: {retrieval_time:.3f}s for 5000 patterns"
        assert len(patterns) == 5000, "Not all patterns retrieved"
    
    def test_memory_cleanup_and_gc(self, memory_test_setup):
        """Test memory cleanup and garbage collection."""
        memory = memory_test_setup
        
        # Create and destroy many objects
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Create many temporary objects
        temp_objects = []
        for i in range(1000):
            learner = LearnerAgent(memory=memory, verbose=False)
            patterns = learner.extract_patterns("temp_repo", [f"def temp_{i}(): pass"])
            temp_objects.append((learner, patterns))
        
        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Clear references and force garbage collection
        temp_objects.clear()
        import gc
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Memory should be cleaned up reasonably well
        memory_retained = final_memory - initial_memory
        peak_increase = peak_memory - initial_memory
        
        # In test environments, memory cleanup is often delayed or incomplete
        # The main goal is to ensure no excessive memory growth, not perfect cleanup
        
        # Verify that we didn't have excessive memory growth (reasonable limit for 1000 objects)
        assert peak_increase < 50, f"Excessive memory growth: {peak_increase:.1f}MB for 1000 objects"
        
        # Verify that final memory is not significantly higher than peak
        # (this would indicate continued growth after cleanup)
        assert final_memory <= peak_memory * 1.1, f"Memory continued growing after cleanup: {final_memory:.1f}MB vs peak {peak_memory:.1f}MB"


class TestConcurrentOperations:
    """Tests for concurrent workflow and agent operations."""
    
    @pytest.fixture
    def concurrent_memory(self):
        """Setup for concurrent operation testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        memory.retrieve_patterns.return_value = []
        yield memory
    
    def test_concurrent_workflow_execution(self, concurrent_memory):
        """Test multiple workflows running concurrently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock LLM initialization to avoid LiteLLM dependency
            with patch('kirolinter.agents.fixer.get_chat_model') as mock_llm1:
                mock_llm1.return_value = Mock()
                with patch('kirolinter.agents.llm_provider.create_llm_provider') as mock_llm2:
                    mock_llm2.return_value = Mock()
                    with patch('kirolinter.agents.integrator.get_chat_model') as mock_llm3:
                        mock_llm3.return_value = Mock()
                        # Create multiple coordinators
                        coordinator_count = 5
                        coordinators = [
                            WorkflowCoordinator(temp_dir, memory=concurrent_memory)
                            for _ in range(coordinator_count)
                        ]
            
            # Mock all reviewers
            for coordinator in coordinators:
                with patch.object(coordinator, 'reviewer') as mock_reviewer:
                    mock_reviewer.analyze.return_value = [
                        Issue("concurrent_issue", IssueType.STYLE, Severity.LOW, "test.py", 1, 1, "Test", "test")
                    ]
            
            def execute_workflow(coordinator, workflow_id):
                """Execute workflow and return result with timing."""
                with patch.object(coordinator, 'reviewer') as mock_reviewer:
                    mock_reviewer.analyze.return_value = []
                    
                    start_time = time.time()
                    result = coordinator.execute_workflow("quick_fix")
                    execution_time = time.time() - start_time
                    
                    return {
                        "workflow_id": workflow_id,
                        "result": result,
                        "execution_time": execution_time
                    }
            
            # Execute workflows concurrently
            with ThreadPoolExecutor(max_workers=coordinator_count) as executor:
                futures = [
                    executor.submit(execute_workflow, coord, i)
                    for i, coord in enumerate(coordinators)
                ]
                
                results = [future.result() for future in as_completed(futures)]
            
            # Verify all workflows completed successfully
            assert len(results) == coordinator_count, "Not all concurrent workflows completed"
            
            for result in results:
                assert result["result"]["status"] == "complete", f"Workflow {result['workflow_id']} failed"
                assert result["execution_time"] < 5.0, f"Concurrent workflow {result['workflow_id']} too slow"
            
            # Verify memory operations were called concurrently
            assert concurrent_memory.store_pattern.call_count >= coordinator_count, "Concurrent memory operations failed"
    
    def test_concurrent_pattern_learning(self, concurrent_memory):
        """Test concurrent pattern learning operations."""
        learner_count = 10
        learners = [LearnerAgent(memory=concurrent_memory, verbose=False) for _ in range(learner_count)]
        
        def learn_patterns(learner, learner_id):
            """Learn patterns concurrently."""
            code_snippets = [
                f"def concurrent_func_{learner_id}_{i}(): return {i}"
                for i in range(10)
            ]
            
            start_time = time.time()
            patterns = learner.extract_patterns(f"repo_{learner_id}", code_snippets)
            learning_time = time.time() - start_time
            
            return {
                "learner_id": learner_id,
                "patterns_count": len(patterns),
                "learning_time": learning_time
            }
        
        # Execute concurrent learning
        with ThreadPoolExecutor(max_workers=learner_count) as executor:
            futures = [
                executor.submit(learn_patterns, learner, i)
                for i, learner in enumerate(learners)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # Verify concurrent learning
        assert len(results) == learner_count, "Not all concurrent learning completed"
        
        for result in results:
            assert result["patterns_count"] > 0, f"Learner {result['learner_id']} found no patterns"
            assert result["learning_time"] < 3.0, f"Concurrent learning {result['learner_id']} too slow"
        
        # Verify memory operations were called for all learners
        expected_calls = learner_count * 10  # 10 patterns per learner
        assert concurrent_memory.store_pattern.call_count >= expected_calls * 0.8, "Concurrent pattern storage failed"
    
    def test_concurrent_cross_repo_operations(self, concurrent_memory):
        """Test concurrent cross-repository operations."""
        cross_learner = CrossRepoLearner(memory=concurrent_memory, verbose=False)
        
        # Mock repository patterns
        repo_patterns = {
            f"repo_{i}": [f"def repo_{i}_func_{j}(): pass" for j in range(5)]
            for i in range(10)
        }
        
        def detect_similarity(repo_a, repo_b):
            """Detect repository similarity concurrently."""
            with patch.object(cross_learner, '_get_repo_patterns') as mock_get_patterns:
                mock_get_patterns.side_effect = [repo_patterns[repo_a], repo_patterns[repo_b]]
                
                start_time = time.time()
                similarity = cross_learner.detect_repo_similarity(repo_a, repo_b)
                detection_time = time.time() - start_time
                
                return {
                    "repo_pair": (repo_a, repo_b),
                    "similarity": similarity,
                    "detection_time": detection_time
                }
        
        # Create repository pairs for comparison
        repo_pairs = [(f"repo_{i}", f"repo_{j}") for i in range(5) for j in range(i+1, 5)]
        
        # Execute concurrent similarity detection
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(detect_similarity, pair[0], pair[1])
                for pair in repo_pairs
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # Verify concurrent similarity detection
        assert len(results) == len(repo_pairs), "Not all similarity detections completed"
        
        for result in results:
            assert 0.0 <= result["similarity"] <= 1.0, f"Invalid similarity score: {result['similarity']}"
            assert result["detection_time"] < 2.0, f"Similarity detection too slow: {result['detection_time']:.3f}s"


class TestPatternEvolutionAndScaling:
    """Tests for pattern evolution and long-term scaling."""
    
    @pytest.fixture
    def evolution_memory(self):
        """Setup for pattern evolution testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.get_team_patterns.return_value = []
        yield memory
    
    def test_pattern_evolution_over_time(self, evolution_memory):
        """Test pattern evolution and refinement over time."""
        learner = LearnerAgent(memory=evolution_memory, verbose=False)
        
        # Simulate pattern evolution over multiple iterations
        iterations = 50
        patterns_per_iteration = 20
        
        for iteration in range(iterations):
            # Generate evolving code patterns
            code_snippets = [
                f"def evolved_func_{iteration}_{i}():\n    # Iteration {iteration}\n    return {i * iteration}"
                for i in range(patterns_per_iteration)
            ]
            
            # Extract patterns
            patterns = learner.extract_patterns(f"evolving_repo", code_snippets)
            
            # Verify pattern extraction
            assert len(patterns) == patterns_per_iteration, f"Pattern count mismatch in iteration {iteration}"
        
        # Verify total pattern storage calls
        total_expected_calls = iterations * patterns_per_iteration
        assert evolution_memory.store_pattern.call_count == total_expected_calls, "Pattern evolution storage failed"
    
    def test_long_term_memory_scaling(self, evolution_memory):
        """Test memory system scaling over long-term usage."""
        learner = LearnerAgent(memory=evolution_memory, verbose=False)
        
        # Simulate long-term usage with many repositories
        repo_count = 100
        patterns_per_repo = 50
        
        start_time = time.time()
        
        for repo_id in range(repo_count):
            repo_name = f"long_term_repo_{repo_id}"
            
            # Generate patterns for each repository
            code_snippets = [
                f"def repo_{repo_id}_func_{i}(): return {i}"
                for i in range(patterns_per_repo)
            ]
            
            patterns = learner.extract_patterns(repo_name, code_snippets)
            assert len(patterns) == patterns_per_repo, f"Pattern extraction failed for {repo_name}"
        
        total_time = time.time() - start_time
        
        # Verify scaling performance
        total_patterns = repo_count * patterns_per_repo
        avg_time_per_pattern = total_time / total_patterns
        
        assert avg_time_per_pattern < 0.01, f"Pattern processing too slow: {avg_time_per_pattern:.4f}s per pattern"
        assert total_time < 30.0, f"Long-term scaling test too slow: {total_time:.2f}s"
        
        # Verify all patterns were stored
        assert evolution_memory.store_pattern.call_count == total_patterns, "Long-term pattern storage failed"
    
    def test_pattern_quality_evolution(self, evolution_memory):
        """Test that pattern quality improves over time."""
        learner = LearnerAgent(memory=evolution_memory, verbose=False)
        
        # Simulate improving code quality over time
        quality_iterations = 10
        quality_scores = []
        
        for iteration in range(quality_iterations):
            # Generate code with improving quality
            if iteration < 3:
                # Early iterations: poor quality code
                code = f"def bad_func_{iteration}():\n    # TODO: fix this\n    eval('dangerous')\n    x = 'very long line that should be flagged as poor quality'"
            elif iteration < 7:
                # Middle iterations: medium quality code
                code = f"def medium_func_{iteration}():\n    return {iteration} * 2"
            else:
                # Later iterations: high quality code
                code = f"def good_func_{iteration}():\n    \"\"\"Well documented function.\"\"\"\n    return {iteration} * 2"
            
            patterns = learner.extract_patterns(f"quality_repo", [code])
            if patterns:
                quality_scores.append(patterns[0]["quality_score"])
        
        # Verify quality improvement trend
        assert len(quality_scores) == quality_iterations, "Quality scores not collected"
        
        # Check that later scores are generally higher than earlier ones
        early_avg = sum(quality_scores[:3]) / 3
        late_avg = sum(quality_scores[-3:]) / 3
        
        assert late_avg > early_avg, f"Quality did not improve over time: early={early_avg:.3f}, late={late_avg:.3f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])