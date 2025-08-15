"""
Conversation Memory for KiroLinter AI Agents.

This module provides memory capabilities for maintaining context across
agent interactions and conversations with intelligent summarization.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import json
import os
import logging
import hashlib
from pathlib import Path
from collections import defaultdict, Counter


class ConversationMemory:
    """
    Enhanced memory system for maintaining conversation context across agent interactions.
    
    Features:
    - Stores conversation history with timestamps and agent tracking
    - Maintains context across sessions with intelligent summarization
    - Supports multi-agent conversation tracking
    - Session management for concurrent agent interactions
    - Automatic memory compression and cleanup
    - Context retrieval for relevant historical information
    """
    
    def __init__(self, memory_file: Optional[str] = None, max_history: int = 100, 
                 max_session_age_hours: int = 24):
        """
        Initialize enhanced conversation memory.
        
        Args:
            memory_file: Optional file path for persistent storage
            max_history: Maximum number of interactions to keep in memory
            max_session_age_hours: Maximum age of sessions before cleanup
        """
        self.max_history = max_history
        self.max_session_age_hours = max_session_age_hours
        self.conversation_history: List[Dict[str, Any]] = []
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.agent_interactions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.summaries: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        
        # Set up persistent storage
        if memory_file:
            self.memory_file = Path(memory_file)
        else:
            # Default to .kiro directory
            kiro_dir = Path.cwd() / ".kiro" / "agent_memory"
            kiro_dir.mkdir(parents=True, exist_ok=True)
            self.memory_file = kiro_dir / "conversation_memory.json"
        
        # Load existing memory
        self._load_memory()
    
    def add_interaction(self, user_input: str, agent_response: str, 
                       agent_name: str = "system", session_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a new interaction to conversation memory with enhanced tracking.
        
        Args:
            user_input: User's input or query
            agent_response: Agent's response
            agent_name: Name of the agent that responded
            session_id: Optional session identifier for grouping interactions
            metadata: Optional metadata about the interaction
            
        Returns:
            Interaction ID for reference
        """
        now = datetime.now()
        interaction_id = hashlib.md5(f"{agent_name}_{now.isoformat()}_{user_input[:50]}".encode()).hexdigest()[:12]
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = f"session_{now.strftime('%Y%m%d_%H%M%S')}"
        
        interaction = {
            "id": interaction_id,
            "timestamp": now.isoformat(),
            "agent_name": agent_name,
            "session_id": session_id,
            "user_input": user_input,
            "agent_response": agent_response,
            "metadata": metadata or {},
            "context_length": len(user_input) + len(agent_response)
        }
        
        # Add to main history
        self.conversation_history.append(interaction)
        
        # Track by agent
        self.agent_interactions[agent_name].append(interaction)
        
        # Update session tracking
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": now.isoformat(),
                "agents_involved": set(),
                "interaction_count": 0,
                "total_context_length": 0
            }
        
        session = self.sessions[session_id]
        session["agents_involved"].add(agent_name)
        session["interaction_count"] += 1
        session["total_context_length"] += interaction["context_length"]
        session["last_activity"] = now.isoformat()
        
        # Check if we need to summarize or trim
        self._manage_memory_size()
        
        # Persist to disk
        self._save_memory()
        
        return interaction_id
    
    def get_conversation_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            last_n: Optional number of recent interactions to return
            
        Returns:
            List of conversation interactions
        """
        if last_n:
            return self.conversation_history[-last_n:]
        return self.conversation_history.copy()
    
    def get_context_for_agent(self, agent_name: str, last_n: int = 5, 
                             include_summaries: bool = True) -> str:
        """
        Get formatted context for a specific agent with intelligent context selection.
        
        Args:
            agent_name: Name of the agent requesting context
            last_n: Number of recent interactions to include
            include_summaries: Whether to include conversation summaries
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Include relevant summaries if requested
        if include_summaries and self.summaries:
            recent_summaries = [s for s in self.summaries[-3:] if agent_name in s.get("agents_involved", [])]
            if recent_summaries:
                context_parts.append("Previous conversation summaries:")
                for summary in recent_summaries:
                    context_parts.append(f"- {summary['summary']} (from {summary['period']})")
                context_parts.append("")
        
        # Get recent interactions, prioritizing those involving the requesting agent
        agent_interactions = [i for i in self.conversation_history if i["agent_name"] == agent_name]
        other_interactions = [i for i in self.conversation_history if i["agent_name"] != agent_name]
        
        # Mix agent-specific and general interactions
        recent_agent = agent_interactions[-max(1, last_n // 2):] if agent_interactions else []
        recent_other = other_interactions[-max(1, last_n // 2):] if other_interactions else []
        
        # Combine and sort by timestamp
        combined_interactions = recent_agent + recent_other
        combined_interactions.sort(key=lambda x: x["timestamp"])
        recent_history = combined_interactions[-last_n:] if combined_interactions else []
        
        if not recent_history and not context_parts:
            return "No previous conversation history available."
        
        if recent_history:
            context_parts.append("Recent conversation context:")
            
            for interaction in recent_history:
                timestamp = interaction["timestamp"]
                user_input = interaction["user_input"]
                response = interaction["agent_response"]
                responding_agent = interaction["agent_name"]
                session_id = interaction.get("session_id", "unknown")
                
                # Truncate long inputs/responses for context
                user_input_short = user_input[:200] + "..." if len(user_input) > 200 else user_input
                response_short = response[:200] + "..." if len(response) > 200 else response
                
                context_parts.append(f"\n[{timestamp[:19]}] [{session_id}] User: {user_input_short}")
                context_parts.append(f"[{timestamp[:19]}] [{session_id}] {responding_agent}: {response_short}")
        
        return "\n".join(context_parts)
    
    def search_history(self, query: str, limit: int = 10, agent_name: Optional[str] = None,
                      session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search conversation history for relevant interactions with enhanced filtering.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            agent_name: Optional filter by agent name
            session_id: Optional filter by session ID
            
        Returns:
            List of matching interactions with relevance scores
        """
        query_lower = query.lower()
        matches = []
        
        for interaction in self.conversation_history:
            # Apply filters
            if agent_name and interaction["agent_name"] != agent_name:
                continue
            if session_id and interaction.get("session_id") != session_id:
                continue
            
            # Calculate relevance score
            relevance_score = 0
            user_input = interaction["user_input"].lower()
            agent_response = interaction["agent_response"].lower()
            
            # Exact phrase matches get higher scores
            if query_lower in user_input:
                relevance_score += 2
            if query_lower in agent_response:
                relevance_score += 2
            
            # Word matches get lower scores
            query_words = query_lower.split()
            for word in query_words:
                if word in user_input:
                    relevance_score += 1
                if word in agent_response:
                    relevance_score += 1
            
            if relevance_score > 0:
                interaction_copy = interaction.copy()
                interaction_copy["relevance_score"] = relevance_score
                matches.append(interaction_copy)
        
        # Sort by relevance score and recency
        matches.sort(key=lambda x: (x["relevance_score"], x["timestamp"]), reverse=True)
        return matches[:limit]
    
    def create_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Create an intelligent summary of a conversation session.
        
        Args:
            session_id: Session ID to summarize
            
        Returns:
            Summary dictionary or None if session not found
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        session_interactions = [i for i in self.conversation_history if i.get("session_id") == session_id]
        
        if not session_interactions:
            return None
        
        # Extract key information
        topics = Counter()
        agents_involved = list(session["agents_involved"])
        total_interactions = len(session_interactions)
        
        # Analyze topics and key phrases
        for interaction in session_interactions:
            user_input = interaction["user_input"].lower()
            agent_response = interaction["agent_response"].lower()
            
            # Simple keyword extraction (could be enhanced with NLP)
            words = (user_input + " " + agent_response).split()
            for word in words:
                if len(word) > 4 and word.isalpha():  # Filter meaningful words
                    topics[word] += 1
        
        # Get top topics
        top_topics = [topic for topic, count in topics.most_common(5)]
        
        # Create summary
        summary = {
            "session_id": session_id,
            "created_at": session["created_at"],
            "last_activity": session.get("last_activity", session["created_at"]),
            "agents_involved": agents_involved,
            "total_interactions": total_interactions,
            "top_topics": top_topics,
            "summary": self._generate_session_summary_text(session_interactions, top_topics, agents_involved),
            "period": f"{session['created_at'][:10]} to {session.get('last_activity', session['created_at'])[:10]}"
        }
        
        return summary
    
    def _generate_session_summary_text(self, interactions: List[Dict[str, Any]], 
                                     topics: List[str], agents: List[str]) -> str:
        """Generate human-readable summary text for a session."""
        if not interactions:
            return "Empty session with no interactions."
        
        agent_list = ", ".join(agents) if len(agents) > 1 else agents[0] if agents else "unknown"
        topic_list = ", ".join(topics[:3]) if topics else "general discussion"
        
        summary_parts = [
            f"Session with {len(interactions)} interactions involving {agent_list}.",
            f"Main topics discussed: {topic_list}."
        ]
        
        # Add specific insights based on interaction patterns
        if len(interactions) > 10:
            summary_parts.append("Extended conversation with detailed discussion.")
        elif any("error" in i["user_input"].lower() or "problem" in i["user_input"].lower() for i in interactions):
            summary_parts.append("Session focused on troubleshooting and problem resolution.")
        elif any("implement" in i["user_input"].lower() or "create" in i["user_input"].lower() for i in interactions):
            summary_parts.append("Session focused on implementation and development tasks.")
        
        return " ".join(summary_parts)
    
    def _manage_memory_size(self) -> None:
        """Manage memory size by creating summaries and trimming old data."""
        # Create summaries for old sessions before trimming
        if len(self.conversation_history) > self.max_history * 0.8:
            self._create_summaries_for_old_sessions()
        
        # Trim history if it exceeds max_history
        if len(self.conversation_history) > self.max_history:
            # Keep the most recent interactions
            old_interactions = self.conversation_history[:-self.max_history]
            self.conversation_history = self.conversation_history[-self.max_history:]
            
            # Update agent interactions
            for agent_name in self.agent_interactions:
                self.agent_interactions[agent_name] = [
                    i for i in self.agent_interactions[agent_name] 
                    if i in self.conversation_history
                ]
        
        # Clean up old sessions
        self._cleanup_old_sessions()
    
    def _create_summaries_for_old_sessions(self) -> None:
        """Create summaries for sessions that are about to be trimmed."""
        cutoff_time = datetime.now() - timedelta(hours=self.max_session_age_hours)
        
        for session_id, session_data in list(self.sessions.items()):
            session_time = datetime.fromisoformat(session_data["created_at"])
            
            if session_time < cutoff_time:
                # Create summary if not already exists
                existing_summary = next((s for s in self.summaries if s["session_id"] == session_id), None)
                if not existing_summary:
                    summary = self.create_session_summary(session_id)
                    if summary:
                        self.summaries.append(summary)
                        self.logger.info(f"Created summary for session {session_id}")
    
    def _cleanup_old_sessions(self) -> None:
        """Clean up old session data."""
        cutoff_time = datetime.now() - timedelta(hours=self.max_session_age_hours * 2)  # Keep sessions longer than summaries
        
        sessions_to_remove = []
        for session_id, session_data in self.sessions.items():
            session_time = datetime.fromisoformat(session_data["created_at"])
            if session_time < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            self.logger.info(f"Cleaned up old session {session_id}")
        
        # Limit summaries to prevent unbounded growth
        if len(self.summaries) > 50:
            self.summaries = self.summaries[-50:]
    
    def get_agent_statistics(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about agent interactions.
        
        Args:
            agent_name: Optional specific agent to analyze
            
        Returns:
            Dictionary with agent statistics
        """
        if agent_name:
            interactions = self.agent_interactions.get(agent_name, [])
            return {
                "agent_name": agent_name,
                "total_interactions": len(interactions),
                "first_interaction": interactions[0]["timestamp"] if interactions else None,
                "last_interaction": interactions[-1]["timestamp"] if interactions else None,
                "avg_response_length": sum(len(i["agent_response"]) for i in interactions) / len(interactions) if interactions else 0,
                "sessions_involved": len(set(i.get("session_id") for i in interactions if i.get("session_id")))
            }
        else:
            # Overall statistics
            agent_counts = Counter(i["agent_name"] for i in self.conversation_history)
            return {
                "total_interactions": len(self.conversation_history),
                "total_agents": len(self.agent_interactions),
                "total_sessions": len(self.sessions),
                "total_summaries": len(self.summaries),
                "agent_distribution": dict(agent_counts),
                "most_active_agent": agent_counts.most_common(1)[0] if agent_counts else None
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific session.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            Session information or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id].copy()
        session["agents_involved"] = list(session["agents_involved"])  # Convert set to list for JSON serialization
        
        # Add interaction details
        session_interactions = [i for i in self.conversation_history if i.get("session_id") == session_id]
        session["interactions"] = session_interactions
        
        return session
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the conversation memory.
        
        Returns:
            Dictionary containing memory statistics and summary
        """
        if not self.conversation_history:
            return {
                "total_interactions": 0,
                "agents_involved": [],
                "active_sessions": 0,
                "total_summaries": 0,
                "date_range": None,
                "summary": "No conversation history available."
            }
        
        # Calculate statistics
        agents_involved = list(set(interaction["agent_name"] for interaction in self.conversation_history))
        
        first_interaction = self.conversation_history[0]["timestamp"]
        last_interaction = self.conversation_history[-1]["timestamp"]
        
        # Count active sessions (sessions with activity in last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        active_sessions = 0
        for session_data in self.sessions.values():
            last_activity = session_data.get("last_activity", session_data["created_at"])
            if datetime.fromisoformat(last_activity) > cutoff_time:
                active_sessions += 1
        
        return {
            "total_interactions": len(self.conversation_history),
            "agents_involved": agents_involved,
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "total_summaries": len(self.summaries),
            "date_range": {
                "first": first_interaction,
                "last": last_interaction
            },
            "memory_file": str(self.memory_file),
            "max_history": self.max_history,
            "max_session_age_hours": self.max_session_age_hours
        }
    
    def clear_memory(self, preserve_summaries: bool = False) -> None:
        """
        Clear conversation memory with option to preserve summaries.
        
        Args:
            preserve_summaries: Whether to keep existing summaries
        """
        self.conversation_history = []
        self.sessions = {}
        self.agent_interactions = defaultdict(list)
        
        if not preserve_summaries:
            self.summaries = []
        
        self._save_memory()
    
    def export_memory(self, export_path: str) -> bool:
        """
        Export conversation memory to a file.
        
        Args:
            export_path: Path to export file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "total_interactions": len(self.conversation_history),
                "conversation_history": self.conversation_history
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Failed to export memory: {e}")
            return False
    
    def _load_memory(self) -> None:
        """Load enhanced conversation memory from disk."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Load conversation history
                    self.conversation_history = data.get("conversation_history", [])
                    
                    # Load sessions (convert agents_involved back to sets)
                    sessions_data = data.get("sessions", {})
                    for session_id, session_info in sessions_data.items():
                        session_info["agents_involved"] = set(session_info.get("agents_involved", []))
                        self.sessions[session_id] = session_info
                    
                    # Load summaries
                    self.summaries = data.get("summaries", [])
                    
                    # Rebuild agent interactions index
                    self.agent_interactions = defaultdict(list)
                    for interaction in self.conversation_history:
                        agent_name = interaction["agent_name"]
                        self.agent_interactions[agent_name].append(interaction)
                    
                    # Ensure we don't exceed max_history
                    if len(self.conversation_history) > self.max_history:
                        self.conversation_history = self.conversation_history[-self.max_history:]
                        
        except Exception as e:
            self.logger.error(f"Failed to load memory from {self.memory_file}: {e}")
            self.conversation_history = []
            self.sessions = {}
            self.agent_interactions = defaultdict(list)
            self.summaries = []
    
    def _save_memory(self) -> None:
        """Save enhanced conversation memory to disk."""
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert sessions for JSON serialization (sets to lists)
            sessions_for_json = {}
            for session_id, session_info in self.sessions.items():
                session_copy = session_info.copy()
                session_copy["agents_involved"] = list(session_copy["agents_involved"])
                sessions_for_json[session_id] = session_copy
            
            data = {
                "saved_at": datetime.now().isoformat(),
                "total_interactions": len(self.conversation_history),
                "total_sessions": len(self.sessions),
                "total_summaries": len(self.summaries),
                "max_history": self.max_history,
                "max_session_age_hours": self.max_session_age_hours,
                "conversation_history": self.conversation_history,
                "sessions": sessions_for_json,
                "summaries": self.summaries
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save memory to {self.memory_file}: {e}")
    
    def __len__(self) -> int:
        """Return the number of interactions in memory."""
        return len(self.conversation_history)
    
    def __str__(self) -> str:
        """Return string representation of enhanced memory."""
        summary = self.get_summary()
        return (f"ConversationMemory({summary['total_interactions']} interactions, "
                f"{len(summary['agents_involved'])} agents, {summary['total_sessions']} sessions, "
                f"{summary['total_summaries']} summaries)")