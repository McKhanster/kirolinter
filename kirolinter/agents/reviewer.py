"""
Reviewer Agent for KiroLinter AI Agent System - Phase 4 Enhanced.

The Reviewer Agent performs autonomous code analysis with pattern-aware intelligence,
risk assessment, and predictive issue detection using Redis-based PatternMemory.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .tools.scanner_tool import ScannerTool, scan_repository, get_file_metrics
from .llm_provider import create_llm_provider
from ..prompts.reviewer_prompts import ReviewerPrompts
from ..memory.pattern_memory import create_pattern_memory
from ..models.issue import Issue


class ReviewerAgent:
    """
    AI agent specialized in code review and analysis.
    
    The Reviewer Agent:
    - Performs autonomous code analysis using scanner tools
    - Prioritizes issues based on impact and severity
    - Provides context-aware problem identification
    - Generates comprehensive review reports
    """
    
    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None, 
                 memory=None, verbose: bool = False):
        """
        Initialize the Reviewer Agent with Phase 4 enhancements.
        
        Args:
            model: LLM model name (e.g., "grok-beta", "ollama/llama2")
            provider: LLM provider (e.g., "xai", "ollama", "openai")
            memory: PatternMemory instance (Redis-based)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        
        # Initialize Redis-based PatternMemory
        self.memory = memory or create_pattern_memory(redis_only=True)
        
        # Initialize LLM with LiteLLM
        try:
            self.llm = create_llm_provider(
                model=model,
                provider=provider,
                temperature=0.1,
                max_tokens=4000
            )
            
            if verbose:
                print(f"🔍 Reviewer: Using LLM model '{self.llm.model}' with Redis PatternMemory")
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
        
        # Create enhanced prompt template for pattern-aware analysis
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", ReviewerPrompts.SYSTEM_PROMPT + "\n\nYou have access to learned patterns and can perform risk assessment."),
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
        Use AI and learned patterns to prioritize issues based on impact and severity.
        
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
            
            # Get learned patterns for intelligent prioritization
            repo_path = getattr(self, 'current_repo_path', '.')
            prioritized_issues = self._prioritize_with_patterns(all_issues, repo_path)
            
            # Use AI agent to prioritize with pattern context
            pattern_context = self._get_pattern_context(repo_path)
            prioritization_input = f"""
            Analyze and prioritize these {len(all_issues)} code issues using learned patterns:
            
            Pattern Context: {pattern_context}
            Issues: {all_issues[:50]}  # Limit for token efficiency
            
            Prioritize based on:
            1. Security impact (highest priority)
            2. Performance impact
            3. Frequently occurring issues (based on learned patterns)
            4. Maintainability concerns
            5. Code quality standards
            
            Return prioritized list with reasoning.
            """
            
            # Use direct LLM call
            formatted_prompt = self.prompt.format_messages(input=prioritization_input)
            result = self.llm.invoke(formatted_prompt)
            
            return {
                "total_issues": len(all_issues),
                "prioritized_issues": prioritized_issues,
                "ai_prioritization": result.content if hasattr(result, 'content') else str(result),
                "issues_by_severity": self._categorize_by_severity(all_issues),
                "issues_by_type": self._categorize_by_type(all_issues),
                "pattern_context": pattern_context
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
    
    # Phase 4 Enhanced Methods
    
    def analyze(self, repo_path: str, focus: List[Dict] = None) -> List[Issue]:
        """
        Pattern-aware analysis with context integration (Task 17.1).
        
        Args:
            repo_path: Repository path to analyze
            focus: List of predicted issues with probabilities
            
        Returns:
            List of Issue objects with context
        """
        try:
            if self.verbose:
                print(f"🔍 Phase 4 Analysis: Analyzing {repo_path} with pattern awareness")
            
            # Get learned patterns for context
            patterns = self.memory.get_team_patterns(repo_path, "issue_frequency")
            
            # Extract focus rules from predictions
            focus_rules = [p["rule_id"] for p in focus or [] if p.get("probability", 0) > 0.7]
            
            if self.verbose and focus_rules:
                print(f"🎯 Focusing on predicted issues: {focus_rules}")
            
            # Run scanner with prioritized rules
            issues = self._run_scanner(repo_path, prioritize=focus_rules)
            
            # Apply pattern context to issues
            contextualized_issues = self._apply_context(issues, patterns)
            
            # Track issue patterns for learning
            for issue in contextualized_issues:
                self.memory.track_issue_pattern(
                    repo_path, 
                    issue.type, 
                    issue.rule_id, 
                    issue.severity.value
                )
            
            return contextualized_issues
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Pattern-aware analysis failed: {e}")
            return []
    
    def _run_scanner(self, repo_path: str, prioritize: List[str] = None) -> List[Issue]:
        """
        Run scanner with optional rule prioritization.
        
        Args:
            repo_path: Repository path
            prioritize: List of rule IDs to prioritize
            
        Returns:
            List of Issue objects
        """
        try:
            # Use existing scanner functionality
            analysis_result = scan_repository.invoke({
                "repo_path": repo_path,
                "config_path": None
            })
            
            if "error" in analysis_result:
                return []
            
            # Convert to Issue objects
            issues = []
            for file_data in analysis_result.get("files", []):
                for issue_data in file_data.get("issues", []):
                    issue = Issue(
                        file_path=file_data["file_path"],
                        line_number=issue_data.get("line_number", 1),
                        rule_id=issue_data.get("rule_id", "unknown"),
                        message=issue_data.get("message", ""),
                        severity=issue_data.get("severity", "low"),
                        issue_type=issue_data.get("type", "code_quality")
                    )
                    issues.append(issue)
            
            # Prioritize if focus rules provided
            if prioritize:
                prioritized = [i for i in issues if i.rule_id in prioritize]
                others = [i for i in issues if i.rule_id not in prioritize]
                issues = prioritized + others
            
            return issues
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Scanner execution failed: {e}")
            return []
    
    def _apply_context(self, issues: List[Issue], patterns: List[Dict]) -> List[Issue]:
        """
        Apply learned pattern context to issues.
        
        Args:
            issues: List of Issue objects
            patterns: List of learned patterns
            
        Returns:
            List of Issue objects with context applied
        """
        for issue in issues:
            # Find matching pattern
            matching_pattern = next(
                (p for p in patterns if p.get('pattern_type') == issue.rule_id), 
                None
            )
            
            if matching_pattern:
                # Add context from learned patterns
                pattern_data = matching_pattern.get('pattern_data', {})
                issue.context = {
                    'frequency': pattern_data.get('frequency', 0),
                    'confidence': matching_pattern.get('confidence', 0.0),
                    'last_seen': pattern_data.get('last_seen', ''),
                    'trend_score': pattern_data.get('trend_score', 0.0)
                }
            else:
                issue.context = {}
        
        return issues
    
    def assess_risk(self, issue: Issue) -> float:
        """
        Assess risk level for an issue using patterns and severity.
        
        Args:
            issue: Issue object to assess
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        try:
            # Get issue frequency patterns
            repo_path = issue.file_path.rsplit('/', 1)[0] if '/' in issue.file_path else '.'
            patterns = self.memory.get_team_patterns(repo_path, "issue_frequency")
            
            # Find frequency for this issue type
            freq = 0
            for pattern in patterns:
                if pattern.get('pattern_type') == issue.rule_id:
                    pattern_data = pattern.get('pattern_data', {})
                    freq = pattern_data.get('frequency', 0)
                    break
            
            # Normalize frequency (assume max frequency of 100)
            freq_score = min(freq / 100.0, 1.0)
            
            # Severity weights
            severity_weights = {
                'low': 0.1,
                'medium': 0.3, 
                'high': 0.6,
                'critical': 0.9
            }
            
            severity_score = severity_weights.get(issue.severity.value, 0.1)
            
            # Combined risk score (50% severity, 50% frequency)
            risk_score = min(1.0, severity_score * 0.5 + freq_score * 0.5)
            
            if self.verbose:
                print(f"🎯 Risk assessment for {issue.rule_id}: {risk_score:.2f} (severity: {severity_score}, freq: {freq_score})")
            
            return risk_score
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Risk assessment failed: {e}")
            return 0.5  # Default medium risk
    
    def analyze_trends(self, repo_path: str) -> Dict:
        """
        Analyze emerging issue trends using learned patterns.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Dictionary with trend analysis
        """
        try:
            if self.verbose:
                print(f"📈 Analyzing trends for {repo_path}")
            
            # Get issue trends from memory
            issue_trends = self.memory.get_issue_trends(repo_path)
            
            # Extract emerging patterns (positive trend)
            emerging_patterns = []
            for issue in issue_trends.get('trending_issues', []):
                if issue.get('trend_score', 0) > 0.1:
                    emerging_patterns.append({
                        "rule_id": issue['issue_rule'],
                        "frequency": issue['frequency'],
                        "growth": issue.get('trend_score', 0),
                        "severity": issue.get('severity', 'medium'),
                        "issue_type": issue.get('issue_type', 'code_quality')
                    })
            
            # Sort by growth rate
            emerging_patterns.sort(key=lambda x: x['growth'], reverse=True)
            
            return {
                "emerging_patterns": emerging_patterns[:10],  # Top 10
                "total_patterns": len(emerging_patterns),
                "analysis_date": datetime.now().isoformat(),
                "repo_path": repo_path
            }
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Trend analysis failed: {e}")
            return {"emerging_patterns": [], "total_patterns": 0}
    
    def prioritize_issues(self, issues: List[Issue], project_phase: str = "development") -> List[Issue]:
        """
        Intelligent issue prioritization with multi-factor analysis (Task 17.2).
        
        Args:
            issues: List of Issue objects
            project_phase: Current project phase (development, testing, production)
            
        Returns:
            List of prioritized Issue objects
        """
        try:
            if not issues:
                return []
            
            if self.verbose:
                print(f"🎯 Prioritizing {len(issues)} issues for {project_phase} phase")
            
            # Get learned patterns for frequency data
            repo_path = issues[0].file_path.rsplit('/', 1)[0] if '/' in issues[0].file_path else '.'
            patterns = self.memory.get_team_patterns(repo_path, "issue_frequency")
            
            # Create pattern lookup
            pattern_lookup = {}
            for pattern in patterns:
                pattern_type = pattern.get('pattern_type', '')
                pattern_data = pattern.get('pattern_data', {})
                pattern_lookup[pattern_type] = {
                    'frequency': pattern_data.get('frequency', 1),
                    'confidence': pattern.get('confidence', 0.0)
                }
            
            # Phase-based weights
            phase_weights = {
                "development": 0.3,
                "testing": 0.5, 
                "production": 0.7
            }
            phase_weight = phase_weights.get(project_phase, 0.5)
            
            # Calculate priority scores
            def calculate_priority(issue):
                # Base risk assessment
                risk_score = self.assess_risk(issue)
                
                # Pattern frequency boost
                pattern_info = pattern_lookup.get(issue.rule_id, {'frequency': 1, 'confidence': 0.0})
                frequency_factor = min(pattern_info['frequency'] / 10.0, 2.0)  # Cap at 2x
                
                # Phase adjustment
                phase_factor = 1 + phase_weight
                
                # Final priority score
                priority = risk_score * frequency_factor * phase_factor
                
                return min(priority, 10.0)  # Cap at 10.0
            
            # Sort by priority (highest first)
            prioritized = sorted(issues, key=calculate_priority, reverse=True)
            
            # Add priority scores to issues
            for i, issue in enumerate(prioritized):
                issue.priority_score = calculate_priority(issue)
                issue.priority_rank = i + 1
            
            if self.verbose:
                top_5 = prioritized[:5]
                print(f"🏆 Top 5 priorities: {[f'{i.rule_id}({i.priority_score:.2f})' for i in top_5]}")
            
            return prioritized
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Issue prioritization failed: {e}")
            return issues  # Return original order on failure
    
    def notify_stakeholders(self, issues: List[Issue], repo_path: str):
        """
        Send notifications to stakeholders based on issue severity and role.
        
        Args:
            issues: List of prioritized Issue objects
            repo_path: Repository path
        """
        try:
            if not issues:
                return
            
            if self.verbose:
                print(f"📢 Notifying stakeholders about {len(issues)} issues")
            
            # Categorize issues by stakeholder interest
            views = {
                "developer": [i for i in issues if i.severity.value in ['low', 'medium']],
                "lead": [i for i in issues if i.severity.value in ['high', 'critical']],
                "security": [i for i in issues if i.type == 'security'],
                "performance": [i for i in issues if i.type == 'performance']
            }
            
            # Send notifications (mock implementation)
            for role, role_issues in views.items():
                if role_issues:
                    self._send_notification(repo_path, role, role_issues)
            
            # Store notification patterns
            self.memory.store_pattern(
                repo_path,
                "notification_sent",
                {
                    "total_issues": len(issues),
                    "by_role": {role: len(role_issues) for role, role_issues in views.items()},
                    "timestamp": datetime.now().isoformat()
                },
                1.0
            )
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Stakeholder notification failed: {e}")
    
    def _send_notification(self, repo_path: str, role: str, issues: List[Issue]):
        """
        Send notification to specific role (mock implementation).
        
        Args:
            repo_path: Repository path
            role: Stakeholder role
            issues: List of issues for this role
        """
        if self.verbose:
            print(f"📧 Notification to {role}: {len(issues)} issues in {repo_path}")
            
            # Show top 3 issues for this role
            for i, issue in enumerate(issues[:3]):
                print(f"  {i+1}. {issue.rule_id} ({issue.severity.value}) - {issue.message[:50]}...")
        
        # In a real implementation, this would send emails, Slack messages, etc.
        # For now, we just log the notification
 
    def _prioritize_with_patterns(self, issues: List[Dict[str, Any]], repo_path: str) -> List[Dict[str, Any]]:
        """
        Prioritize issues using learned patterns from PatternMemory.
        
        Args:
            issues: List of issues to prioritize
            repo_path: Repository path for pattern lookup
            
        Returns:
            List of issues sorted by priority (highest first)
        """
        try:
            from ..memory.pattern_memory import PatternMemory
            pattern_memory = PatternMemory()
            
            # Get issue frequency patterns
            issue_trends = pattern_memory.get_issue_trends(repo_path)
            trending_issues = {
                issue['issue_rule']: issue['frequency'] 
                for issue in issue_trends.get('trending_issues', [])
            }
            
            # Calculate priority scores
            def calculate_priority_score(issue):
                score = 0
                
                # Base severity score
                severity_scores = {"critical": 100, "high": 75, "medium": 50, "low": 25}
                score += severity_scores.get(issue.get("severity", "low"), 25)
                
                # Pattern-based frequency boost
                rule_id = issue.get("rule_id", "")
                if rule_id in trending_issues:
                    frequency = trending_issues[rule_id]
                    score += min(frequency * 2, 50)  # Cap frequency boost at 50
                
                # Type-based priority
                issue_type = issue.get("type", "")
                if issue_type == "security":
                    score += 30
                elif issue_type == "performance":
                    score += 20
                elif issue_type == "maintainability":
                    score += 10
                
                return score
            
            # Sort by priority score (highest first)
            prioritized = sorted(issues, key=calculate_priority_score, reverse=True)
            
            # Add priority scores to issues
            for i, issue in enumerate(prioritized):
                issue['priority_score'] = calculate_priority_score(issue)
                issue['priority_rank'] = i + 1
            
            if self.verbose and trending_issues:
                print(f"🎯 Using learned patterns: {len(trending_issues)} issue types tracked")
            
            return prioritized
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Pattern-based prioritization failed: {e}")
            
            # Fallback to simple severity-based prioritization
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            return sorted(
                issues, 
                key=lambda x: severity_order.get(x.get("severity", "low"), 1),
                reverse=True
            )
    
    def _get_pattern_context(self, repo_path: str) -> str:
        """
        Get pattern context for AI prioritization.
        
        Args:
            repo_path: Repository path
            
        Returns:
            String describing learned patterns
        """
        try:
            from ..memory.pattern_memory import PatternMemory
            pattern_memory = PatternMemory()
            
            # Get issue trends
            issue_trends = pattern_memory.get_issue_trends(repo_path)
            trending_issues = issue_trends.get('trending_issues', [])
            
            if not trending_issues:
                return "No learned patterns available yet."
            
            # Create context summary
            context_parts = ["Learned patterns from repository history:"]
            
            # Top 5 most frequent issues
            top_issues = sorted(trending_issues, key=lambda x: x['frequency'], reverse=True)[:5]
            if top_issues:
                context_parts.append("Most frequent issues:")
                for issue in top_issues:
                    context_parts.append(f"  - {issue['issue_rule']} ({issue['issue_type']}): {issue['frequency']} occurrences")
            
            # Issue distribution
            issue_dist = issue_trends.get('issue_distribution', {})
            if issue_dist:
                context_parts.append("Issue type distribution:")
                for issue_type, count in sorted(issue_dist.items(), key=lambda x: x[1], reverse=True):
                    context_parts.append(f"  - {issue_type}: {count}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            return f"Pattern context unavailable: {str(e)}"