"""
Conversation Memory for KiroLinter AI Agents.

This module provides memory capabilities for maintaining context across
agent interactions and conversations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path


class ConversationMemory:
    """
    Memory system for maintaining conversation context across agent interactions.
    
    Features:
    - Stores conversation history with timestamps
    - Maintains context across sessions
    - Supports memory summarization for long conversations
    - Persists memory to disk for session continuity
    """
    
    def __init__(self, memory_file: Optional[str] = None, max_history: int = 100):
        """
        Initialize conversation memory.
        
        Args:
            memory_file: Optional file path for persistent storage
            max_history: Maximum number of interactions to keep in memory
        """
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
        
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
                       agent_name: str = "system", metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new interaction to conversation memory.
        
        Args:
            user_input: User's input or query
            agent_response: Agent's response
            agent_name: Name of the agent that responded
            metadata: Optional metadata about the interaction
        """
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "user_input": user_input,
            "agent_response": agent_response,
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(interaction)
        
        # Trim history if it exceeds max_history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Persist to disk
        self._save_memory()
    
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
    
    def get_context_for_agent(self, agent_name: str, last_n: int = 5) -> str:
        """
        Get formatted context for a specific agent.
        
        Args:
            agent_name: Name of the agent requesting context
            last_n: Number of recent interactions to include
            
        Returns:
            Formatted context string
        """
        recent_history = self.get_conversation_history(last_n)
        
        if not recent_history:
            return "No previous conversation history."
        
        context_parts = ["Recent conversation context:"]
        
        for interaction in recent_history:
            timestamp = interaction["timestamp"]
            user_input = interaction["user_input"]
            response = interaction["agent_response"]
            responding_agent = interaction["agent_name"]
            
            context_parts.append(f"\n[{timestamp}] User: {user_input}")
            context_parts.append(f"[{timestamp}] {responding_agent}: {response}")
        
        return "\n".join(context_parts)
    
    def search_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search conversation history for relevant interactions.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching interactions
        """
        query_lower = query.lower()
        matches = []
        
        for interaction in self.conversation_history:
            # Search in user input and agent response
            if (query_lower in interaction["user_input"].lower() or 
                query_lower in interaction["agent_response"].lower()):
                matches.append(interaction)
        
        # Return most recent matches first
        return matches[-limit:] if matches else []
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation memory.
        
        Returns:
            Dictionary containing memory statistics and summary
        """
        if not self.conversation_history:
            return {
                "total_interactions": 0,
                "agents_involved": [],
                "date_range": None,
                "summary": "No conversation history available."
            }
        
        # Calculate statistics
        agents_involved = list(set(interaction["agent_name"] for interaction in self.conversation_history))
        
        first_interaction = self.conversation_history[0]["timestamp"]
        last_interaction = self.conversation_history[-1]["timestamp"]
        
        return {
            "total_interactions": len(self.conversation_history),
            "agents_involved": agents_involved,
            "date_range": {
                "first": first_interaction,
                "last": last_interaction
            },
            "memory_file": str(self.memory_file),
            "max_history": self.max_history
        }
    
    def clear_memory(self) -> None:
        """Clear all conversation memory."""
        self.conversation_history = []
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
        """Load conversation memory from disk."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = data.get("conversation_history", [])
                    
                    # Ensure we don't exceed max_history
                    if len(self.conversation_history) > self.max_history:
                        self.conversation_history = self.conversation_history[-self.max_history:]
                        
        except Exception as e:
            print(f"Failed to load memory from {self.memory_file}: {e}")
            self.conversation_history = []
    
    def _save_memory(self) -> None:
        """Save conversation memory to disk."""
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "saved_at": datetime.now().isoformat(),
                "total_interactions": len(self.conversation_history),
                "max_history": self.max_history,
                "conversation_history": self.conversation_history
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Failed to save memory to {self.memory_file}: {e}")
    
    def __len__(self) -> int:
        """Return the number of interactions in memory."""
        return len(self.conversation_history)
    
    def __str__(self) -> str:
        """Return string representation of memory."""
        summary = self.get_summary()
        return f"ConversationMemory({summary['total_interactions']} interactions, {len(summary['agents_involved'])} agents)"