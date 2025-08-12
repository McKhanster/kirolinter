"""
KiroLinter Agent Memory System

This module provides memory capabilities for AI agents including:
- Conversation memory for context retention across interactions
- Knowledge base for storing learned patterns and rules
"""

from .conversation import ConversationMemory
# from .knowledge import KnowledgeBase  # TODO: Implement

__all__ = [
    'ConversationMemory',
    # 'KnowledgeBase'  # TODO: Implement
]