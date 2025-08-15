"""
Tests for Enhanced Conversation Memory System (Phase 2).

Tests the enhanced ConversationMemory class with intelligent summarization,
multi-agent tracking, and session management.
"""

import pytest
import tempfile
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from kirolinter.memory.conversation import ConversationMemory


class TestEnhancedConversationMemory:
    """Test enhanced ConversationMemory functionality."""
    
    @pytest.fixture
    def temp_memory_file(self):
        """Create temporary memory file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            memory_file = f.name
        
        yield memory_file
        
        # Cleanup
        if os.path.exists(memory_file):
            os.unlink(memory_file)
    
    @pytest.fixture
    def conversation_memory(self, temp_memory_file):
        """Create ConversationMemory instance with temporary file."""
        return ConversationMemory(temp_memory_file, max_history=50)
    
    def test_enhanced_interaction_tracking(self, conversation_memory):
        """Test enhanced interaction tracking with sessions and metadata."""
        # Add interaction with session tracking
        interaction_id = conversation_memory.add_interaction(
            user_input="How do I fix this code issue?",
            agent_response="I can help you identify and fix the issue.",
            agent_name="reviewer",
            session_id="test_session_1",
            metadata={"issue_type": "syntax", "severity": "high"}
        )
        
        assert interaction_id is not None
        assert len(interaction_id) == 12  # Should be 12-character hash
        
        # Verify interaction was stored
        history = conversation_memory.get_conversation_history()
        assert len(history) == 1
        
        interaction = history[0]
        assert interaction["id"] == interaction_id
        assert interaction["agent_name"] == "reviewer"
        assert interaction["session_id"] == "test_session_1"
        assert interaction["metadata"]["issue_type"] == "syntax"
        assert "context_length" in interaction
    
    def test_session_management(self, conversation_memory):
        """Test session creation and management."""
        session_id = "test_session"
        
        # Add multiple interactions to same session
        conversation_memory.add_interaction(
            "First question", "First response", "agent1", session_id
        )
        conversation_memory.add_interaction(
            "Second question", "Second response", "agent2", session_id
        )
        
        # Check session info
        session_info = conversation_memory.get_session_info(session_id)
        assert session_info is not None
        assert session_info["interaction_count"] == 2
        assert len(session_info["agents_involved"]) == 2
        assert "agent1" in session_info["agents_involved"]
        assert "agent2" in session_info["agents_involved"]
        assert len(session_info["interactions"]) == 2
    
    def test_intelligent_context_retrieval(self, conversation_memory):
        """Test intelligent context retrieval for agents."""
        # Add interactions from different agents
        conversation_memory.add_interaction(
            "Review this code", "Code looks good", "reviewer", "session1"
        )
        conversation_memory.add_interaction(
            "Fix this issue", "Issue fixed", "fixer", "session1"
        )
        conversation_memory.add_interaction(
            "Another review", "Approved", "reviewer", "session2"
        )
        
        # Get context for reviewer (should prioritize reviewer interactions)
        context = conversation_memory.get_context_for_agent("reviewer", last_n=3)
        
        assert "reviewer" in context
        # The context should include reviewer interactions
        # Check that at least one reviewer response is included
        reviewer_responses = ["Code looks good", "Approved"]
        assert any(response in context for response in reviewer_responses), f"Expected reviewer responses in context: {context}"
        
        # Test context with summaries disabled
        context_no_summaries = conversation_memory.get_context_for_agent(
            "reviewer", last_n=2, include_summaries=False
        )
        assert "Previous conversation summaries" not in context_no_summaries
    
    def test_enhanced_search_functionality(self, conversation_memory):
        """Test enhanced search with filtering and relevance scoring."""
        # Add test interactions
        conversation_memory.add_interaction(
            "How to fix syntax error?", "Check your brackets", "helper", "session1"
        )
        conversation_memory.add_interaction(
            "Performance issue", "Optimize your loops", "optimizer", "session2"
        )
        conversation_memory.add_interaction(
            "Another syntax problem", "Review syntax rules", "helper", "session1"
        )
        
        # Search with query
        results = conversation_memory.search_history("syntax", limit=5)
        assert len(results) == 2
        
        # Results should have relevance scores
        for result in results:
            assert "relevance_score" in result
            assert result["relevance_score"] > 0
        
        # Search with agent filter
        helper_results = conversation_memory.search_history(
            "syntax", agent_name="helper", limit=5
        )
        assert len(helper_results) == 2
        assert all(r["agent_name"] == "helper" for r in helper_results)
        
        # Search with session filter
        session1_results = conversation_memory.search_history(
            "syntax", session_id="session1", limit=5
        )
        assert len(session1_results) == 2
        assert all(r["session_id"] == "session1" for r in session1_results)
    
    def test_session_summarization(self, conversation_memory):
        """Test intelligent session summarization."""
        session_id = "summary_test"
        
        # Add interactions with meaningful content
        conversation_memory.add_interaction(
            "I have a function that's not working", 
            "Let me help you debug the function",
            "debugger", session_id
        )
        conversation_memory.add_interaction(
            "The function has a syntax error",
            "I can see the issue - missing parentheses",
            "debugger", session_id
        )
        conversation_memory.add_interaction(
            "How do I fix it?",
            "Add closing parentheses on line 15",
            "debugger", session_id
        )
        
        # Create session summary
        summary = conversation_memory.create_session_summary(session_id)
        
        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["total_interactions"] == 3
        assert "debugger" in summary["agents_involved"]
        assert len(summary["top_topics"]) > 0
        assert "summary" in summary
        assert len(summary["summary"]) > 0
        
        # Summary should contain meaningful information
        summary_text = summary["summary"].lower()
        assert "debugger" in summary_text
        assert "interactions" in summary_text
    
    def test_memory_size_management(self, conversation_memory):
        """Test automatic memory size management and summarization."""
        # Set low max_history for testing
        conversation_memory.max_history = 5
        
        # Add more interactions than max_history
        for i in range(8):
            conversation_memory.add_interaction(
                f"Question {i}", f"Answer {i}", "agent", f"session_{i}"
            )
        
        # Should have trimmed to max_history
        history = conversation_memory.get_conversation_history()
        assert len(history) <= conversation_memory.max_history
        
        # Should have created summaries for old sessions
        # (This is tested indirectly through the memory management)
    
    def test_agent_statistics(self, conversation_memory):
        """Test agent interaction statistics."""
        # Add interactions from different agents
        conversation_memory.add_interaction("Q1", "A1", "agent1", "s1")
        conversation_memory.add_interaction("Q2", "A2", "agent1", "s1")
        conversation_memory.add_interaction("Q3", "A3", "agent2", "s2")
        
        # Get statistics for specific agent
        agent1_stats = conversation_memory.get_agent_statistics("agent1")
        assert agent1_stats["agent_name"] == "agent1"
        assert agent1_stats["total_interactions"] == 2
        assert agent1_stats["sessions_involved"] == 1
        assert agent1_stats["first_interaction"] is not None
        assert agent1_stats["last_interaction"] is not None
        assert agent1_stats["avg_response_length"] > 0
        
        # Get overall statistics
        overall_stats = conversation_memory.get_agent_statistics()
        assert overall_stats["total_interactions"] == 3
        assert overall_stats["total_agents"] == 2
        assert overall_stats["total_sessions"] == 2
        assert "agent_distribution" in overall_stats
        assert overall_stats["agent_distribution"]["agent1"] == 2
        assert overall_stats["agent_distribution"]["agent2"] == 1
    
    def test_enhanced_summary_with_sessions(self, conversation_memory):
        """Test enhanced summary including session information."""
        # Add interactions across multiple sessions
        conversation_memory.add_interaction("Q1", "A1", "agent1", "session1")
        conversation_memory.add_interaction("Q2", "A2", "agent2", "session2")
        
        summary = conversation_memory.get_summary()
        
        assert summary["total_interactions"] == 2
        assert summary["total_sessions"] == 2
        assert summary["active_sessions"] >= 0  # Could be 0 or more depending on timing
        assert summary["total_summaries"] == 0  # No summaries created yet
        assert len(summary["agents_involved"]) == 2
        assert "max_session_age_hours" in summary
    
    def test_memory_persistence_with_sessions(self, conversation_memory):
        """Test that enhanced memory persists correctly across instances."""
        session_id = "persist_test"
        
        # Add interaction with session
        conversation_memory.add_interaction(
            "Test persistence", "Memory should persist", "tester", session_id
        )
        
        # Create new instance with same file
        memory_file = conversation_memory.memory_file
        new_memory = ConversationMemory(str(memory_file))
        
        # Verify data was loaded
        history = new_memory.get_conversation_history()
        assert len(history) == 1
        assert history[0]["session_id"] == session_id
        
        # Verify session was loaded
        session_info = new_memory.get_session_info(session_id)
        assert session_info is not None
        assert session_info["interaction_count"] == 1
    
    def test_clear_memory_with_summaries(self, conversation_memory):
        """Test clearing memory with option to preserve summaries."""
        # Add interactions and create a summary
        conversation_memory.add_interaction("Q1", "A1", "agent1", "session1")
        summary = conversation_memory.create_session_summary("session1")
        if summary:
            conversation_memory.summaries.append(summary)
        
        # Clear memory but preserve summaries
        conversation_memory.clear_memory(preserve_summaries=True)
        
        # Verify interactions are cleared but summaries remain
        assert len(conversation_memory.get_conversation_history()) == 0
        assert len(conversation_memory.sessions) == 0
        if summary:
            assert len(conversation_memory.summaries) > 0
        
        # Clear everything including summaries
        conversation_memory.clear_memory(preserve_summaries=False)
        assert len(conversation_memory.summaries) == 0
    
    def test_session_cleanup(self, conversation_memory):
        """Test automatic cleanup of old sessions."""
        # Set short session age for testing
        conversation_memory.max_session_age_hours = 0.001  # Very short for testing
        
        # Add interaction
        conversation_memory.add_interaction("Q1", "A1", "agent1", "old_session")
        
        # Manually trigger cleanup (normally done automatically)
        conversation_memory._cleanup_old_sessions()
        
        # Session should still exist (cleanup threshold is 2x session age)
        assert "old_session" in conversation_memory.sessions
    
    def test_context_length_tracking(self, conversation_memory):
        """Test that context length is properly tracked."""
        long_input = "This is a very long user input " * 10
        long_response = "This is a very long agent response " * 10
        
        conversation_memory.add_interaction(
            long_input, long_response, "agent", "session1"
        )
        
        history = conversation_memory.get_conversation_history()
        interaction = history[0]
        
        expected_length = len(long_input) + len(long_response)
        assert interaction["context_length"] == expected_length
        
        # Check session context length tracking
        session_info = conversation_memory.get_session_info("session1")
        assert session_info["total_context_length"] == expected_length


if __name__ == "__main__":
    pytest.main([__file__])