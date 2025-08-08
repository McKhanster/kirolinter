"""
JSON report generation for KiroLinter analysis results.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from kirolinter.core.scanner import ScanResult
from kirolinter.models.issue import Issue, Severity
from kirolinter.reporting.diff_generator import DiffGenerator


class JSONReporter:
    """Generate structured JSON reports from analysis results."""
    
    def __init__(self, include_diffs: bool = False):
        self.include_diffs = include_diffs
        self.diff_generator = DiffGenerator() if include_diffs else None
    
    def generate_report(self, target: str, scan_results: List[ScanResult], 
                       total_files: int, analysis_time: float, 
                       errors: List[str] = None) -> str:
        """
        Generate a structured JSON report from scan results.
        
        Args:
            target: The analyzed target (repository URL or local path)
            scan_results: List of scan results from individual files
            total_files: Total number of files analyzed
            analysis_time: Time taken for analysis in seconds
            errors: List of errors encountered during analysis
        
        Returns:
            JSON string containing the structured report
        """
        # Calculate summary statistics
        total_issues = sum(len(result.issues) for result in scan_results)
        issues_by_severity = self._calculate_severity_counts(scan_results)
        issues_by_type = self._calculate_type_counts(scan_results)
        
        # Build the main report structure
        report = {
            "kirolinter_version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "target": target,
            "summary": {
                "total_files_analyzed": total_files,
                "total_issues_found": total_issues,
                "analysis_time_seconds": round(analysis_time, 2),
                "issues_by_severity": issues_by_severity,
                "issues_by_type": issues_by_type,
                "has_critical_issues": any(
                    result.has_critical_issues() for result in scan_results
                )
            },
            "files": []
        }
        
        # Add file-level results
        for scan_result in scan_results:
            file_report = self._generate_file_report(scan_result)
            if file_report["issues"] or file_report["parse_errors"]:
                report["files"].append(file_report)
        
        # Add errors if any
        if errors:
            report["errors"] = errors
        
        # Add metadata
        report["metadata"] = {
            "rules_applied": self._get_applied_rules(scan_results),
            "file_extensions_analyzed": [".py"],
            "excluded_patterns": []  # Could be populated from config
        }
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def _generate_file_report(self, scan_result: ScanResult) -> Dict[str, Any]:
        """Generate report data for a single file."""
        file_report = {
            "file_path": scan_result.file_path,
            "issues": [],
            "metrics": scan_result.metrics,
            "parse_errors": scan_result.parse_errors
        }
        
        # Add issues with suggestions and optional diffs
        for issue in scan_result.issues:
            issue_data = issue.to_dict()
            
            # Add suggestion if available (from suggester)
            if hasattr(issue, 'suggestion') and issue.suggestion:
                suggestion = issue.suggestion
                issue_data["suggested_fix"] = {
                    "fix_type": suggestion.fix_type.value,
                    "suggested_code": suggestion.suggested_code,
                    "confidence": suggestion.confidence,
                    "explanation": suggestion.explanation
                }
                
                # Add diff patch if requested and available
                if self.include_diffs and self.diff_generator:
                    try:
                        diff_patch = self.diff_generator.generate_patch(issue)
                        if diff_patch:
                            issue_data["suggested_fix"]["diff_patch"] = diff_patch
                    except Exception:
                        # Don't fail the report if diff generation fails
                        pass
            elif self.include_diffs and self.diff_generator:
                # Fallback: generate diff without suggestion
                try:
                    diff_patch = self.diff_generator.generate_patch(issue)
                    if diff_patch:
                        issue_data["suggested_fix"] = {
                            "diff_patch": diff_patch,
                            "confidence": 0.7,  # Lower confidence for auto-generated
                            "description": self.diff_generator.generate_suggestion_text(issue)
                        }
                except Exception:
                    # Don't fail the report if diff generation fails
                    pass
            
            file_report["issues"].append(issue_data)
        
        return file_report
    
    def _calculate_severity_counts(self, scan_results: List[ScanResult]) -> Dict[str, int]:
        """Calculate count of issues by severity level."""
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for result in scan_results:
            for issue in result.issues:
                severity_counts[issue.severity.value] += 1
        
        return severity_counts
    
    def _calculate_type_counts(self, scan_results: List[ScanResult]) -> Dict[str, int]:
        """Calculate count of issues by type."""
        type_counts = {
            "code_smell": 0,
            "security": 0,
            "performance": 0
        }
        
        for result in scan_results:
            for issue in result.issues:
                type_counts[issue.type.value] += 1
        
        return type_counts
    
    def _get_applied_rules(self, scan_results: List[ScanResult]) -> List[str]:
        """Get list of rules that were applied during analysis."""
        applied_rules = set()
        
        for result in scan_results:
            for issue in result.issues:
                applied_rules.add(issue.rule_id)
        
        return sorted(list(applied_rules))
    
    def generate_issue_summary(self, scan_results: List[ScanResult]) -> Dict[str, Any]:
        """Generate a summary of issues for quick overview."""
        total_issues = sum(len(result.issues) for result in scan_results)
        
        if total_issues == 0:
            return {
                "status": "clean",
                "message": "No issues found",
                "total_issues": 0
            }
        
        severity_counts = self._calculate_severity_counts(scan_results)
        
        # Determine overall status
        if severity_counts["critical"] > 0:
            status = "critical"
            message = f"Found {severity_counts['critical']} critical issue(s)"
        elif severity_counts["high"] > 0:
            status = "high"
            message = f"Found {severity_counts['high']} high severity issue(s)"
        elif severity_counts["medium"] > 0:
            status = "medium"
            message = f"Found {severity_counts['medium']} medium severity issue(s)"
        else:
            status = "low"
            message = f"Found {severity_counts['low']} low severity issue(s)"
        
        return {
            "status": status,
            "message": message,
            "total_issues": total_issues,
            "severity_breakdown": severity_counts
        }


class CompactJSONReporter(JSONReporter):
    """Generate compact JSON reports without detailed metadata."""
    
    def generate_report(self, target: str, scan_results: List[ScanResult], 
                       total_files: int, analysis_time: float, 
                       errors: List[str] = None) -> str:
        """Generate a compact JSON report."""
        issues = []
        
        for scan_result in scan_results:
            for issue in scan_result.issues:
                issue_data = issue.to_dict()
                issues.append(issue_data)
        
        compact_report = {
            "target": target,
            "total_issues": len(issues),
            "analysis_time": round(analysis_time, 2),
            "issues": issues
        }
        
        if errors:
            compact_report["errors"] = errors
        
        return json.dumps(compact_report, separators=(',', ':'))  # Minimal whitespace