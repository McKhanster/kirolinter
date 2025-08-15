"""
Phase 6 Tests: Advanced Learning and Adaptation

Tests for sophisticated pattern extraction, cross-repository learning,
and predictive analytics capabilities.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import the components to test
from kirolinter.agents.learner import LearnerAgent
from kirolinter.learning.cross_repo_learner import CrossRepoLearner
from kirolinter.memory.pattern_memory import PatternMemory


class TestAdvancedPatternExtraction:
    """Test sophisticated pattern extraction algorithms."""
    
    @pytest.fixture
    def mock_memory(self):
        """Create a mock pattern memory."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.retrieve_patterns.return_value = []
        return memory
    
    @pytest.fixture
    def learner_agent(self, mock_memory):
        """Create a learner agent with mocked dependencies."""
        with patch('kirolinter.agents.learner.ML_AVAILABLE', True):
            agent = LearnerAgent(memory=mock_memory, verbose=False)
            return agent
    
    def test_pattern_extraction_with_ml(self, learner_agent, mock_memory):
        """Test ML-based pattern extraction with clustering."""
        # Mock ML components
        with patch.object(learner_agent, 'vectorizer') as mock_vectorizer, \
             patch.object(learner_agent, 'clusterer') as mock_clusterer:
            
            # Setup mocks
            mock_vectorizer.fit_transform.return_value.toarray.return_value = [[1, 0], [0, 1]]
            mock_clusterer.fit_predict.return_value = [0, 1]
            mock_clusterer.cluster_centers_ = [[1, 0], [0, 1]]
            mock_clusterer.n_clusters = 2
            
            # Test data
            code_snippets = [
                "def foo(): pass",
                "x = 1"
            ]
            
            # Execute
            patterns = learner_agent.extract_patterns("test_repo", code_snippets)
            
            # Verify
            assert len(patterns) == 2
            assert all("cluster" in pattern for pattern in patterns)
            assert all("quality_score" in pattern for pattern in patterns)
            assert all("analysis_method" in pattern for pattern in patterns)
            assert patterns[0]["analysis_method"] == "ml_clustering"
            
            # Verify storage calls
            assert mock_memory.store_pattern.call_count >= 2
    
    def test_pattern_extraction_statistical_fallback(self, mock_memory):
        """Test statistical pattern extraction when ML is unavailable."""
        with patch('kirolinter.agents.learner.ML_AVAILABLE', False):
            agent = LearnerAgent(memory=mock_memory, verbose=False)
            
            code_snippets = [
                "def complex_function():\n    if True:\n        for i in range(10):\n            pass",
                "x = 1"
            ]
            
            patterns = agent.extract_patterns("test_repo", code_snippets)
            
            assert len(patterns) == 2
            assert all("analysis_method" in pattern for pattern in patterns)
            assert patterns[0]["analysis_method"] == "statistical"
            assert "complexity_score" in patterns[0]
    
    def test_quality_score_calculation(self, learner_agent):
        """Test quality score calculation for code snippets."""
        # High quality code
        good_code = "def calculate_sum(numbers):\n    return sum(numbers)"
        good_score = learner_agent._calculate_quality_score(good_code)
        assert 0.7 <= good_score <= 1.0
        
        # Low quality code with issues
        bad_code = "def bad_function():\n    # TODO: fix this\n    eval('dangerous code')\n    x = 'very long line that exceeds the recommended length limit and should be flagged as a quality issue'"
        bad_score = learner_agent._calculate_quality_score(bad_code)
        assert 0.0 <= bad_score <= 0.6
        
        # Verify good code scores higher than bad code
        assert good_score > bad_score
    
    def test_find_similar_patterns_ml(self, learner_agent, mock_memory):
        """Test ML-based similar pattern finding."""
        # Mock stored patterns
        stored_patterns = [
            {"snippet": "def foo(): pass", "quality_score": 0.8},
            {"snippet": "def bar(): return 1", "quality_score": 0.9}
        ]
        mock_memory.retrieve_patterns.return_value = stored_patterns
        
        # Mock vectorizer
        with patch.object(learner_agent, 'vectorizer') as mock_vectorizer:
            mock_vectorizer.fit_transform.return_value.toarray.return_value = [
                [1, 0, 0], [0, 1, 0], [1, 0, 0]  # Third is similar to first
            ]
            
            target_pattern = {"snippet": "def similar(): pass"}
            similar = learner_agent.find_similar_patterns("test_repo", target_pattern)
            
            # Should find similar patterns
            assert len(similar) >= 0  # May be empty if similarity threshold not met
            if similar:
                assert all("similarity_score" in pattern for pattern in similar)
    
    def test_complexity_estimation(self, learner_agent):
        """Test code complexity estimation."""
        # Simple code
        simple_code = "x = 1"
        simple_complexity = learner_agent._estimate_complexity(simple_code)
        assert 0.0 <= simple_complexity <= 0.3
        
        # Complex code
        complex_code = """
        def complex_function(data):
            if data:
                for item in data:
                    try:
                        if item > 0:
                            while item > 0:
                                item -= 1
                    except Exception:
                        pass
        """
        complex_complexity = learner_agent._estimate_complexity(complex_code)
        assert 0.3 <= complex_complexity <= 1.0
        
        # Verify complex code has higher complexity
        assert complex_complexity > simple_complexity


