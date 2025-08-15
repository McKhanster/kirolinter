"""
Integrator Agent for KiroLinter AI Agent System - Phase 4 Enhanced.

The Integrator Agent handles intelligent PR management, workflow orchestration,
and automated GitHub integration with pattern-aware categorization.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .llm_config import get_chat_model, get_model_info
from ..memory.pattern_memory import create_pattern_memory


class IntegratorAgent:
    """
    AI agent specialized in intelligent PR management and workflow orchestration.
    
    Phase 4 Enhanced Features:
    - Smart PR management with intelligent descriptions
    - Automatic reviewer assignment based on expertise
    - Workflow orchestration and automation
    - Pattern-aware categorization and notifications
    """
    
    def __init__(self, model_provider: Optional[str] = None, memory=None, verbose: bool = False):
        """
        Initialize the Integrator Agent with Phase 4 enhancements.
        
        Args:
            model_provider: LLM provider (xai, ollama, openai) - auto-selects if None
            memory: PatternMemory instance (Redis-based)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.model_provider = model_provider
        
        # Initialize Redis-based PatternMemory
        self.memory = memory or create_pattern_memory(redis_only=True)
        
        # Initialize LLM using LiteLLM
        try:
            self.llm = get_chat_model(provider=model_provider)
            if verbose:
                model_info = get_model_info()
                preferred = model_info.get("preferred_model", {})
                print(f"🔗 Integrator: Using {preferred.get('description', 'Unknown')} model with Redis PatternMemory")
        except Exception as e:
            if verbose:
                print(f"⚠️ Integrator: Failed to initialize LLM: {e}")
            raise
        
        # Mock GitHub client (in real implementation, this would be a proper GitHub API client)
        self.client = MockGitHubClient(verbose=verbose)
    
    # Phase 4 Enhanced Methods
    
    def create_pr(self, repo_path: str, fixes: List[str]) -> Dict[str, Any]:
        """
        Smart PR management with intelligent descriptions (Task 19.1).
        
        Args:
            repo_path: Repository path
            fixes: List of applied fix IDs
            
        Returns:
            Dictionary with PR creation results
        """
        try:
            if not fixes:
                return {"pr_created": False, "reason": "No fixes to create PR for"}
            
            if self.verbose:
                print(f"🔗 Creating intelligent PR for {len(fixes)} fixes")
            
            # Categorize fixes using learned patterns
            categories = self._categorize_fixes(fixes, repo_path)
            
            # Generate intelligent PR description
            description = self._generate_pr_description(categories, repo_path)
            
            # Create PR title based on categories
            title = self._generate_pr_title(categories)
            
            # Create the pull request (mock implementation)
            pr = self.client.create_pull_request(repo_path, title, description)
            
            # Assign reviewers based on fix categories
            self._assign_reviewers(pr, categories)
            
            # Notify stakeholders
            self._notify_stakeholders(pr, categories)
            
            # Store PR creation pattern
            self.memory.store_pattern(
                repo_path,
                "pr_created",
                {
                    "pr_id": pr.get("number", 0),
                    "fixes": fixes,
                    "categories": categories,
                    "title": title,
                    "timestamp": datetime.now().isoformat()
                },
                1.0
            )
            
            if self.verbose:
                print(f"✅ Created PR #{pr.get('number', 0)}: {title}")
            
            return {
                "pr_created": True,
                "pr_number": pr.get("number", 0),
                "pr_url": pr.get("url", ""),
                "title": title,
                "categories": categories
            }
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ PR creation failed: {e}")
            return {"pr_created": False, "error": str(e)}
    
    def _categorize_fixes(self, fixes: List[str], repo_path: str) -> Dict[str, List[str]]:
        """
        Categorize fixes using learned patterns.
        
        Args:
            fixes: List of fix IDs
            repo_path: Repository path
            
        Returns:
            Dictionary with categorized fixes
        """
        try:
            # Get fix success patterns from memory
            patterns = self.memory.get_team_patterns(repo_path, "fix_success")
            
            # Create pattern lookup
            pattern_lookup = {}
            for pattern in patterns:
                pattern_data = pattern.get('pattern_data', {})
                issue_id = pattern_data.get('issue_id', '')
                fix_type = pattern_data.get('fix_type', 'code_quality')
                if issue_id:
                    pattern_lookup[issue_id] = fix_type
            
            # Categorize fixes
            categories = {
                "security": [],
                "performance": [],
                "code_quality": [],
                "maintainability": [],
                "style": [],
                "other": []
            }
            
            for fix_id in fixes:
                # Determine category from patterns or fix ID
                if fix_id in pattern_lookup:
                    fix_type = pattern_lookup[fix_id]
                else:
                    # Infer from fix ID
                    fix_type = self._infer_fix_type(fix_id)
                
                # Map to categories
                if fix_type in ['security', 'vulnerability']:
                    categories["security"].append(fix_id)
                elif fix_type in ['performance', 'optimization']:
                    categories["performance"].append(fix_id)
                elif fix_type in ['maintainability', 'complexity']:
                    categories["maintainability"].append(fix_id)
                elif fix_type in ['style', 'format', 'formatting']:
                    categories["style"].append(fix_id)
                else:
                    categories["code_quality"].append(fix_id)
            
            # Remove empty categories
            return {k: v for k, v in categories.items() if v}
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Fix categorization failed: {e}")
            return {"code_quality": fixes}  # Fallback
    
    def _infer_fix_type(self, fix_id: str) -> str:
        """
        Infer fix type from fix ID.
        
        Args:
            fix_id: Fix identifier
            
        Returns:
            Inferred fix type
        """
        fix_id_lower = fix_id.lower()
        
        if any(keyword in fix_id_lower for keyword in ['security', 'vuln', 'cve', 'auth', 'sql']):
            return 'security'
        elif any(keyword in fix_id_lower for keyword in ['perf', 'slow', 'memory', 'cpu']):
            return 'performance'
        elif any(keyword in fix_id_lower for keyword in ['complex', 'maintain', 'refactor']):
            return 'maintainability'
        elif any(keyword in fix_id_lower for keyword in ['style', 'format', 'lint', 'pep8']):
            return 'style'
        else:
            return 'code_quality'
    
    def _generate_pr_title(self, categories: Dict[str, List[str]]) -> str:
        """
        Generate intelligent PR title based on fix categories.
        
        Args:
            categories: Categorized fixes
            
        Returns:
            Generated PR title
        """
        total_fixes = sum(len(fixes) for fixes in categories.values())
        
        if len(categories) == 1:
            category = list(categories.keys())[0]
            return f"🔧 KiroLinter: Fix {total_fixes} {category} issue{'s' if total_fixes > 1 else ''}"
        else:
            return f"🔧 KiroLinter: Apply {total_fixes} automated fixes"
    
    def _generate_pr_description(self, categories: Dict[str, List[str]], repo_path: str) -> str:
        """
        Generate intelligent PR description with categorized fixes.
        
        Args:
            categories: Categorized fixes
            repo_path: Repository path
            
        Returns:
            Generated PR description
        """
        try:
            total_fixes = sum(len(fixes) for fixes in categories.values())
            
            description_parts = [
                "## 🤖 KiroLinter Automated Fixes",
                "",
                f"This PR applies **{total_fixes} automated fixes** identified by KiroLinter's AI analysis.",
                ""
            ]
            
            # Add category breakdown
            if len(categories) > 1:
                description_parts.extend([
                    "### 📊 Fix Categories",
                    ""
                ])
                
                category_icons = {
                    "security": "🔒",
                    "performance": "⚡",
                    "code_quality": "✨",
                    "maintainability": "🔧",
                    "style": "🎨"
                }
                
                for category, fixes in categories.items():
                    icon = category_icons.get(category, "📝")
                    description_parts.append(f"- {icon} **{category.title()}**: {len(fixes)} fix{'es' if len(fixes) > 1 else ''}")
                
                description_parts.append("")
            
            # Add safety information
            description_parts.extend([
                "### 🛡️ Safety Information",
                "",
                "- All fixes have been validated for safety before application",
                "- Automatic backups were created before any modifications",
                "- Changes can be rolled back if needed",
                "- Only high-confidence fixes (>90%) were applied automatically",
                ""
            ])
            
            # Add review guidance
            description_parts.extend([
                "### 👀 Review Guidance",
                "",
                "Please review the changes and verify they meet your project's standards.",
                "The fixes are based on learned patterns from your repository's history.",
                ""
            ])
            
            # Add footer
            description_parts.extend([
                "---",
                "*Generated by KiroLinter AI Agent System*"
            ])
            
            return "\n".join(description_parts)
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ PR description generation failed: {e}")
            return f"KiroLinter applied {sum(len(fixes) for fixes in categories.values())} automated fixes."
    
    def _assign_reviewers(self, pr: Dict[str, Any], categories: Dict[str, List[str]]):
        """
        Assign reviewers based on fix categories and expertise.
        
        Args:
            pr: Pull request object
            categories: Categorized fixes
        """
        try:
            reviewers = []
            
            # Assign based on categories
            if "security" in categories and categories["security"]:
                reviewers.extend(["security_team", "security_lead"])
            
            if "performance" in categories and categories["performance"]:
                reviewers.extend(["performance_team", "tech_lead"])
            
            # Default reviewers for other categories
            if any(cat in categories for cat in ["code_quality", "maintainability", "style"]):
                reviewers.extend(["dev_team", "code_reviewer"])
            
            # Remove duplicates and limit to reasonable number
            reviewers = list(set(reviewers))[:3]
            
            if reviewers:
                self.client.assign_reviewers(pr, reviewers)
                
                if self.verbose:
                    print(f"👥 Assigned reviewers: {', '.join(reviewers)}")
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Reviewer assignment failed: {e}")
    
    def _notify_stakeholders(self, pr: Dict[str, Any], categories: Dict[str, List[str]]):
        """
        Notify stakeholders based on fix categories.
        
        Args:
            pr: Pull request object
            categories: Categorized fixes
        """
        try:
            notifications = []
            
            # High-priority notifications
            if "security" in categories and categories["security"]:
                notifications.append({
                    "recipients": ["security_team", "tech_lead"],
                    "priority": "high",
                    "message": f"Security fixes applied in PR #{pr.get('number', 0)}"
                })
            
            # Standard notifications
            if any(cat in categories for cat in ["performance", "code_quality"]):
                notifications.append({
                    "recipients": ["dev_team"],
                    "priority": "normal",
                    "message": f"Code quality fixes applied in PR #{pr.get('number', 0)}"
                })
            
            # Send notifications (mock implementation)
            for notification in notifications:
                self._send_notification(notification)
            
            if self.verbose and notifications:
                print(f"📢 Sent {len(notifications)} stakeholder notifications")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Stakeholder notification failed: {e}")
    
    def _send_notification(self, notification: Dict[str, Any]):
        """
        Send notification to stakeholders (mock implementation).
        
        Args:
            notification: Notification details
        """
        if self.verbose:
            recipients = ", ".join(notification["recipients"])
            print(f"📧 {notification['priority'].upper()}: {notification['message']} -> {recipients}")
    
    # Legacy method for backward compatibility
    def create_fix_pr(self, repo_path: str, fix_results: Dict[str, Any], pr_title: str) -> Dict[str, Any]:
        """Create a pull request with applied fixes (legacy method)."""
        fixes = fix_results.get("applied_fixes", [])
        result = self.create_pr(repo_path, fixes)
        
        return {
            "pr_created": result.get("pr_created", False),
            "pr_url": result.get("pr_url", ""),
            "pr_number": result.get("pr_number", 0)
        }


