"""
Tests for Phase 4 Intelligent Integrator Agent.

Tests smart PR management, categorization, and stakeholder notifications.
"""

import pytest
from unittest.mock import Mock, patch

from kirolinter.agents.integrator import IntegratorAgent, MockGitHubClient


class TestIntelligentIntegrator:
    """Test intelligent integrator agent capabilities."""
    
    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch('kirolinter.agents.integrator.get_chat_model') as mock:
            mock.return_value = Mock()
            yield mock
    
    @pytest.fixture
    def mock_memory(self):
        """Create mock PatternMemory."""
        memory = Mock()
        memory.get_team_patterns.return_value = [
            {
                "pattern_data": {
                    "issue_id": "security_fix_1",
                    "fix_type": "security"
                },
                "confidence": 0.9
            },
            {
                "pattern_data": {
                    "issue_id": "style_fix_1",
                    "fix_type": "style"
                },
                "confidence": 0.8
            }
        ]
        memory.store_pattern.return_value = True
        return memory
    
    def test_fix_categorization(self, mock_memory):
        """Test intelligent fix categorization using patterns."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        fixes = ["security_fix_1", "code_quality_fix_2", "style_fix_1", "performance_fix_3"]
        
        categories = integrator._categorize_fixes(fixes, "/test/repo")
        
        # Should have categorized fixes based on patterns and inference
        assert isinstance(categories, dict)
        assert "security" in categories
        assert "style" in categories
        
        # Security fix should be in security category
        assert "security_fix_1" in categories["security"]
        assert "style_fix_1" in categories["style"]
    
    def test_fix_type_inference(self, mock_memory):
        """Test fix type inference from fix IDs."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        # Test various fix ID patterns
        assert integrator._infer_fix_type("security_vulnerability_fix") == "security"
        assert integrator._infer_fix_type("sql_injection_fix") == "security"
        assert integrator._infer_fix_type("performance_optimization") == "performance"
        assert integrator._infer_fix_type("memory_leak_fix") == "performance"
        assert integrator._infer_fix_type("code_complexity_reduction") == "maintainability"
        assert integrator._infer_fix_type("pep8_style_fix") == "style"
        assert integrator._infer_fix_type("format_improvement") == "style"
        assert integrator._infer_fix_type("general_fix") == "code_quality"
    
    def test_pr_title_generation(self, mock_memory):
        """Test intelligent PR title generation."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        # Single category
        single_category = {"security": ["fix1", "fix2", "fix3"]}
        title = integrator._generate_pr_title(single_category)
        assert "security" in title.lower()
        assert "3" in title
        
        # Multiple categories
        multi_category = {
            "security": ["fix1"],
            "code_quality": ["fix2", "fix3"],
            "style": ["fix4"]
        }
        title = integrator._generate_pr_title(multi_category)
        assert "4" in title  # Total fixes
        assert "automated fixes" in title.lower()
    
    def test_pr_description_generation(self, mock_memory):
        """Test intelligent PR description generation."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        categories = {
            "security": ["security_fix_1", "security_fix_2"],
            "code_quality": ["quality_fix_1"],
            "style": ["style_fix_1"]
        }
        
        description = integrator._generate_pr_description(categories, "/test/repo")
        
        # Should contain key sections
        assert "KiroLinter Automated Fixes" in description
        assert "Fix Categories" in description
        assert "Safety Information" in description
        assert "Review Guidance" in description
        
        # Should mention specific categories
        assert "Security" in description
        assert "Code_Quality" in description or "Code Quality" in description
        assert "Style" in description
        
        # Should show correct counts
        assert "4 automated fixes" in description
    
    def test_reviewer_assignment(self, mock_memory):
        """Test automatic reviewer assignment based on categories."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        # Mock PR object
        pr = {"number": 123, "reviewers": []}
        
        # Test security fixes
        security_categories = {"security": ["fix1", "fix2"]}
        integrator._assign_reviewers(pr, security_categories)
        
        # Should have assigned security reviewers
        assert "reviewers" in pr
        expected_reviewers = ["security_team", "security_lead"]
        assert any(reviewer in expected_reviewers for reviewer in pr["reviewers"])
        
        # Test performance fixes
        pr = {"number": 124, "reviewers": []}
        performance_categories = {"performance": ["fix1"]}
        integrator._assign_reviewers(pr, performance_categories)
        
        expected_reviewers = ["performance_team", "tech_lead"]
        assert any(reviewer in expected_reviewers for reviewer in pr["reviewers"])
    
    def test_stakeholder_notifications(self, mock_memory):
        """Test stakeholder notification system."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        pr = {"number": 123}
        categories = {
            "security": ["security_fix"],
            "code_quality": ["quality_fix"]
        }
        
        # Mock the notification sending
        with patch.object(integrator, '_send_notification') as mock_send:
            integrator._notify_stakeholders(pr, categories)
            
            # Should have sent notifications
            assert mock_send.called
            
            # Check notification calls
            calls = mock_send.call_args_list
            assert len(calls) >= 1
            
            # Security fixes should trigger high-priority notifications
            security_notification = next(
                (call for call in calls if "security" in str(call)), 
                None
            )
            assert security_notification is not None
    
    def test_complete_pr_creation(self, mock_memory):
        """Test complete PR creation workflow."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        fixes = ["security_fix_1", "code_quality_fix_2", "style_fix_3"]
        
        result = integrator.create_pr("/test/repo", fixes)
        
        # Should have created PR successfully
        assert result["pr_created"] is True
        assert "pr_number" in result
        assert "categories" in result
        assert "title" in result
        
        # Should have stored pattern
        mock_memory.store_pattern.assert_called()
        call_args = mock_memory.store_pattern.call_args
        assert call_args[0][0] == "/test/repo"
        assert call_args[0][1] == "pr_created"
        pattern_data = call_args[0][2]
        assert pattern_data["pr_id"] == result["pr_number"]
        assert pattern_data["fixes"] == fixes
        assert "categories" in pattern_data
        assert "title" in pattern_data
    
    def test_empty_fixes_handling(self, mock_memory):
        """Test handling of empty fixes list."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        result = integrator.create_pr("/test/repo", [])
        
        # Should handle empty fixes gracefully
        assert result["pr_created"] is False
        assert "reason" in result
        assert "No fixes" in result["reason"]
    
    def test_mock_github_client(self):
        """Test MockGitHubClient functionality."""
        client = MockGitHubClient(verbose=True)
        
        # Test PR creation
        pr = client.create_pull_request("/test/repo", "Test PR", "Test description")
        
        assert "number" in pr
        assert pr["title"] == "Test PR"
        assert pr["description"] == "Test description"
        assert "url" in pr
        
        # Test reviewer assignment
        reviewers = ["reviewer1", "reviewer2"]
        client.assign_reviewers(pr, reviewers)
        
        assert pr["reviewers"] == reviewers
        
        # Test label addition
        labels = ["bug", "enhancement"]
        client.add_labels(pr, labels)
        
        assert pr["labels"] == labels
    
    def test_legacy_method_compatibility(self, mock_memory):
        """Test backward compatibility with legacy create_fix_pr method."""
        integrator = IntegratorAgent(memory=mock_memory, verbose=True)
        
        fix_results = {"applied_fixes": ["fix1", "fix2"]}
        
        result = integrator.create_fix_pr("/test/repo", fix_results, "Test PR")
        
        # Should return legacy format
        assert "pr_created" in result
        assert "pr_url" in result
        assert "pr_number" in result
        
        # Should have actually created PR
        assert result["pr_created"] is True


if __name__ == "__main__":
    pytest.main([__file__])