"""
HTML web reporter for interactive KiroLinter analysis results.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from kirolinter.core.scanner import ScanResult
from kirolinter.models.issue import Issue, Severity, IssueType


class WebReporter:
    """Generate interactive HTML reports with syntax highlighting and filtering."""
    
    def __init__(self, include_source_code: bool = True, theme: str = 'light'):
        """
        Initialize web reporter.
        
        Args:
            include_source_code: Whether to include source code snippets
            theme: UI theme ('light' or 'dark')
        """
        self.include_source_code = include_source_code
        self.theme = theme
    
    def generate_report(self, target: str, scan_results: List[ScanResult], 
                       total_files: int, analysis_time: float, 
                       errors: List[str] = None) -> str:
        """
        Generate an interactive HTML report.
        
        Args:
            target: The analyzed target (repository URL or local path)
            scan_results: List of scan results from individual files
            total_files: Total number of files analyzed
            analysis_time: Time taken for analysis in seconds
            errors: List of errors encountered during analysis
        
        Returns:
            HTML string containing the interactive report
        """
        # Calculate summary statistics
        total_issues = sum(len(result.issues) for result in scan_results)
        issues_by_severity = self._calculate_severity_counts(scan_results)
        issues_by_type = self._calculate_type_counts(scan_results)
        
        # Generate HTML components
        html_head = self._generate_html_head()
        html_header = self._generate_header(target, total_files, total_issues, analysis_time)
        html_summary = self._generate_summary_section(issues_by_severity, issues_by_type)
        html_filters = self._generate_filter_controls()
        html_export = self._generate_export_controls()
        html_files = self._generate_files_section(scan_results)
        html_scripts = self._generate_javascript()
        
        # Combine into complete HTML document
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
{html_head}
<body class="{self.theme}-theme">
    <div class="container">
        {html_header}
        {html_summary}
        {html_filters}
        {html_export}
        {html_files}
    </div>
    {html_scripts}
</body>
</html>
"""
        
        return html_content
    
    def _generate_html_head(self) -> str:
        """Generate HTML head section with styles."""
        return f"""
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KiroLinter Analysis Report</title>
    <style>
        /* Base Styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Header Styles */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .header .stats {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            background: rgba(255, 255, 255, 0.2);
            padding: 10px 20px;
            border-radius: 5px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            display: block;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        /* Summary Section */
        .summary {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .summary-card h3 {{
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        
        .severity-item, .type-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .severity-item:last-child, .type-item:last-child {{
            border-bottom: none;
        }}
        
        .severity-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
        }}
        
        .severity-critical {{ background-color: #dc3545; }}
        .severity-high {{ background-color: #fd7e14; }}
        .severity-medium {{ background-color: #ffc107; color: #333; }}
        .severity-low {{ background-color: #28a745; }}
        
        .type-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
        }}
        
        .type-security {{ background-color: #dc3545; }}
        .type-performance {{ background-color: #17a2b8; }}
        .type-code_smell {{ background-color: #6c757d; }}
        
        /* Filter Controls */
        .filters {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .filter-group {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .filter-group label {{
            font-weight: bold;
            margin-right: 5px;
        }}
        
        select, input {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 200px;
        }}
        
        /* File Section */
        .file-card {{
            background: white;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .file-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .file-header:hover {{
            background: #e9ecef;
        }}
        
        .file-path {{
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #495057;
        }}
        
        .issue-count {{
            background: #6c757d;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        
        .file-content {{
            display: none;
            padding: 20px;
        }}
        
        .file-content.expanded {{
            display: block;
        }}
        
        .issue-item {{
            border-left: 4px solid #ddd;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }}
        
        .issue-item.severity-critical {{
            border-left-color: #dc3545;
        }}
        
        .issue-item.severity-high {{
            border-left-color: #fd7e14;
        }}
        
        .issue-item.severity-medium {{
            border-left-color: #ffc107;
        }}
        
        .issue-item.severity-low {{
            border-left-color: #28a745;
        }}
        
        .issue-header {{
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .issue-message {{
            font-weight: bold;
            color: #333;
            flex: 1;
        }}
        
        .issue-location {{
            font-family: 'Courier New', monospace;
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        .issue-details {{
            margin-top: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        
        .suggestion-box {{
            background: #e8f5e8;
            border: 1px solid #c3e6c3;
            border-radius: 5px;
            padding: 15px;
            margin-top: 10px;
        }}
        
        .suggestion-header {{
            font-weight: bold;
            color: #155724;
            margin-bottom: 8px;
        }}
        
        .suggestion-code {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 3px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            margin: 8px 0;
            overflow-x: auto;
        }}
        
        .diff-patch {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 3px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.8em;
            margin: 8px 0;
            overflow-x: auto;
            white-space: pre;
        }}
        
        .diff-added {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .diff-removed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        /* Dark Theme */
        .dark-theme {{
            background-color: #1a1a1a;
            color: #e0e0e0;
        }}
        
        .dark-theme .file-card,
        .dark-theme .summary-card,
        .dark-theme .filters {{
            background: #2d2d2d;
            color: #e0e0e0;
        }}
        
        .dark-theme .file-header {{
            background: #3d3d3d;
        }}
        
        .dark-theme .issue-item {{
            background: #3d3d3d;
        }}
        
        /* Export Controls */
        .export-controls {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .export-group {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .export-group h3 {{
            margin: 0;
            margin-right: 20px;
            color: #333;
        }}
        
        .export-btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .export-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }}
        
        .export-btn:active {{
            transform: translateY(0);
        }}
        
        /* Clickable Diffs */
        .diff-clickable {{
            cursor: pointer;
            border: 1px dashed #ccc;
            padding: 5px;
            margin: 5px 0;
            border-radius: 3px;
            transition: background-color 0.2s ease;
        }}
        
        .diff-clickable:hover {{
            background-color: #f0f8ff;
            border-color: #007acc;
        }}
        
        .diff-expanded {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr;
            }}
            
            .header .stats {{
                justify-content: center;
            }}
            
            .filter-group {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .export-group {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .export-btn {{
                margin-bottom: 10px;
            }}
        }}
        
        /* Animations */
        .file-content {{
            transition: all 0.3s ease;
        }}
        
        .issue-item {{
            transition: transform 0.2s ease;
        }}
        
        .issue-item:hover {{
            transform: translateX(5px);
        }}
    </style>
</head>
"""
    
    def _generate_header(self, target: str, total_files: int, total_issues: int, analysis_time: float) -> str:
        """Generate the header section."""
        return f"""
<div class="header">
    <h1>🔍 KiroLinter Analysis Report</h1>
    <div class="subtitle">Analysis of: {target}</div>
    <div class="stats">
        <div class="stat-item">
            <span class="stat-value">{total_files}</span>
            <span class="stat-label">Files Analyzed</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{total_issues}</span>
            <span class="stat-label">Issues Found</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{analysis_time:.2f}s</span>
            <span class="stat-label">Analysis Time</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <span class="stat-label">Generated</span>
        </div>
    </div>
</div>
"""
    
    def _generate_summary_section(self, issues_by_severity: Dict[str, int], issues_by_type: Dict[str, int]) -> str:
        """Generate the summary section with charts."""
        severity_items = ""
        for severity, count in issues_by_severity.items():
            if count > 0:
                severity_items += f"""
                <div class="severity-item">
                    <span>
                        <span class="severity-badge severity-{severity}">{severity.upper()}</span>
                    </span>
                    <span class="count">{count}</span>
                </div>
                """
        
        type_items = ""
        for issue_type, count in issues_by_type.items():
            if count > 0:
                display_type = issue_type.replace('_', ' ').title()
                type_items += f"""
                <div class="type-item">
                    <span>
                        <span class="type-badge type-{issue_type}">{display_type}</span>
                    </span>
                    <span class="count">{count}</span>
                </div>
                """
        
        return f"""
<div class="summary">
    <div class="summary-card">
        <h3>Issues by Severity</h3>
        {severity_items}
    </div>
    <div class="summary-card">
        <h3>Issues by Type</h3>
        {type_items}
    </div>
</div>
"""
    
    def _generate_filter_controls(self) -> str:
        """Generate filter controls."""
        return """
<div class="filters">
    <div class="filter-group">
        <label for="severity-filter">Severity:</label>
        <select id="severity-filter">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
        </select>
        
        <label for="type-filter">Type:</label>
        <select id="type-filter">
            <option value="">All Types</option>
            <option value="security">Security</option>
            <option value="performance">Performance</option>
            <option value="code_smell">Code Smell</option>
        </select>
        
        <label for="search-filter">Search:</label>
        <input type="text" id="search-filter" class="search-box" placeholder="Search issues...">
        
        <button onclick="clearFilters()">Clear Filters</button>
    </div>
</div>
"""
    
    def _generate_export_controls(self) -> str:
        """Generate export controls."""
        return """
<div class="export-controls">
    <div class="export-group">
        <h3>📤 Export Options</h3>
        <button onclick="exportToCSV()" class="export-btn">
            📊 Export to CSV
        </button>
        <button onclick="exportToPDF()" class="export-btn">
            📄 Export to PDF
        </button>
        <button onclick="exportToJSON()" class="export-btn">
            📋 Export to JSON
        </button>
        <button onclick="copyToClipboard()" class="export-btn">
            📋 Copy Summary
        </button>
    </div>
</div>
"""
    
    def _generate_files_section(self, scan_results: List[ScanResult]) -> str:
        """Generate the files section with issues."""
        files_html = ""
        
        for scan_result in scan_results:
            if not scan_result.issues:
                continue
            
            issues_html = ""
            for issue in scan_result.issues:
                suggestion_html = ""
                
                # Add suggestion if available
                if hasattr(issue, 'suggestion') and issue.suggestion:
                    suggestion = issue.suggestion
                    suggestion_html = f"""
                    <div class="suggestion-box">
                        <div class="suggestion-header">
                            💡 Suggested Fix (Confidence: {suggestion.confidence:.0%})
                        </div>
                        <div>{suggestion.explanation}</div>
                        {f'<div class="suggestion-code">{suggestion.suggested_code}</div>' if suggestion.suggested_code else ''}
                        {f'<div class="diff-patch">{suggestion.diff_patch}</div>' if hasattr(suggestion, 'diff_patch') and suggestion.diff_patch else ''}
                    </div>
                    """
                
                # Add CVE information if available
                cve_html = ""
                if hasattr(issue, 'cve_info') and issue.cve_info:
                    cve_info = issue.cve_info
                    cve_html = f"""
                    <div class="issue-details">
                        <strong>CVE:</strong> {cve_info['cve_id']} (Score: {cve_info['score']}/10)<br>
                        <strong>Description:</strong> {cve_info['description']}
                    </div>
                    """
                
                issues_html += f"""
                <div class="issue-item severity-{issue.severity.value} type-{issue.type.value}" 
                     data-severity="{issue.severity.value}" 
                     data-type="{issue.type.value}"
                     data-message="{issue.message.lower()}">
                    <div class="issue-header">
                        <div class="issue-message">{issue.message}</div>
                        <div class="issue-location">Line {issue.line_number}</div>
                    </div>
                    <div class="issue-details">
                        <strong>Rule:</strong> {issue.rule_id} | 
                        <strong>Type:</strong> {issue.type.value.replace('_', ' ').title()} | 
                        <strong>Severity:</strong> {issue.severity.value.upper()}
                    </div>
                    {cve_html}
                    {suggestion_html}
                </div>
                """
            
            files_html += f"""
            <div class="file-card">
                <div class="file-header" onclick="toggleFile(this)">
                    <div class="file-path">{scan_result.file_path}</div>
                    <div class="issue-count">{len(scan_result.issues)} issues</div>
                </div>
                <div class="file-content">
                    {issues_html}
                </div>
            </div>
            """
        
        return f'<div class="files-section">{files_html}</div>'
    
    def _generate_javascript(self) -> str:
        """Generate JavaScript for interactivity."""
        return """
<script>
    // Toggle file content visibility
    function toggleFile(header) {
        const content = header.nextElementSibling;
        content.classList.toggle('expanded');
    }
    
    // Filter functionality
    function applyFilters() {
        const severityFilter = document.getElementById('severity-filter').value;
        const typeFilter = document.getElementById('type-filter').value;
        const searchFilter = document.getElementById('search-filter').value.toLowerCase();
        
        const issues = document.querySelectorAll('.issue-item');
        
        issues.forEach(issue => {
            let show = true;
            
            // Severity filter
            if (severityFilter && !issue.classList.contains('severity-' + severityFilter)) {
                show = false;
            }
            
            // Type filter
            if (typeFilter && !issue.classList.contains('type-' + typeFilter)) {
                show = false;
            }
            
            // Search filter
            if (searchFilter && !issue.dataset.message.includes(searchFilter)) {
                show = false;
            }
            
            issue.style.display = show ? 'block' : 'none';
        });
        
        // Update file visibility based on visible issues
        document.querySelectorAll('.file-card').forEach(fileCard => {
            const visibleIssues = fileCard.querySelectorAll('.issue-item[style="display: block"], .issue-item:not([style])');
            const hasVisibleIssues = Array.from(visibleIssues).some(issue => 
                issue.style.display !== 'none'
            );
            fileCard.style.display = hasVisibleIssues ? 'block' : 'none';
        });
    }
    
    // Clear all filters
    function clearFilters() {
        document.getElementById('severity-filter').value = '';
        document.getElementById('type-filter').value = '';
        document.getElementById('search-filter').value = '';
        applyFilters();
    }
    
    // Add event listeners
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('severity-filter').addEventListener('change', applyFilters);
        document.getElementById('type-filter').addEventListener('change', applyFilters);
        document.getElementById('search-filter').addEventListener('input', applyFilters);
        
        // Expand first file by default
        const firstFile = document.querySelector('.file-header');
        if (firstFile) {
            toggleFile(firstFile);
        }
        
        // Add click handlers for diffs
        document.querySelectorAll('.diff-clickable').forEach(diff => {
            diff.addEventListener('click', function() {
                this.classList.toggle('diff-expanded');
            });
        });
    });
    
    // Export functionality
    function exportToCSV() {
        const issues = collectVisibleIssues();
        const csvContent = generateCSV(issues);
        downloadFile(csvContent, 'kirolinter-analysis.csv', 'text/csv');
    }
    
    function exportToPDF() {
        // Use browser's print functionality for PDF export
        const printWindow = window.open('', '_blank');
        const printContent = generatePrintableHTML();
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.print();
    }
    
    function exportToJSON() {
        const issues = collectVisibleIssues();
        const jsonContent = JSON.stringify({
            timestamp: new Date().toISOString(),
            issues: issues
        }, null, 2);
        downloadFile(jsonContent, 'kirolinter-analysis.json', 'application/json');
    }
    
    function copyToClipboard() {
        const summary = generateSummaryText();
        navigator.clipboard.writeText(summary).then(() => {
            alert('Summary copied to clipboard!');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = summary;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            alert('Summary copied to clipboard!');
        });
    }
    
    function collectVisibleIssues() {
        const issues = [];
        document.querySelectorAll('.issue-item').forEach(item => {
            if (item.style.display !== 'none') {
                const fileCard = item.closest('.file-card');
                const filePath = fileCard.querySelector('.file-path').textContent;
                const message = item.querySelector('.issue-message').textContent;
                const location = item.querySelector('.issue-location').textContent;
                const severity = item.dataset.severity;
                const type = item.dataset.type;
                
                issues.push({
                    file: filePath,
                    location: location,
                    severity: severity,
                    type: type,
                    message: message
                });
            }
        });
        return issues;
    }
    
    function generateCSV(issues) {
        const headers = ['File', 'Location', 'Severity', 'Type', 'Message'];
        const csvRows = [headers.join(',')];
        
        issues.forEach(issue => {
            const row = [
                `"${issue.file}"`,
                `"${issue.location}"`,
                `"${issue.severity}"`,
                `"${issue.type}"`,
                `"${issue.message.replace(/"/g, '""')}"`
            ];
            csvRows.push(row.join(','));
        });
        
        return csvRows.join('\\n');
    }
    
    function generateSummaryText() {
        const issues = collectVisibleIssues();
        const severityCounts = {};
        const typeCounts = {};
        
        issues.forEach(issue => {
            severityCounts[issue.severity] = (severityCounts[issue.severity] || 0) + 1;
            typeCounts[issue.type] = (typeCounts[issue.type] || 0) + 1;
        });
        
        let summary = 'KiroLinter Analysis Summary\\n';
        summary += '========================\\n\\n';
        summary += `Total Issues: ${issues.length}\\n\\n`;
        
        summary += 'By Severity:\\n';
        Object.entries(severityCounts).forEach(([severity, count]) => {
            summary += `  ${severity}: ${count}\\n`;
        });
        
        summary += '\\nBy Type:\\n';
        Object.entries(typeCounts).forEach(([type, count]) => {
            summary += `  ${type}: ${count}\\n`;
        });
        
        return summary;
    }
    
    function generatePrintableHTML() {
        const issues = collectVisibleIssues();
        let html = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>KiroLinter Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .issue { margin-bottom: 15px; padding: 10px; border-left: 4px solid #ccc; }
                .critical { border-left-color: #dc3545; }
                .high { border-left-color: #fd7e14; }
                .medium { border-left-color: #ffc107; }
                .low { border-left-color: #28a745; }
                .file-header { font-weight: bold; margin-top: 20px; }
            </style>
        </head>
        <body>
            <h1>KiroLinter Analysis Report</h1>
            <p>Generated: ${new Date().toLocaleString()}</p>
            <p>Total Issues: ${issues.length}</p>
        `;
        
        const byFile = {};
        issues.forEach(issue => {
            if (!byFile[issue.file]) byFile[issue.file] = [];
            byFile[issue.file].push(issue);
        });
        
        Object.entries(byFile).forEach(([file, fileIssues]) => {
            html += `<div class="file-header">${file}</div>`;
            fileIssues.forEach(issue => {
                html += `
                <div class="issue ${issue.severity}">
                    <strong>${issue.location}</strong> - ${issue.severity.toUpperCase()}<br>
                    ${issue.message}
                </div>`;
            });
        });
        
        html += '</body></html>';
        return html;
    }
    
    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
</script>
"""
    
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