class MockGitHubClient:
    """
    Mock GitHub client for testing and development.
    
    In a real implementation, this would be replaced with a proper
    GitHub API client like PyGithub or github3.py.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.pr_counter = 1000  # Start PR numbers at 1000
    
    def create_pull_request(self, repo_path: str, title: str, description: str) -> Dict[str, Any]:
        """
        Create a pull request (mock implementation).
        
        Args:
            repo_path: Repository path
            title: PR title
            description: PR description
            
        Returns:
            Mock PR object
        """
        pr_number = self.pr_counter
        self.pr_counter += 1
        
        pr = {
            "number": pr_number,
            "title": title,
            "description": description,
            "url": f"https://github.com/mock-org/{repo_path.split('/')[-1]}/pull/{pr_number}",
            "state": "open",
            "created_at": datetime.now().isoformat()
        }
        
        if self.verbose:
            print(f"🔗 Mock PR created: #{pr_number} - {title}")
        
        return pr
    
    def assign_reviewers(self, pr: Dict[str, Any], reviewers: List[str]):
        """
        Assign reviewers to PR (mock implementation).
        
        Args:
            pr: PR object
            reviewers: List of reviewer usernames
        """
        pr["reviewers"] = reviewers
        
        if self.verbose:
            print(f"👥 Mock reviewers assigned to PR #{pr['number']}: {', '.join(reviewers)}")
    
    def add_labels(self, pr: Dict[str, Any], labels: List[str]):
        """
        Add labels to PR (mock implementation).
        
        Args:
            pr: PR object
            labels: List of label names
        """
        pr["labels"] = labels
        
        if self.verbose:
            print(f"🏷️  Mock labels added to PR #{pr['number']}: {', '.join(labels)}")