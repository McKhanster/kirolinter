"""
Data models for representing code analysis issues.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IssueType(Enum):
    """Types of issues that can be detected."""
    CODE_SMELL = "code_smell"
    SECURITY = "security"
    PERFORMANCE = "performance"


class Severity(Enum):
    """Severity levels for issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __lt__(self, other):
        """Enable comparison of severity levels."""
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) < order.index(other)


@dataclass
class Issue:
    """Represents a code quality issue found during analysis."""
    
    id: str
    type: IssueType
    severity: Severity
    file_path: str
    line_number: int
    column: int
    message: str
    rule_id: str
    cve_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert issue to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'severity': self.severity.value,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column': self.column,
            'message': self.message,
            'rule_id': self.rule_id,
            'cve_id': self.cve_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Issue':
        """Create issue from dictionary."""
        return cls(
            id=data['id'],
            type=IssueType(data['type']),
            severity=Severity(data['severity']),
            file_path=data['file_path'],
            line_number=data['line_number'],
            column=data['column'],
            message=data['message'],
            rule_id=data['rule_id'],
            cve_id=data.get('cve_id')
        )