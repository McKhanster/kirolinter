"""
Data models for code fix suggestions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FixType(Enum):
    """Types of fixes that can be suggested."""
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"
    REFACTOR = "refactor"


@dataclass
class Suggestion:
    """Represents a suggested fix for a code issue."""
    
    issue_id: str
    fix_type: FixType
    original_code: str
    suggested_code: str
    confidence: float
    explanation: str
    diff_patch: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert suggestion to dictionary for JSON serialization."""
        return {
            'issue_id': self.issue_id,
            'fix_type': self.fix_type.value,
            'original_code': self.original_code,
            'suggested_code': self.suggested_code,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'diff_patch': self.diff_patch
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Suggestion':
        """Create suggestion from dictionary."""
        return cls(
            issue_id=data['issue_id'],
            fix_type=FixType(data['fix_type']),
            original_code=data['original_code'],
            suggested_code=data['suggested_code'],
            confidence=data['confidence'],
            explanation=data['explanation'],
            diff_patch=data.get('diff_patch')
        )