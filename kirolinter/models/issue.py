"""
Issue model for KiroLinter AI Agent System.

Represents code issues found during analysis with enhanced metadata
for pattern-aware processing and risk assessment.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class IssueSeverity(Enum):
    """Issue severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(Enum):
    """Issue type categories."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_QUALITY = "code_quality"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    BUG = "bug"
    COMPLEXITY = "complexity"


# Aliases for backward compatibility
Severity = IssueSeverity


@dataclass
class Issue:
    """
    Represents a code issue with enhanced metadata for Phase 4 processing.
    
    Attributes:
        file_path: Path to the file containing the issue
        line_number: Line number where issue occurs
        rule_id: Linting rule that triggered the issue
        message: Human-readable issue description
        severity: Issue severity level
        issue_type: Type of issue (security, performance, etc.)
        context: Additional context from learned patterns
        priority_score: Calculated priority score (0.0-10.0)
        priority_rank: Rank in prioritized list
    """
    file_path: str
    line_number: int
    rule_id: str
    message: str
    severity: IssueSeverity
    issue_type: str = "code_quality"
    context: Dict[str, Any] = field(default_factory=dict)
    priority_score: float = 0.0
    priority_rank: int = 0
    
    def __post_init__(self):
        """Convert string severity to enum if needed."""
        if isinstance(self.severity, str):
            try:
                self.severity = IssueSeverity(self.severity.lower())
            except ValueError:
                self.severity = IssueSeverity.LOW
    
    @property
    def type(self) -> str:
        """Alias for issue_type for backward compatibility."""
        return self.issue_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary representation."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "issue_type": self.issue_type,
            "context": self.context,
            "priority_score": self.priority_score,
            "priority_rank": self.priority_rank
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Issue':
        """Create Issue from dictionary representation."""
        return cls(
            file_path=data["file_path"],
            line_number=data["line_number"],
            rule_id=data["rule_id"],
            message=data["message"],
            severity=data["severity"],
            issue_type=data.get("issue_type", "code_quality"),
            context=data.get("context", {}),
            priority_score=data.get("priority_score", 0.0),
            priority_rank=data.get("priority_rank", 0)
        )
    
    def __str__(self) -> str:
        """String representation of the issue."""
        return f"{self.rule_id} ({self.severity.value}) at {self.file_path}:{self.line_number}"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"Issue(rule_id='{self.rule_id}', severity='{self.severity.value}', "
                f"file='{self.file_path}:{self.line_number}', priority={self.priority_score:.2f})")