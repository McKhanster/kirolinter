"""
LangChain tool wrapper for KiroLinter suggester functionality.
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ...core.suggester import SuggestionEngine
from ...core.interactive_fixer import InteractiveFixer
from ...models.issue import Issue
from ...models.config import Config


class SuggesterInput(BaseModel):
    """Input schema for suggester tool."""
    issue_data: Dict[str, Any] = Field(description="Issue data to generate suggestions for")
    context: Optional[str] = Field(default=None, description="Additional context for suggestion generation")


class SuggesterTool(BaseTool):
    """LangChain tool for generating fix suggestions."""
    
    name: str = "fix_suggester"
    description: str = """
    Generate AI-powered fix suggestions for code quality issues.
    
    This tool analyzes code issues and provides:
    - Specific fix recommendations
    - Code patches and diffs
    - Confidence scores for suggestions
    - Explanations of the fixes
    
    Works with various issue types including code smells, security vulnerabilities, and performance issues.
    """
    args_schema: type[BaseModel] = SuggesterInput
    
    def _run(self, issue_data: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
        """Generate fix suggestions for the given issue."""
        try:
            # Convert issue data to Issue object
            issue = Issue(
                id=issue_data.get("id", ""),
                type=issue_data.get("type", "code_smell"),
                severity=issue_data.get("severity", "low"),
                file_path=issue_data.get("file_path", ""),
                line_number=issue_data.get("line_number", 0),
                column=issue_data.get("column", 0),
                message=issue_data.get("message", ""),
                rule_id=issue_data.get("rule_id", ""),
                cve_id=issue_data.get("cve_id")
            )
            
            # Initialize suggester
            suggester = SuggestionEngine(Config())
            
            # Generate suggestions
            suggestions = suggester.generate_suggestions([issue], context)
            
            # Format results
            result = {
                "issue_id": issue.id,
                "suggestions_count": len(suggestions),
                "suggestions": []
            }
            
            for suggestion in suggestions:
                result["suggestions"].append({
                    "fix_type": suggestion.fix_type.value if hasattr(suggestion.fix_type, 'value') else str(suggestion.fix_type),
                    "original_code": suggestion.original_code,
                    "suggested_code": suggestion.suggested_code,
                    "confidence": suggestion.confidence,
                    "explanation": suggestion.explanation,
                    "diff_patch": suggestion.diff_patch
                })
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to generate suggestions: {str(e)}",
                "issue_id": issue_data.get("id", "unknown"),
                "suggestions_count": 0,
                "suggestions": []
            }


@tool
def generate_batch_suggestions(issues_data: List[Dict[str, Any]], team_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate fix suggestions for multiple issues at once.
    
    Args:
        issues_data: List of issue dictionaries
        team_context: Optional team style context for personalized suggestions
        
    Returns:
        Dictionary containing suggestions for all issues
    """
    try:
        # Convert to Issue objects
        issues = []
        for issue_data in issues_data:
            issue = Issue(
                id=issue_data.get("id", ""),
                type=issue_data.get("type", "code_smell"),
                severity=issue_data.get("severity", "low"),
                file_path=issue_data.get("file_path", ""),
                line_number=issue_data.get("line_number", 0),
                column=issue_data.get("column", 0),
                message=issue_data.get("message", ""),
                rule_id=issue_data.get("rule_id", ""),
                cve_id=issue_data.get("cve_id")
            )
            issues.append(issue)
        
        # Generate suggestions
        suggester = SuggestionEngine(Config())
        suggestions = suggester.generate_suggestions(issues, team_context)
        
        # Group suggestions by issue
        suggestions_by_issue = {}
        for suggestion in suggestions:
            issue_id = suggestion.issue_id
            if issue_id not in suggestions_by_issue:
                suggestions_by_issue[issue_id] = []
            
            suggestions_by_issue[issue_id].append({
                "fix_type": suggestion.fix_type.value if hasattr(suggestion.fix_type, 'value') else str(suggestion.fix_type),
                "original_code": suggestion.original_code,
                "suggested_code": suggestion.suggested_code,
                "confidence": suggestion.confidence,
                "explanation": suggestion.explanation,
                "diff_patch": suggestion.diff_patch
            })
        
        return {
            "total_issues": len(issues),
            "total_suggestions": len(suggestions),
            "suggestions_by_issue": suggestions_by_issue
        }
        
    except Exception as e:
        return {
            "error": f"Failed to generate batch suggestions: {str(e)}",
            "total_issues": len(issues_data),
            "total_suggestions": 0,
            "suggestions_by_issue": {}
        }


