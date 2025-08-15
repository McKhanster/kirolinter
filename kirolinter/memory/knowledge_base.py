"""
Knowledge Base for KiroLinter AI Agent System.

This module provides structured storage and retrieval of coding insights,
patterns, and best practices with semantic search capabilities.
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
import re


class KnowledgeBase:
    """
    Structured knowledge storage system for coding insights and patterns.
    
    Features:
    - JSON-based knowledge storage with semantic search
    - Pattern library for reusable coding patterns and best practices
    - Fix template storage with success rate tracking
    - Team insights aggregation and reporting
    - Cross-repository pattern sharing
    """
    
    def __init__(self, knowledge_dir: Optional[str] = None):
        """
        Initialize knowledge base.
        
        Args:
            knowledge_dir: Optional directory for knowledge storage
        """
        if knowledge_dir:
            self.knowledge_dir = Path(knowledge_dir)
        else:
            # Default to .kiro directory
            self.knowledge_dir = Path.cwd() / ".kiro" / "knowledge_base"
        
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Initialize storage files
        self.patterns_file = self.knowledge_dir / "patterns.json"
        self.templates_file = self.knowledge_dir / "fix_templates.json"
        self.insights_file = self.knowledge_dir / "team_insights.json"
        self.best_practices_file = self.knowledge_dir / "best_practices.json"
        
        # Load existing data
        self.patterns = self._load_json_file(self.patterns_file, {})
        self.fix_templates = self._load_json_file(self.templates_file, {})
        self.team_insights = self._load_json_file(self.insights_file, {})
        self.best_practices = self._load_json_file(self.best_practices_file, {})
    
    def _load_json_file(self, file_path: Path, default: Any) -> Any:
        """Load JSON file with error handling."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
        return default
    
    def _save_json_file(self, file_path: Path, data: Any) -> bool:
        """Save data to JSON file with error handling."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save {file_path}: {e}")
            return False
    
    def store_pattern(self, pattern_id: str, pattern_data: Dict[str, Any],
                     category: str = "general", tags: Optional[List[str]] = None) -> bool:
        """
        Store a coding pattern in the knowledge base.
        
        Args:
            pattern_id: Unique identifier for the pattern
            pattern_data: Pattern details and implementation
            category: Pattern category (e.g., 'naming', 'structure', 'security')
            tags: Optional tags for better searchability
            
        Returns:
            True if stored successfully
        """
        try:
            pattern_entry = {
                "id": pattern_id,
                "category": category,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "usage_count": 0,
                "success_rate": 0.0,
                "data": pattern_data
            }
            
            # Update existing pattern or create new one
            if pattern_id in self.patterns:
                existing = self.patterns[pattern_id]
                pattern_entry["created_at"] = existing.get("created_at", pattern_entry["created_at"])
                pattern_entry["usage_count"] = existing.get("usage_count", 0) + 1  # Increment usage count
                pattern_entry["success_rate"] = existing.get("success_rate", 0.0)
            
            self.patterns[pattern_id] = pattern_entry
            
            # Save to disk
            if self._save_json_file(self.patterns_file, self.patterns):
                self.logger.info(f"Stored pattern: {pattern_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern {pattern_id}: {e}")
            return False
    
    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific pattern by ID.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Pattern data or None if not found
        """
        return self.patterns.get(pattern_id)
    
    def search_patterns(self, query: str, category: Optional[str] = None,
                       tags: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search patterns using semantic matching.
        
        Args:
            query: Search query
            category: Optional category filter
            tags: Optional tags filter
            limit: Maximum number of results
            
        Returns:
            List of matching patterns with relevance scores
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        matches = []
        
        for pattern_id, pattern in self.patterns.items():
            # Apply filters
            if category and pattern.get("category") != category:
                continue
            
            if tags and not any(tag in pattern.get("tags", []) for tag in tags):
                continue
            
            # Calculate relevance score
            relevance_score = 0
            
            # Check pattern ID
            if query_lower in pattern_id.lower():
                relevance_score += 3
            
            # Check category
            if query_lower in pattern.get("category", "").lower():
                relevance_score += 2
            
            # Check tags
            for tag in pattern.get("tags", []):
                if query_lower in tag.lower():
                    relevance_score += 2
            
            # Check pattern data (convert to string for searching)
            pattern_text = json.dumps(pattern.get("data", {})).lower()
            
            # Exact phrase match
            if query_lower in pattern_text:
                relevance_score += 3
            
            # Word matches
            pattern_words = set(re.findall(r'\w+', pattern_text))
            common_words = query_words.intersection(pattern_words)
            relevance_score += len(common_words)
            
            # Boost score based on usage and success rate
            usage_boost = min(pattern.get("usage_count", 0) * 0.1, 2.0)
            success_boost = pattern.get("success_rate", 0.0) * 2.0
            relevance_score += usage_boost + success_boost
            
            if relevance_score > 0:
                pattern_copy = pattern.copy()
                pattern_copy["relevance_score"] = relevance_score
                matches.append(pattern_copy)
        
        # Sort by relevance score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches[:limit]
    
    def store_fix_template(self, template_id: str, template_data: Dict[str, Any],
                          issue_type: str, success_rate: float = 0.0) -> bool:
        """
        Store a fix template with success tracking.
        
        Args:
            template_id: Unique identifier for the template
            template_data: Template implementation and metadata
            issue_type: Type of issue this template addresses
            success_rate: Historical success rate (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
        try:
            template_entry = {
                "id": template_id,
                "issue_type": issue_type,
                "success_rate": success_rate,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "data": template_data
            }
            
            # Update existing template or create new one
            if template_id in self.fix_templates:
                existing = self.fix_templates[template_id]
                template_entry["created_at"] = existing.get("created_at", template_entry["created_at"])
                template_entry["usage_count"] = existing.get("usage_count", 0)
            
            self.fix_templates[template_id] = template_entry
            
            # Save to disk
            if self._save_json_file(self.templates_file, self.fix_templates):
                self.logger.info(f"Stored fix template: {template_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to store fix template {template_id}: {e}")
            return False
    
    def get_fix_templates(self, issue_type: Optional[str] = None,
                         min_success_rate: float = 0.0) -> List[Dict[str, Any]]:
        """
        Get fix templates, optionally filtered by issue type and success rate.
        
        Args:
            issue_type: Optional filter by issue type
            min_success_rate: Minimum success rate threshold
            
        Returns:
            List of matching fix templates
        """
        templates = []
        
        for template_id, template in self.fix_templates.items():
            # Apply filters
            if issue_type and template.get("issue_type") != issue_type:
                continue
            
            if template.get("success_rate", 0.0) < min_success_rate:
                continue
            
            templates.append(template)
        
        # Sort by success rate and usage count
        templates.sort(key=lambda x: (x.get("success_rate", 0.0), x.get("usage_count", 0)), reverse=True)
        return templates
    
    def update_template_success_rate(self, template_id: str, success: bool) -> bool:
        """
        Update the success rate of a fix template based on usage outcome.
        
        Args:
            template_id: Template identifier
            success: Whether the template application was successful
            
        Returns:
            True if updated successfully
        """
        try:
            if template_id not in self.fix_templates:
                self.logger.warning(f"Template {template_id} not found for success rate update")
                return False
            
            template = self.fix_templates[template_id]
            
            # Update usage count
            usage_count = template.get("usage_count", 0) + 1
            template["usage_count"] = usage_count
            
            # Update success rate using exponential moving average
            current_rate = template.get("success_rate", 0.0)
            alpha = 0.1  # Learning rate
            new_rate = current_rate + alpha * (1.0 if success else 0.0 - current_rate)
            template["success_rate"] = max(0.0, min(1.0, new_rate))
            
            template["updated_at"] = datetime.now().isoformat()
            
            # Save to disk
            if self._save_json_file(self.templates_file, self.fix_templates):
                self.logger.info(f"Updated success rate for template {template_id}: {template['success_rate']:.2f}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update template success rate: {e}")
            return False
    
    def store_team_insight(self, repo_path: str, insight_data: Dict[str, Any],
                          insight_type: str = "general") -> bool:
        """
        Store team-specific insights and recommendations.
        
        Args:
            repo_path: Repository path
            insight_data: Insight details and recommendations
            insight_type: Type of insight (e.g., 'style', 'quality', 'security')
            
        Returns:
            True if stored successfully
        """
        try:
            if repo_path not in self.team_insights:
                self.team_insights[repo_path] = {}
            
            insight_id = hashlib.md5(f"{repo_path}_{insight_type}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            insight_entry = {
                "id": insight_id,
                "type": insight_type,
                "created_at": datetime.now().isoformat(),
                "data": insight_data
            }
            
            if insight_type not in self.team_insights[repo_path]:
                self.team_insights[repo_path][insight_type] = []
            
            self.team_insights[repo_path][insight_type].append(insight_entry)
            
            # Keep only recent insights (last 50 per type)
            self.team_insights[repo_path][insight_type] = self.team_insights[repo_path][insight_type][-50:]
            
            # Save to disk
            if self._save_json_file(self.insights_file, self.team_insights):
                self.logger.info(f"Stored team insight for {repo_path}: {insight_type}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to store team insight: {e}")
            return False
    
    def get_team_insights(self, repo_path: str, insight_type: Optional[str] = None,
                         days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get team insights for a repository.
        
        Args:
            repo_path: Repository path
            insight_type: Optional filter by insight type
            days_back: Number of days to look back
            
        Returns:
            List of matching insights
        """
        if repo_path not in self.team_insights:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        insights = []
        
        repo_insights = self.team_insights[repo_path]
        
        for itype, insight_list in repo_insights.items():
            if insight_type and itype != insight_type:
                continue
            
            for insight in insight_list:
                created_at = datetime.fromisoformat(insight["created_at"])
                if created_at >= cutoff_date:
                    insights.append(insight)
        
        # Sort by creation date (most recent first)
        insights.sort(key=lambda x: x["created_at"], reverse=True)
        return insights
    
    def store_best_practice(self, practice_id: str, practice_data: Dict[str, Any],
                           category: str = "general", language: str = "python") -> bool:
        """
        Store a coding best practice.
        
        Args:
            practice_id: Unique identifier for the practice
            practice_data: Practice details and examples
            category: Practice category
            language: Programming language
            
        Returns:
            True if stored successfully
        """
        try:
            practice_entry = {
                "id": practice_id,
                "category": category,
                "language": language,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "data": practice_data
            }
            
            if category not in self.best_practices:
                self.best_practices[category] = {}
            
            self.best_practices[category][practice_id] = practice_entry
            
            # Save to disk
            if self._save_json_file(self.best_practices_file, self.best_practices):
                self.logger.info(f"Stored best practice: {practice_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to store best practice {practice_id}: {e}")
            return False
    
    def get_best_practices(self, category: Optional[str] = None,
                          language: str = "python") -> List[Dict[str, Any]]:
        """
        Get best practices, optionally filtered by category and language.
        
        Args:
            category: Optional category filter
            language: Programming language filter
            
        Returns:
            List of matching best practices
        """
        practices = []
        
        categories_to_search = [category] if category else self.best_practices.keys()
        
        for cat in categories_to_search:
            if cat not in self.best_practices:
                continue
            
            for practice_id, practice in self.best_practices[cat].items():
                if practice.get("language") == language:
                    practices.append(practice)
        
        return practices
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the knowledge base contents.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        return {
            "total_patterns": len(self.patterns),
            "total_fix_templates": len(self.fix_templates),
            "total_repositories_with_insights": len(self.team_insights),
            "total_best_practices": sum(len(practices) for practices in self.best_practices.values()),
            "pattern_categories": list(set(p.get("category", "unknown") for p in self.patterns.values())),
            "template_issue_types": list(set(t.get("issue_type", "unknown") for t in self.fix_templates.values())),
            "insight_repositories": list(self.team_insights.keys()),
            "best_practice_categories": list(self.best_practices.keys()),
            "knowledge_dir": str(self.knowledge_dir)
        }
    
    def export_knowledge(self, export_path: str) -> bool:
        """
        Export entire knowledge base to a single JSON file.
        
        Args:
            export_path: Path to export file
            
        Returns:
            True if export successful
        """
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "summary": self.get_knowledge_summary(),
                "patterns": self.patterns,
                "fix_templates": self.fix_templates,
                "team_insights": self.team_insights,
                "best_practices": self.best_practices
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Knowledge base exported to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export knowledge base: {e}")
            return False
    
    def import_knowledge(self, import_path: str, merge: bool = True) -> bool:
        """
        Import knowledge base from a JSON file with deduplication.
        
        Args:
            import_path: Path to import file
            merge: Whether to merge with existing data or replace
            
        Returns:
            True if import successful
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if merge:
                # Merge patterns with deduplication
                for pattern_id, pattern_data in import_data.get("patterns", {}).items():
                    if pattern_id not in self.patterns:
                        self.patterns[pattern_id] = pattern_data
                    else:
                        # Update usage count and timestamp for existing patterns
                        existing = self.patterns[pattern_id]
                        existing["usage_count"] = existing.get("usage_count", 0) + pattern_data.get("usage_count", 0)
                        existing["updated_at"] = datetime.now().isoformat()
                
                # Merge fix templates with deduplication
                for template_id, template_data in import_data.get("fix_templates", {}).items():
                    if template_id not in self.fix_templates:
                        self.fix_templates[template_id] = template_data
                    else:
                        # Update success rate using weighted average
                        existing = self.fix_templates[template_id]
                        existing_count = existing.get("usage_count", 1)
                        import_count = template_data.get("usage_count", 1)
                        total_count = existing_count + import_count
                        
                        existing_rate = existing.get("success_rate", 0.0)
                        import_rate = template_data.get("success_rate", 0.0)
                        
                        weighted_rate = (existing_rate * existing_count + import_rate * import_count) / total_count
                        existing["success_rate"] = weighted_rate
                        existing["usage_count"] = total_count
                        existing["updated_at"] = datetime.now().isoformat()
                
                # Merge team insights (avoid duplicates by checking timestamps)
                for repo_path, insights in import_data.get("team_insights", {}).items():
                    if repo_path not in self.team_insights:
                        self.team_insights[repo_path] = {}
                    for insight_type, insight_list in insights.items():
                        if insight_type not in self.team_insights[repo_path]:
                            self.team_insights[repo_path][insight_type] = []
                        
                        # Deduplicate by checking existing insight IDs
                        existing_ids = {insight.get("id") for insight in self.team_insights[repo_path][insight_type]}
                        new_insights = [insight for insight in insight_list if insight.get("id") not in existing_ids]
                        self.team_insights[repo_path][insight_type].extend(new_insights)
                
                # Merge best practices with deduplication
                for category, practices in import_data.get("best_practices", {}).items():
                    if category not in self.best_practices:
                        self.best_practices[category] = {}
                    for practice_id, practice_data in practices.items():
                        if practice_id not in self.best_practices[category]:
                            self.best_practices[category][practice_id] = practice_data
            else:
                # Replace existing data
                self.patterns = import_data.get("patterns", {})
                self.fix_templates = import_data.get("fix_templates", {})
                self.team_insights = import_data.get("team_insights", {})
                self.best_practices = import_data.get("best_practices", {})
            
            # Save all data
            success = all([
                self._save_json_file(self.patterns_file, self.patterns),
                self._save_json_file(self.templates_file, self.fix_templates),
                self._save_json_file(self.insights_file, self.team_insights),
                self._save_json_file(self.best_practices_file, self.best_practices)
            ])
            
            if success:
                self.logger.info(f"Knowledge base imported from {import_path} with deduplication")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to import knowledge base: {e}")
            return False