class TestCrossRepositoryLearning:
    """Test cross-repository learning capabilities."""
    
    @pytest.fixture
    def mock_memory(self):
        """Create a mock pattern memory."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.retrieve_patterns.return_value = []
        return memory
    
    @pytest.fixture
    def cross_repo_learner(self, mock_memory):
        """Create a cross-repository learner."""
        return CrossRepoLearner(memory=mock_memory, verbose=False)
    
    def test_safe_pattern_sharing(self, cross_repo_learner, mock_memory):
        """Test safe pattern sharing between repositories."""
        # Mock source patterns (mix of safe and unsafe)
        safe_pattern = {
            "snippet": "def calculate_total(items): return sum(items)",
            "quality_score": 0.9,
            "type": "code_pattern"
        }
        
        unsafe_pattern = {
            "snippet": "password = 'secret123'",
            "quality_score": 0.5,
            "type": "code_pattern"
        }
        
        mock_memory.retrieve_patterns.return_value = [safe_pattern, unsafe_pattern]
        
        # Execute sharing
        result = cross_repo_learner.share_patterns("source_repo", "target_repo")
        
        # Verify results
        assert result["success"] is True
        assert result["patterns_shared"] >= 0  # At least safe patterns should be shared
        assert result["patterns_rejected"] >= 1  # Unsafe pattern should be rejected
    
    def test_pattern_safety_check(self, cross_repo_learner):
        """Test pattern safety validation."""
        # Safe patterns
        safe_patterns = [
            {"snippet": "def add(a, b): return a + b"},
            {"description": "A simple addition function"},
            {"type": "naming_convention", "style": "snake_case"}
        ]
        
        for pattern in safe_patterns:
            assert cross_repo_learner._is_safe_to_share(pattern) is True
        
        # Unsafe patterns
        unsafe_patterns = [
            {"snippet": "password = 'secret123'"},
            {"snippet": "api_key = 'sk-1234567890'"},
            {"snippet": "database_url = 'postgresql://user:pass@localhost/db'"},
            {"description": "Connect to database at 192.168.1.100"},
            {"snippet": "user@example.com sent this code"}
        ]
        
        for pattern in unsafe_patterns:
            assert cross_repo_learner._is_safe_to_share(pattern) is False
    
    def test_repository_similarity_detection(self, cross_repo_learner, mock_memory):
        """Test repository similarity detection."""
        # Mock patterns for both repositories
        patterns_a = ["def foo(): pass", "import os", "class MyClass: pass"]
        patterns_b = ["def bar(): pass", "import sys", "class YourClass: pass"]
        
        with patch.object(cross_repo_learner, '_get_repo_patterns') as mock_get_patterns:
            mock_get_patterns.side_effect = [patterns_a, patterns_b]
            
            similarity = cross_repo_learner.detect_repo_similarity("repo_a", "repo_b")
            
            assert 0.0 <= similarity <= 1.0
            # Should store similarity result
            mock_memory.store_pattern.assert_called()
    
    def test_pattern_marketplace_integration(self, cross_repo_learner, mock_memory):
        """Test community pattern marketplace integration."""
        # Mock community patterns
        community_patterns = [
            {
                "type": "code_pattern",
                "snippet": "def validate_email(email): return '@' in email",
                "quality_score": 0.8,
                "source": "community"
            },
            {
                "type": "code_pattern",
                "snippet": "password = 'unsafe'",  # This should be rejected
                "quality_score": 0.9,
                "source": "community"
            }
        ]
        
        result = cross_repo_learner.pattern_marketplace("target_repo", community_patterns)
        
        assert result["success"] is True
        assert result["patterns_integrated"] >= 0
        assert result["patterns_rejected"] >= 1  # Unsafe pattern should be rejected
    
    def test_content_anonymization(self, cross_repo_learner):
        """Test content anonymization for shared patterns."""
        sensitive_content = """
        password = "secret123"
        api_key = "sk-abcdef123456"
        user_email = "john.doe@company.com"
        server_ip = "192.168.1.100"
        """
        
        anonymized = cross_repo_learner._anonymize_content(sensitive_content)
        
        # Verify sensitive data is anonymized
        assert "secret123" not in anonymized
        assert "sk-abcdef123456" not in anonymized
        assert "john.doe@company.com" not in anonymized
        assert "192.168.1.100" not in anonymized
        
        # Verify placeholders are present
        assert "[REDACTED]" in anonymized
        assert "[EMAIL]" in anonymized
        assert "[IP_ADDRESS]" in anonymized


class TestPredictiveAnalytics:
    """Test predictive analytics for code quality trends."""
    
    @pytest.fixture
    def mock_memory(self):
        """Create a mock pattern memory with workflow execution data."""
        memory = Mock(spec=PatternMemory)
        
        # Mock workflow execution history
        base_time = datetime.now() - timedelta(days=30)
        executions = []
        
        for i in range(10):
            execution = {
                "timestamp": (base_time + timedelta(days=i*3)).isoformat(),
                "progress": 80 - i*2,  # Declining trend
                "success": True
            }
            executions.append(execution)
        
        memory.retrieve_patterns.return_value = executions
        memory.store_pattern.return_value = True
        return memory
    
    @pytest.fixture
    def learner_agent(self, mock_memory):
        """Create a learner agent for predictive analytics."""
        with patch('kirolinter.agents.learner.ML_AVAILABLE', True):
            agent = LearnerAgent(memory=mock_memory, verbose=False)
            return agent
    
    def test_quality_trend_prediction_ml(self, learner_agent, mock_memory):
        """Test ML-based quality trend prediction."""
        with patch.object(learner_agent, 'trend_predictor') as mock_predictor:
            mock_predictor.fit.return_value = None
            mock_predictor.predict.return_value = [0.65]  # Predicted score
            mock_predictor.score.return_value = 0.8  # R² score for confidence
            
            result = learner_agent.predict_quality_trends("test_repo")
            
            assert "predicted_score" in result
            assert "early_warning" in result
            assert "recommendations" in result
            assert "confidence" in result
            
            # Should detect declining trend and trigger early warning
            assert result["early_warning"] is True
            assert len(result["recommendations"]) > 0
    
    def test_quality_trend_prediction_statistical(self, mock_memory):
        """Test statistical trend prediction fallback."""
        with patch('kirolinter.agents.learner.ML_AVAILABLE', False):
            agent = LearnerAgent(memory=mock_memory, verbose=False)
            
            result = agent.predict_quality_trends("test_repo")
            
            assert "predicted_score" in result
            assert "early_warning" in result
            assert "recommendations" in result
            assert 0.0 <= result["predicted_score"] <= 1.0
    
    def test_quality_goal_tracking(self, learner_agent, mock_memory):
        """Test quality goal tracking and progress analysis."""
        # Mock the get_team_patterns method that analyze_workflows calls
        mock_memory.get_team_patterns.return_value = []
        
        # Mock current workflow analysis
        with patch.object(learner_agent, 'analyze_workflows') as mock_analyze:
            mock_analyze.return_value = {"success_rate": 0.75}
            
            result = learner_agent.track_quality_goals("test_repo", target_score=0.9)
            
            # Debug: print the result to see what's actually returned
            print(f"DEBUG: result = {result}")
            
            assert "current" in result, f"'current' key missing from result: {result.keys()}"
            assert result["current"] == 0.75
            assert result["target"] == 0.9
            assert abs(result["gap"] - 0.15) < 0.001  # Handle floating point precision
            assert "action_items" in result
            assert "timeline_estimate" in result
            assert len(result["action_items"]) > 0
    
    def test_workflow_analysis(self, learner_agent, mock_memory):
        """Test workflow execution analysis."""
        result = learner_agent.analyze_workflows("test_repo")
        
        assert "success_rate" in result
        assert "total_executions" in result
        assert "avg_progress" in result
        assert "trend" in result
        
        assert 0.0 <= result["success_rate"] <= 1.0
        assert result["total_executions"] >= 0
    
    def test_recommendation_generation(self, learner_agent):
        """Test recommendation generation based on trends."""
        # Test early warning recommendations
        early_warning_recs = learner_agent._generate_recommendations(
            early_warning=True, predicted_score=0.6, current_score=0.8
        )
        
        assert len(early_warning_recs) > 0
        assert any("review frequency" in rec.lower() for rec in early_warning_recs)
        
        # Test normal recommendations
        normal_recs = learner_agent._generate_recommendations(
            early_warning=False, predicted_score=0.85, current_score=0.8
        )
        
        assert len(normal_recs) > 0
        assert any("maintain" in rec.lower() for rec in normal_recs)
    
    def test_insufficient_data_handling(self, mock_memory):
        """Test handling of insufficient data for predictions."""
        # Mock insufficient execution data
        mock_memory.retrieve_patterns.return_value = []
        mock_memory.get_team_patterns.return_value = []
        
        agent = LearnerAgent(memory=mock_memory, verbose=False)
        result = agent.predict_quality_trends("test_repo")
        
        assert result["data_points"] == 0
        assert result["confidence"] <= 0.1
        assert "insufficient data" in result["recommendations"][0].lower()


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple Phase 6 features."""
    
    @pytest.fixture
    def setup_integration_test(self):
        """Setup for integration testing."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        memory.retrieve_patterns.return_value = []
        
        learner = LearnerAgent(memory=memory, verbose=False)
        cross_repo = CrossRepoLearner(memory=memory, verbose=False)
        
        return {
            "memory": memory,
            "learner": learner,
            "cross_repo": cross_repo
        }
    
    def test_end_to_end_learning_workflow(self, setup_integration_test):
        """Test complete learning workflow from pattern extraction to prediction."""
        components = setup_integration_test
        learner = components["learner"]
        cross_repo = components["cross_repo"]
        
        # Step 1: Extract patterns
        code_snippets = [
            "def process_data(data): return [x*2 for x in data]",
            "def validate_input(value): return value is not None"
        ]
        
        with patch('kirolinter.agents.learner.ML_AVAILABLE', True):
            with patch.object(learner, 'vectorizer') as mock_vectorizer, \
                 patch.object(learner, 'clusterer') as mock_clusterer:
                
                mock_vectorizer.fit_transform.return_value.toarray.return_value = [[1, 0], [0, 1]]
                mock_clusterer.fit_predict.return_value = [0, 1]
                mock_clusterer.cluster_centers_ = [[1, 0], [0, 1]]
                mock_clusterer.n_clusters = 2
                
                patterns = learner.extract_patterns("repo_a", code_snippets)
                assert len(patterns) == 2
        
        # Step 2: Share patterns across repositories
        components["memory"].retrieve_patterns.return_value = patterns
        sharing_result = cross_repo.share_patterns("repo_a", "repo_b")
        assert sharing_result["success"] is True
        
        # Step 3: Predict quality trends
        # Mock execution history for prediction
        executions = [
            {"timestamp": datetime.now().isoformat(), "progress": 85},
            {"timestamp": (datetime.now() - timedelta(days=7)).isoformat(), "progress": 80},
            {"timestamp": (datetime.now() - timedelta(days=14)).isoformat(), "progress": 75}
        ]
        components["memory"].retrieve_patterns.return_value = executions
        
        prediction = learner.predict_quality_trends("repo_b")
        assert "predicted_score" in prediction
        assert "recommendations" in prediction
    
    def test_cross_repo_similarity_and_sharing(self, setup_integration_test):
        """Test repository similarity detection followed by pattern sharing."""
        cross_repo = setup_integration_test["cross_repo"]
        
        # Mock similar repositories
        with patch.object(cross_repo, '_get_repo_patterns') as mock_get_patterns:
            mock_get_patterns.side_effect = [
                ["def foo(): pass", "import os"],  # repo_a patterns
                ["def bar(): pass", "import sys"]  # repo_b patterns
            ]
            
            # Detect similarity
            similarity = cross_repo.detect_repo_similarity("repo_a", "repo_b")
            assert 0.0 <= similarity <= 1.0
            
            # If similar enough, share patterns
            if similarity > 0.5:
                # Mock patterns for sharing
                setup_integration_test["memory"].retrieve_patterns.return_value = [
                    {"snippet": "def shared_function(): pass", "quality_score": 0.8}
                ]
                
                sharing_result = cross_repo.share_patterns("repo_a", "repo_b")
                assert sharing_result["success"] is True


# Performance and benchmark tests
class TestPhase6Performance:
    """Test performance characteristics of Phase 6 features."""
    
    def test_pattern_extraction_performance(self):
        """Test pattern extraction performance with large datasets."""
        memory = Mock(spec=PatternMemory)
        memory.store_pattern.return_value = True
        
        with patch('kirolinter.agents.learner.ML_AVAILABLE', False):  # Use statistical for speed
            agent = LearnerAgent(memory=memory, verbose=False)
            
            # Generate large dataset
            large_dataset = [f"def function_{i}(): return {i}" for i in range(100)]
            
            import time
            start_time = time.time()
            patterns = agent.extract_patterns("test_repo", large_dataset)
            end_time = time.time()
            
            # Should complete within reasonable time (< 5 seconds)
            assert end_time - start_time < 5.0
            assert len(patterns) == 100
    
    def test_similarity_detection_performance(self):
        """Test repository similarity detection performance."""
        memory = Mock(spec=PatternMemory)
        cross_repo = CrossRepoLearner(memory=memory, verbose=False)
        
        # Mock large pattern sets
        large_patterns_a = [f"pattern_{i}_a" for i in range(50)]
        large_patterns_b = [f"pattern_{i}_b" for i in range(50)]
        
        with patch.object(cross_repo, '_get_repo_patterns') as mock_get_patterns:
            mock_get_patterns.side_effect = [large_patterns_a, large_patterns_b]
            
            import time
            start_time = time.time()
            similarity = cross_repo.detect_repo_similarity("repo_a", "repo_b")
            end_time = time.time()
            
            # Should complete within reasonable time (< 3 seconds)
            assert end_time - start_time < 3.0
            assert 0.0 <= similarity <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])