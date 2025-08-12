"""
Reviewer Agent for KiroLinter AI Agent System.

The Reviewer Agent performs autonomous code analysis with AI-powered prioritization
and intelligent issue detection.
"""

from typing import Dict, List, Any, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .tools.scanner_tool import ScannerTool, scan_repository, get_file_metrics
from .llm_provider import create_llm_provider
from ..prompts.reviewer_prompts import ReviewerPrompts


class ReviewerAgent:
    """
    AI agent specialized in code review and analysis.
    
    The Reviewer Agent:
    - Performs autonomous code analysis using scanner tools
    - Prioritizes issues based on impact and severity
    - Provides context-aware problem identification
    - Generates comprehensive review reports
    """
    
    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None, verbose: bool = False):
        """
        Initialize the Reviewer Agent.
        
        Args:
            model: LLM model name (e.g., "grok-beta", "ollama/llama2")
            provider: LLM provider (e.g., "xai", "ollama", "openai")
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        
        # Initialize LLM with LiteLLM
        try:
            self.llm = create_llm_provider(
                model=model,
                provider=provider,
                temperature=0.1,
                max_tokens=4000
            )
            
            if verbose:
                print(f"🔍 Reviewer: Using LLM model '{self.llm.model}'")
        except Exception as e:
            if verbose:
                print(f"⚠️ Reviewer: Failed to initialize LLM: {e}")
            raise
        
        # Initialize tools
        self.tools = [
            ScannerTool(),
            scan_repository,
            get_file_metrics
        ]
        
        # Create simple prompt template for direct LLM usage
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", ReviewerPrompts.SYSTEM_PROMPT),
            ("human", "{input}"),
        ])
        
        # For now, use direct LLM calls instead of function calling
        # This ensures compatibility with all LLM providers
        self.agent_executor = None  # Will use direct LLM calls
    
    def analyze_repository(self, repo_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive repository analysis.
        
        Args:
            repo_path: Path to repository to analyze
            config_path: Optional configuration file path
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            if self.verbose:
                print(f"🔍 Reviewer Agent: Analyzing repository {repo_path}")
            
            # Use the scan_repository tool directly for efficiency
            analysis_result = scan_repository.invoke({
                "repo_path": repo_path,
                "config_path": config_path
            })
            
            if "error" in analysis_result:
                return analysis_result
            
            # Enhance with AI analysis
            ai_analysis = self._ai_analyze_results(analysis_result)
            analysis_result["ai_insights"] = ai_analysis
            
            return analysis_result
            
        except Exception as e:
            return {
                "error": f"Repository analysis failed: {str(e)}",
                "repo_path": repo_path
            }
    
    def analyze_file(self, file_path: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform detailed analysis of a single file.
        
        Args:
            file_path: Path to file to analyze
            context: Optional context for analysis
            
        Returns:
            Dictionary containing file analysis results
        """
        try:
            if self.verbose:
                print(f"📄 Reviewer Agent: Analyzing file {file_path}")
            
            # Use scanner tool
            scanner_tool = ScannerTool()
            analysis_result = scanner_tool._run(file_path)
            
            if "error" in analysis_result:
                return analysis_result
            
            # Get file metrics
            metrics_result = get_file_metrics.invoke({"file_path": file_path})
            analysis_result["metrics"] = metrics_result
            
            # AI-powered analysis enhancement
            if analysis_result["total_issues"] > 0:
                ai_analysis = self._ai_analyze_file_issues(analysis_result, context)
                analysis_result["ai_insights"] = ai_analysis
            
            return analysis_result
            
        except Exception as e:
            return {
                "error": f"File analysis failed: {str(e)}",
                "file_path": file_path
            }
    
    def prioritize_issues(self, files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use AI to prioritize issues based on impact and severity.
        
        Args:
            files_data: List of file analysis results
            
        Returns:
            Dictionary containing prioritized issues
        """
        try:
            if self.verbose:
                print("🎯 Reviewer Agent: Prioritizing issues...")
            
            # Collect all issues
            all_issues = []
            for file_data in files_data:
                for issue in file_data.get("issues", []):
                    issue["file_path"] = file_data["file_path"]
                    all_issues.append(issue)
            
            if not all_issues:
                return {
                    "total_issues": 0,
                    "prioritized_issues": [],
                    "priority_categories": {}
                }
            
            # Use AI agent to prioritize
            prioritization_input = f"""
            Analyze and prioritize these {len(all_issues)} code issues:
            
            Issues: {all_issues[:50]}  # Limit for token efficiency
            
            Prioritize based on:
            1. Security impact (highest priority)
            2. Performance impact
            3. Maintainability concerns
            4. Code quality standards
            
            Return prioritized list with reasoning.
            """
            
            # Use direct LLM call
            formatted_prompt = self.prompt.format_messages(input=prioritization_input)
            result = self.llm.invoke(formatted_prompt)
            
            return {
                "total_issues": len(all_issues),
                "ai_prioritization": result.content if hasattr(result, 'content') else str(result),
                "issues_by_severity": self._categorize_by_severity(all_issues),
                "issues_by_type": self._categorize_by_type(all_issues)
            }
            
        except Exception as e:
            return {
                "error": f"Issue prioritization failed: {str(e)}",
                "total_issues": len(files_data) if files_data else 0
            }
    
    def generate_review_report(self, analysis_result: Dict[str, Any], 
                             prioritization_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive review report.
        
        Args:
            analysis_result: Repository analysis results
            prioritization_result: Optional issue prioritization results
            
        Returns:
            Dictionary containing review report
        """
        try:
            if self.verbose:
                print("📝 Reviewer Agent: Generating review report...")
            
            # Prepare report data
            report_data = {
                "repository_path": analysis_result.get("repository_path", ""),
                "total_files": analysis_result.get("total_files_analyzed", 0),
                "total_issues": analysis_result.get("total_issues_found", 0),
                "analysis_time": analysis_result.get("analysis_time_seconds", 0),
                "has_critical_issues": analysis_result.get("has_critical_issues", False)
            }
            
            # Generate AI-powered review summary
            review_input = f"""
            Generate a comprehensive code review report for this analysis:
            
            Repository: {report_data['repository_path']}
            Files analyzed: {report_data['total_files']}
            Issues found: {report_data['total_issues']}
            Critical issues: {report_data['has_critical_issues']}
            
            Analysis results: {analysis_result.get('issues_by_severity', {})}
            
            Provide:
            1. Executive summary
            2. Key findings and recommendations
            3. Priority actions
            4. Code quality assessment
            """
            
            # Use direct LLM call instead of agent executor for better compatibility
            formatted_prompt = self.prompt.format_messages(input=review_input)
            ai_report = self.llm.invoke(formatted_prompt)
            
            return {
                "report_type": "comprehensive_review",
                "metadata": report_data,
                "ai_summary": ai_report.content if hasattr(ai_report, 'content') else str(ai_report),
                "prioritization": prioritization_result,
                "recommendations": self._generate_recommendations(analysis_result),
                "generated_at": self._get_timestamp()
            }
            
        except Exception as e:
            return {
                "error": f"Report generation failed: {str(e)}",
                "report_type": "error_report"
            }
    
    def _ai_analyze_results(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to provide insights on analysis results."""
        try:
            insights_input = f"""
            Analyze these code quality results and provide insights:
            
            Total files: {analysis_result.get('total_files_analyzed', 0)}
            Total issues: {analysis_result.get('total_issues_found', 0)}
            Issues by severity: {analysis_result.get('issues_by_severity', {})}
            Issues by type: {analysis_result.get('issues_by_type', {})}
            
            Provide insights on:
            1. Overall code quality assessment
            2. Most concerning patterns
            3. Recommended focus areas
            """
            
            # Use direct LLM call
            formatted_prompt = self.prompt.format_messages(input=insights_input)
            result = self.llm.invoke(formatted_prompt)
            
            return {
                "ai_assessment": result.content if hasattr(result, 'content') else str(result),
                "confidence": "high"
            }
            
        except Exception as e:
            return {
                "error": f"AI analysis failed: {str(e)}",
                "confidence": "low"
            }
    
    def _ai_analyze_file_issues(self, file_result: Dict[str, Any], context: Optional[str]) -> Dict[str, Any]:
        """Use AI to analyze issues in a specific file."""
        try:
            context_str = f"Context: {context}" if context else ""
            
            analysis_input = f"""
            Analyze issues in this file:
            
            File: {file_result.get('file_path', '')}
            Issues found: {file_result.get('total_issues', 0)}
            Issues: {file_result.get('issues', [])[:10]}  # Limit for efficiency
            {context_str}
            
            Provide file-specific insights and recommendations.
            """
            
            # Use direct LLM call
            formatted_prompt = self.prompt.format_messages(input=analysis_input)
            result = self.llm.invoke(formatted_prompt)
            
            return {
                "file_assessment": result.content if hasattr(result, 'content') else str(result),
                "focus_areas": self._extract_focus_areas(file_result)
            }
            
        except Exception as e:
            return {
                "error": f"File AI analysis failed: {str(e)}"
            }
    
    def _categorize_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize issues by severity level."""
        categories = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for issue in issues:
            severity = issue.get("severity", "low").lower()
            if severity in categories:
                categories[severity] += 1
        
        return categories
    
    def _categorize_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize issues by type."""
        categories = {}
        
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            categories[issue_type] = categories.get(issue_type, 0) + 1
        
        return categories
    
    def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Check for critical issues
        if analysis_result.get("has_critical_issues", False):
            recommendations.append("🚨 Address critical security issues immediately")
        
        # Check issue distribution
        issues_by_severity = analysis_result.get("issues_by_severity", {})
        if issues_by_severity.get("high", 0) > 10:
            recommendations.append("🔥 High number of high-severity issues - prioritize fixes")
        
        if issues_by_severity.get("low", 0) > 50:
            recommendations.append("🧹 Consider batch fixing low-severity issues for code cleanliness")
        
        # Check for patterns
        issues_by_type = analysis_result.get("issues_by_type", {})
        if issues_by_type.get("code_smell", 0) > issues_by_type.get("security", 0) * 3:
            recommendations.append("📝 Focus on code quality improvements")
        
        return recommendations
    
    def _extract_focus_areas(self, file_result: Dict[str, Any]) -> List[str]:
        """Extract focus areas for a specific file."""
        focus_areas = []
        
        issues = file_result.get("issues", [])
        if not issues:
            return ["✅ No issues found"]
        
        # Analyze issue patterns
        rule_counts = {}
        for issue in issues:
            rule_id = issue.get("rule_id", "unknown")
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        
        # Identify top issues
        top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for rule_id, count in top_rules:
            focus_areas.append(f"🎯 {rule_id}: {count} occurrences")
        
        return focus_areas
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for reports."""
        from datetime import datetime
        return datetime.now().isoformat()