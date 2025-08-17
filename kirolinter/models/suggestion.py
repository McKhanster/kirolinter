"""
Suggestion model for KiroLinter AI Agent System.

Represents fix suggestions with enhanced metadata for safety validation
and outcome tracking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class FixType(Enum):
    """Fix type categories."""
    REPLACE = "replace"
    DELETE = "delete"
    INSERT = "insert"
    FORMAT = "format"
    REFACTOR = "refactor"


@dataclass
class Suggestion:
    """
    Represents a code fix suggestion with safety and tracking metadata.
    
    Attributes:
        issue_id: ID of the issue this suggestion fixes
        file_path: Path to the file to be modified
        line_number: Line number where fix should be applied
        fix_type: Type of fix (replace, delete, insert, format)
        suggested_code: The suggested code change
        confidence: Confidence score (0.0-1.0)
        diff_patch: Optional diff patch for the change
        metadata: Additional metadata for the suggestion
    """
    issue_id: str
    file_path: str
    line_number: int
    fix_type: str
    suggested_code: str
    confidence: float
    diff_patch: Optional[str] = None
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate suggestion data after initialization."""
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        # Validate fix type
        valid_fix_types = ['replace', 'delete', 'insert', 'format']
        if self.fix_type not in valid_fix_types:
            self.fix_type = 'replace'  # Default to replace
    
    @property
    def issue(self):
        """Alias for issue_id for backward compatibility."""
        return self.issue_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suggestion to dictionary representation."""
        return {
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "fix_type": self.fix_type,
            "suggested_code": self.suggested_code,
            "confidence": self.confidence,
            "diff_patch": self.diff_patch,
            "explanation": self.explanation,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Suggestion':
        """Create Suggestion from dictionary representation."""
        return cls(
            issue_id=data["issue_id"],
            file_path=data["file_path"],
            line_number=data["line_number"],
            fix_type=data["fix_type"],
            suggested_code=data["suggested_code"],
            confidence=data["confidence"],
            diff_patch=data.get("diff_patch"),
            explanation=data.get("explanation", ""),
            metadata=data.get("metadata", {})
        )
    
    def is_safe_for_auto_apply(self) -> bool:
        """
        Check if suggestion is safe for automatic application.
        
        Returns:
            True if suggestion meets safety criteria
        """
        # High confidence required
        if self.confidence < 0.9:
            return False
        
        # Safe fix types only
        safe_types = ['replace', 'delete', 'format']
        if self.fix_type not in safe_types:
            return False
        
        # Reasonable code size
        if len(self.suggested_code) > 500:
            return False
        
        return True
    
    def __str__(self) -> str:
        """String representation of the suggestion."""
        return f"{self.fix_type} fix for {self.issue_id} at {self.file_path}:{self.line_number}"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"Suggestion(issue_id='{self.issue_id}', fix_type='{self.fix_type}', "
                f"file='{self.file_path}:{self.line_number}', confidence={self.confidence:.2f})")