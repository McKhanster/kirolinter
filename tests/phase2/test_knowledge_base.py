"""
Tests for Knowledge Base System (Phase 2).

Tests the KnowledgeBase class with pattern storage, fix templates,
team insights, and semantic search capabilities.
"""

import pytest
import tempfile
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from kirolinter.memory.knowledge_base import KnowledgeBase


class TestKnowledgeBase:
    """Test KnowledgeBase functionality."""
    
    @pytest.fixture
    def temp_knowledge_dir(self):
        """Create temporary knowledge directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def knowledge_base(self, temp_knowledge_dir):
        """Create KnowledgeBase instance with temporary directory."""
        return KnowledgeBase(temp_knowledge_dir)
    
    def test_pattern_storage_and_retrieval(self, knowledge_base):
        """Test storing and retrieving coding patterns."""
        pattern_id = "snake_case_naming"
        pattern_data = {
            "description": "Use snake_case for variable names",
            "examples": ["user_name", "file_path", "data_count"],
            "anti_examples": ["userName", "filePath", "dataCount"]
        }
        
        # Store pattern
        success = knowledge_base.store_pattern(
            pattern_id, pattern_data, category="naming", tags=["python", "style"]
        )
        assert success
        
        # Retrieve specific pattern
        retrieved = knowledge_base.get_pattern(pattern_id)
        assert retrieved is not None
        assert retrieved["id"] == pattern_id
        assert retrieved["category"] == "naming"
        assert "python" in retrieved["tags"]
        assert retrieved["data"]["description"] == pattern_data["description"]
    
    def test_pattern_search_functionality(self, knowledge_base):
        """Test semantic pattern search."""
        # Store multiple patterns
        patterns = [
            ("snake_case", {"desc": "Snake case naming"}, "naming", ["python"]),
            ("camel_case", {"desc": "Camel case naming"}, "naming", ["javascript"]),
            ("security_check", {"desc": "Input validation"}, "security", ["python"]),
            ("loop_optimization", {"desc": "Efficient loops"}, "performance", ["python"])
        ]
        
        for pattern_id, data, category, tags in patterns:
            knowledge_base.store_pattern(pattern_id, data, category, tags)
        
        # Search by query
        results = knowledge_base.search_patterns("naming", limit=5)
        assert len(results) >= 2  # Should find naming-related patterns
        
        # Verify relevance scoring
        for result in results:
            assert "relevance_score" in result
            assert result["relevance_score"] > 0
        
        # Search with category filter
        naming_results = knowledge_base.search_patterns("case", category="naming")
        assert len(naming_results) == 2
        assert all(r["category"] == "naming" for r in naming_results)
        
        # Search with tags filter
        python_results = knowledge_base.search_patterns("python", tags=["python"])
        assert len(python_results) >= 2
        assert all("python" in r["tags"] for r in python_results)
    
    def test_fix_template_management(self, knowledge_base):
        """Test fix template storage and success rate tracking."""
        template_id = "remove_unused_import"
        template_data = {
            "description": "Remove unused import statements",
            "pattern": r"^import\s+(\w+).*$",
            "replacement": "",
            "conditions": ["import_not_used"]
        }
        
        # Store fix template
        success = knowledge_base.store_fix_template(
            template_id, template_data, "style", success_rate=0.8
        )
        assert success
        
        # Get fix templates
        templates = knowledge_base.get_fix_templates("style")
        assert len(templates) == 1
        assert templates[0]["id"] == template_id
        assert templates[0]["success_rate"] == 0.8
        
        # Update success rate
        success = knowledge_base.update_template_success_rate(template_id, True)
        assert success
        
        # Verify success rate was updated
        updated_templates = knowledge_base.get_fix_templates("style")
        updated_rate = updated_templates[0]["success_rate"]
        assert updated_rate > 0.8  # Should increase with successful application
        
        # Test with failure
        knowledge_base.update_template_success_rate(template_id, False)
        failed_templates = knowledge_base.get_fix_templates("style")
        failed_rate = failed_templates[0]["success_rate"]
        assert failed_rate < updated_rate  # Should decrease with failure
    
    def test_team_insights_storage(self, knowledge_base):
        """Test team insights storage and retrieval."""
        repo_path = "/test/repo"
        
        # Store team insights
        insight_data = {
            "code_quality_trend": "improving",
            "common_issues": ["unused_imports", "long_lines"],
            "team_preferences": {"naming": "snake_case", "imports": "from_import"}
        }
        
        success = knowledge_base.store_team_insight(
            repo_path, insight_data, "quality_analysis"
        )
        assert success
        
        # Store another insight
        style_insight = {
            "preferred_line_length": 88,
            "indentation": "spaces",
            "quote_style": "double"
        }
        
        knowledge_base.store_team_insight(repo_path, style_insight, "style_analysis")
        
        # Retrieve insights
        all_insights = knowledge_base.get_team_insights(repo_path)
        assert len(all_insights) == 2
        
        # Filter by type
        quality_insights = knowledge_base.get_team_insights(repo_path, "quality_analysis")
        assert len(quality_insights) == 1
        assert quality_insights[0]["data"]["code_quality_trend"] == "improving"
    
    def test_best_practices_management(self, knowledge_base):
        """Test best practices storage and retrieval."""
        practice_id = "function_naming"
        practice_data = {
            "title": "Function Naming Conventions",
            "description": "Use descriptive names for functions",
            "examples": ["calculate_total", "validate_input", "process_data"],
            "rationale": "Improves code readability and maintainability"
        }
        
        # Store best practice
        success = knowledge_base.store_best_practice(
            practice_id, practice_data, "naming", "python"
        )
        assert success
        
        # Retrieve best practices
        practices = knowledge_base.get_best_practices("naming", "python")
        assert len(practices) == 1
        assert practices[0]["id"] == practice_id
        assert practices[0]["data"]["title"] == practice_data["title"]
        
        # Test retrieval without category filter
        all_practices = knowledge_base.get_best_practices(language="python")
        assert len(all_practices) >= 1
    
    def test_knowledge_summary(self, knowledge_base):
        """Test knowledge base summary generation."""
        # Add various types of knowledge
        knowledge_base.store_pattern("test_pattern", {"data": "test"}, "test")
        knowledge_base.store_fix_template("test_template", {"data": "test"}, "test")
        knowledge_base.store_team_insight("/repo", {"data": "test"}, "test")
        knowledge_base.store_best_practice("test_practice", {"data": "test"}, "test")
        
        # Get summary
        summary = knowledge_base.get_knowledge_summary()
        
        assert summary["total_patterns"] == 1
        assert summary["total_fix_templates"] == 1
        assert summary["total_repositories_with_insights"] == 1
        assert summary["total_best_practices"] == 1
        assert "test" in summary["pattern_categories"]
        assert "test" in summary["template_issue_types"]
        assert "/repo" in summary["insight_repositories"]
        assert "test" in summary["best_practice_categories"]
    
    def test_knowledge_export_import(self, knowledge_base):
        """Test knowledge base export and import functionality."""
        # Add test data
        knowledge_base.store_pattern("pattern1", {"data": "p1"}, "cat1")
        knowledge_base.store_fix_template("template1", {"data": "t1"}, "issue1")
        knowledge_base.store_team_insight("/repo1", {"data": "i1"}, "insight1")
        knowledge_base.store_best_practice("practice1", {"data": "bp1"}, "cat1")
        
        # Export knowledge
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        try:
            success = knowledge_base.export_knowledge(export_file)
            assert success
            assert os.path.exists(export_file)
            
            # Verify export content
            with open(export_file, 'r') as f:
                export_data = json.load(f)
            
            assert "patterns" in export_data
            assert "fix_templates" in export_data
            assert "team_insights" in export_data
            assert "best_practices" in export_data
            assert "summary" in export_data
            
            # Test import with merge
            with tempfile.TemporaryDirectory() as temp_dir:
                new_kb = KnowledgeBase(temp_dir)
                import_success = new_kb.import_knowledge(export_file, merge=True)
                assert import_success
            
            # Verify imported data
            imported_patterns = new_kb.search_patterns("pattern1")
            assert len(imported_patterns) >= 1  # May have duplicates due to merge
            
            imported_templates = new_kb.get_fix_templates("issue1")
            assert len(imported_templates) == 1
            
            imported_insights = new_kb.get_team_insights("/repo1")
            assert len(imported_insights) == 1
            
            imported_practices = new_kb.get_best_practices("cat1")
            assert len(imported_practices) == 1
            
        finally:
            if os.path.exists(export_file):
                os.unlink(export_file)
    
    def test_pattern_usage_tracking(self, knowledge_base):
        """Test that pattern usage is tracked correctly."""
        pattern_id = "usage_test"
        pattern_data = {"description": "Test pattern for usage tracking"}
        
        # Store pattern
        knowledge_base.store_pattern(pattern_id, pattern_data)
        
        # Get initial pattern
        pattern = knowledge_base.get_pattern(pattern_id)
        initial_usage = pattern["usage_count"]
        
        # Update pattern (should increment usage)
        updated_data = {"description": "Updated test pattern"}
        knowledge_base.store_pattern(pattern_id, updated_data)
        
        # Verify usage count increased
        updated_pattern = knowledge_base.get_pattern(pattern_id)
        assert updated_pattern["usage_count"] == initial_usage + 1
    
    def test_fix_template_filtering(self, knowledge_base):
        """Test fix template filtering by success rate."""
        # Store templates with different success rates
        templates = [
            ("high_success", {"data": "good"}, "style", 0.9),
            ("medium_success", {"data": "ok"}, "style", 0.6),
            ("low_success", {"data": "bad"}, "style", 0.3)
        ]
        
        for template_id, data, issue_type, success_rate in templates:
            knowledge_base.store_fix_template(template_id, data, issue_type, success_rate)
        
        # Get all templates
        all_templates = knowledge_base.get_fix_templates("style")
        assert len(all_templates) == 3
        
        # Filter by minimum success rate
        good_templates = knowledge_base.get_fix_templates("style", min_success_rate=0.7)
        assert len(good_templates) == 1
        assert good_templates[0]["id"] == "high_success"
        
        # Verify sorting (highest success rate first)
        assert all_templates[0]["success_rate"] >= all_templates[1]["success_rate"]
        assert all_templates[1]["success_rate"] >= all_templates[2]["success_rate"]
    
    def test_team_insights_time_filtering(self, knowledge_base):
        """Test team insights filtering by time."""
        repo_path = "/test/repo"
        
        # Store insight
        knowledge_base.store_team_insight(repo_path, {"data": "recent"}, "test")
        
        # Get recent insights (should include the one we just stored)
        recent_insights = knowledge_base.get_team_insights(repo_path, days_back=1)
        assert len(recent_insights) == 1
        
        # Get very old insights (should be empty)
        old_insights = knowledge_base.get_team_insights(repo_path, days_back=0)
        assert len(old_insights) == 0
    
    def test_knowledge_base_persistence(self, knowledge_base):
        """Test that knowledge base data persists across instances."""
        # Store data
        knowledge_base.store_pattern("persist_test", {"data": "persistent"})
        
        # Create new instance with same directory
        knowledge_dir = knowledge_base.knowledge_dir
        new_kb = KnowledgeBase(str(knowledge_dir))
        
        # Verify data persisted
        pattern = new_kb.get_pattern("persist_test")
        assert pattern is not None
        assert pattern["data"]["data"] == "persistent"


if __name__ == "__main__":
    pytest.main([__file__])