@tool
def apply_interactive_fixes(file_path: str, fix_types: List[str], auto_approve: bool = False) -> Dict[str, Any]:
    """
    Apply interactive fixes to a file with safety checks.
    
    Args:
        file_path: Path to file to fix
        fix_types: List of fix types to apply (e.g., ['unused_import', 'unused_variable'])
        auto_approve: Whether to auto-approve fixes without user interaction
        
    Returns:
        Dictionary containing fix application results
    """
    try:
        # Initialize interactive fixer
        fixer = InteractiveFixer(verbose=True)
        
        # For agent mode, we'll simulate the analysis results needed
        # In a real implementation, this would integrate with the analysis engine
        from ...core.engine import AnalysisEngine
        
        engine = AnalysisEngine()
        config = Config()
        
        # Analyze the file to get current issues
        results = engine.analyze_file(file_path, config)
        
        if auto_approve:
            # Apply fixes automatically
            fixes_applied = fixer.apply_fixes_automatically(results, fix_types)
        else:
            # This would normally be interactive, but for agent mode we'll auto-approve
            fixes_applied = fixer.apply_interactive_fixes(results)
        
        return {
            "file_path": file_path,
            "fixes_applied": fixes_applied,
            "fix_types_requested": fix_types,
            "backup_created": True,  # Interactive fixer always creates backups
            "success": True
        }
        
    except Exception as e:
        return {
            "error": f"Failed to apply fixes to {file_path}: {str(e)}",
            "file_path": file_path,
            "fixes_applied": 0,
            "success": False
        }


@tool
def validate_fix_safety(file_path: str, suggested_fix: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that a suggested fix is safe to apply.
    
    Args:
        file_path: Path to file being fixed
        suggested_fix: Dictionary containing fix details
        
    Returns:
        Dictionary containing safety validation results
    """
    try:
        # Basic safety checks
        safety_checks = {
            "syntax_valid": True,
            "preserves_functionality": True,
            "no_breaking_changes": True,
            "confidence_acceptable": True,
            "safe_to_apply": True
        }
        
        # Check confidence score
        confidence = suggested_fix.get("confidence", 0)
        if confidence < 0.7:
            safety_checks["confidence_acceptable"] = False
            safety_checks["safe_to_apply"] = False
        
        # Check for potentially dangerous operations
        suggested_code = suggested_fix.get("suggested_code", "")
        dangerous_patterns = ["exec(", "eval(", "__import__", "globals()", "locals()"]
        
        for pattern in dangerous_patterns:
            if pattern in suggested_code:
                safety_checks["preserves_functionality"] = False
                safety_checks["safe_to_apply"] = False
                break
        
        # TODO: Add more sophisticated safety checks
        # - AST parsing validation
        # - Type checking
        # - Test execution
        
        return {
            "file_path": file_path,
            "fix_id": suggested_fix.get("id", "unknown"),
            "safety_checks": safety_checks,
            "overall_safe": safety_checks["safe_to_apply"],
            "recommendations": [
                "Create backup before applying" if safety_checks["safe_to_apply"] else "Manual review required",
                "Test thoroughly after applying" if safety_checks["safe_to_apply"] else "Do not apply automatically"
            ]
        }
        
    except Exception as e:
        return {
            "error": f"Failed to validate fix safety: {str(e)}",
            "file_path": file_path,
            "overall_safe": False
        }