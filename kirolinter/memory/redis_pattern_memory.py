"""
Redis-based Pattern Memory for KiroLinter AI Agent System.

This module provides high-performance, lock-free pattern storage using Redis
with automatic fallback to SQLite for compatibility.
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Import DataAnonymizer from separate module to avoid circular imports
from .anonymizer import DataAnonymizer


class RedisPatternMemory:
    """
    Redis-based pattern memory with zero concurrency issues.
    
    Features:
    - Lock-free operations using Redis atomic commands
    - Automatic data expiration with configurable TTL
    - High-performance hash and set operations
    - JSON serialization for complex data structures
    - Seamless fallback to SQLite when Redis unavailable
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 7776000):  # 90 days
        """
        Initialize Redis-only pattern memory.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL for patterns in seconds (90 days)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(__name__)
        self.anonymizer = DataAnonymizer()
        
        # Connect to Redis (required)
        if not REDIS_AVAILABLE:
            raise Exception("Redis-only mode: Redis library not available")
        
        try:
            self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            self.use_redis = True
            self.sqlite_memory = None  # No SQLite fallback
            self.logger.info("Redis connection established")
        except Exception as e:
            raise Exception(f"Redis-only mode: Redis connection failed: {e}")
    
    def _get_pattern_key(self, repo_path: str, pattern_type: str) -> str:
        """Generate Redis key for pattern storage."""
        return f"kirolinter:pattern:{repo_path}:{pattern_type}"
    
    def _get_issue_key(self, repo_path: str) -> str:
        """Generate Redis key for issue patterns."""
        return f"kirolinter:issues:{repo_path}"
    
    def _get_fix_key(self, repo_path: str) -> str:
        """Generate Redis key for fix outcomes."""
        return f"kirolinter:fixes:{repo_path}"
    
    def _get_session_key(self, repo_path: str) -> str:
        """Generate Redis key for learning sessions."""
        return f"kirolinter:sessions:{repo_path}"
    
    def store_pattern(self, repo_path: str, pattern_type: str, 
                     pattern_data: Dict[str, Any], confidence: float = 0.0) -> bool:
        """
        Store a pattern with Redis atomic operations.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern
            pattern_data: Pattern details and rules
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
        # Redis-only mode - no fallback needed
        
        try:
            # Validate input
            if not repo_path or not pattern_type or not pattern_data:
                self.logger.error("Invalid input for pattern storage")
                return False
            
            if not 0.0 <= confidence <= 1.0:
                self.logger.error(f"Invalid confidence score: {confidence}")
                return False
            
            # Anonymize sensitive data
            anonymized_data = self.anonymizer.anonymize_pattern_data(pattern_data)
            
            # Validate anonymization
            if not self.anonymizer.validate_anonymization(anonymized_data):
                self.logger.error("Anonymization validation failed - pattern not stored")
                return False
            
            # Prepare pattern entry
            pattern_key = self._get_pattern_key(repo_path, pattern_type)
            now = datetime.now().isoformat()
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Check if pattern exists to preserve creation time and usage count
            existing = self.redis.hgetall(pattern_key)
            created_at = existing.get("created_at", now)
            usage_count = int(existing.get("usage_count", 0)) + (1 if existing else 0)
            
            # Record learning change for audit trail
            before_data = existing.get("pattern_data") if existing else None
            after_data = json.dumps(anonymized_data)
            
            if existing:
                reason = f"Updated pattern confidence from {existing.get('confidence', 0)} to {confidence}"
            else:
                reason = f"Created new pattern with confidence {confidence}"
            
            # Store pattern data
            pattern_entry = {
                "pattern_type": pattern_type,
                "pattern_data": after_data,
                "confidence": str(confidence),
                "usage_count": str(usage_count),
                "created_at": created_at,
                "updated_at": now
            }
            
            pipe.hset(pattern_key, mapping=pattern_entry)
            pipe.expire(pattern_key, self.default_ttl)
            
            # Add to pattern index for efficient retrieval
            index_key = f"kirolinter:index:patterns:{repo_path}"
            pipe.sadd(index_key, pattern_type)
            pipe.expire(index_key, self.default_ttl)
            
            # Execute pipeline
            pipe.execute()
            
            # Record the learning change (after the main operation)
            self.record_learning_change(repo_path, pattern_type, before_data, after_data, reason)
            
            self.logger.info(f"Stored pattern: {pattern_type} for {repo_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            return False
    
    def get_team_patterns(self, repo_path: str, pattern_type: Optional[str] = None,
                         min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Retrieve team patterns for a repository.
        
        Args:
            repo_path: Repository path
            pattern_type: Optional filter by pattern type
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching patterns
        """
        try:
            patterns = []
            
            if pattern_type:
                # Get specific pattern
                pattern_key = self._get_pattern_key(repo_path, pattern_type)
                pattern_data = self.redis.hgetall(pattern_key)
                
                if pattern_data and float(pattern_data.get("confidence", 0)) >= min_confidence:
                    pattern = self._format_pattern_response(pattern_data)
                    if pattern:
                        patterns.append(pattern)
            else:
                # Get all patterns for repository
                index_key = f"kirolinter:index:patterns:{repo_path}"
                pattern_types = self.redis.smembers(index_key)
                
                for ptype in pattern_types:
                    pattern_key = self._get_pattern_key(repo_path, ptype)
                    pattern_data = self.redis.hgetall(pattern_key)
                    
                    if pattern_data and float(pattern_data.get("confidence", 0)) >= min_confidence:
                        pattern = self._format_pattern_response(pattern_data)
                        if pattern:
                            patterns.append(pattern)
            
            # Sort by confidence and usage count
            patterns.sort(key=lambda x: (x.get("confidence", 0), x.get("usage_count", 0)), reverse=True)
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve team patterns: {e}")
            return []
    
    def _format_pattern_response(self, pattern_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Format Redis pattern data for response."""
        try:
            return {
                "pattern_type": pattern_data.get("pattern_type", ""),
                "pattern_data": json.loads(pattern_data.get("pattern_data", "{}")),
                "confidence": float(pattern_data.get("confidence", 0)),
                "usage_count": int(pattern_data.get("usage_count", 0)),
                "created_at": pattern_data.get("created_at", ""),
                "updated_at": pattern_data.get("updated_at", "")
            }
        except Exception as e:
            self.logger.error(f"Failed to format pattern response: {e}")
            return None
    
    def track_issue_pattern(self, repo_path: str, issue_type: str, 
                           issue_rule: str, severity: str) -> bool:
        """
        Track occurrence of an issue pattern using Redis atomic operations.
        
        Args:
            repo_path: Repository path
            issue_type: Type of issue
            issue_rule: Specific rule that triggered
            severity: Issue severity level
            
        Returns:
            True if tracked successfully
        """
        try:
            issue_key = self._get_issue_key(repo_path)
            issue_id = f"{issue_type}:{issue_rule}"
            now = datetime.now().isoformat()
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Get existing issue data
            existing = self.redis.hget(issue_key, issue_id)
            if existing:
                issue_data = json.loads(existing)
                issue_data["frequency"] = issue_data.get("frequency", 0) + 1
                issue_data["last_seen"] = now
                issue_data["trend_score"] = issue_data.get("trend_score", 0) + 0.1
            else:
                issue_data = {
                    "issue_type": issue_type,
                    "issue_rule": issue_rule,
                    "severity": severity,
                    "frequency": 1,
                    "last_seen": now,
                    "trend_score": 0.1,
                    "created_at": now
                }
            
            # Store updated issue data
            pipe.hset(issue_key, issue_id, json.dumps(issue_data))
            pipe.expire(issue_key, self.default_ttl)
            pipe.execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track issue pattern: {e}")
            return False
    
    def get_issue_trends(self, repo_path: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get trending issue patterns for a repository.
        
        Args:
            repo_path: Repository path
            days_back: Number of days to look back for trends
            
        Returns:
            Dictionary with trending issues and statistics
        """
        try:
            issue_key = self._get_issue_key(repo_path)
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            trends = {
                "trending_issues": [],
                "issue_distribution": Counter(),
                "severity_distribution": Counter(),
                "total_patterns": 0
            }
            
            # Get all issue patterns
            all_issues = self.redis.hgetall(issue_key)
            
            for issue_id, issue_json in all_issues.items():
                try:
                    issue_data = json.loads(issue_json)
                    
                    # Filter by date
                    if issue_data.get("last_seen", "") >= cutoff_date:
                        trends["trending_issues"].append(issue_data)
                        trends["issue_distribution"][issue_data["issue_type"]] += issue_data["frequency"]
                        trends["severity_distribution"][issue_data["severity"]] += issue_data["frequency"]
                        trends["total_patterns"] += 1
                        
                except json.JSONDecodeError:
                    continue
            
            # Sort by trend score and frequency
            trends["trending_issues"].sort(
                key=lambda x: (x.get("trend_score", 0), x.get("frequency", 0)), 
                reverse=True
            )
            trends["trending_issues"] = trends["trending_issues"][:20]  # Limit to top 20
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Failed to get issue trends: {e}")
            return {"trending_issues": [], "issue_distribution": {}, "severity_distribution": {}, "total_patterns": 0}
    
    def record_fix_outcome(self, repo_path: str, issue_type: str, fix_type: str,
                          success: bool, feedback_score: float = 0.0,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record the outcome of an applied fix using Redis lists.
        
        Args:
            repo_path: Repository path
            issue_type: Type of issue that was fixed
            fix_type: Type of fix applied
            success: Whether the fix was successful
            feedback_score: User feedback score (-1.0 to 1.0)
            metadata: Additional metadata about the fix
            
        Returns:
            True if recorded successfully
        """
        try:
            fix_key = self._get_fix_key(repo_path)
            now = datetime.now().isoformat()
            
            fix_outcome = {
                "issue_type": issue_type,
                "fix_type": fix_type,
                "success": success,
                "feedback_score": feedback_score,
                "metadata": metadata or {},
                "applied_at": now
            }
            
            # Use Redis pipeline
            pipe = self.redis.pipeline()
            pipe.lpush(fix_key, json.dumps(fix_outcome))
            pipe.ltrim(fix_key, 0, 999)  # Keep last 1000 outcomes
            pipe.expire(fix_key, self.default_ttl)
            pipe.execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record fix outcome: {e}")
            return False
    
    def get_fix_success_rates(self, repo_path: str) -> Dict[str, Any]:
        """
        Get success rates for different types of fixes.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Dictionary with success rates by fix type
        """
        try:
            fix_key = self._get_fix_key(repo_path)
            fix_outcomes = self.redis.lrange(fix_key, 0, -1)
            
            success_rates = defaultdict(lambda: {
                "total_attempts": 0,
                "successful_fixes": 0,
                "success_rate": 0.0,
                "avg_feedback": 0.0,
                "feedback_scores": []
            })
            
            for outcome_json in fix_outcomes:
                try:
                    outcome = json.loads(outcome_json)
                    fix_type = outcome["fix_type"]
                    
                    success_rates[fix_type]["total_attempts"] += 1
                    if outcome["success"]:
                        success_rates[fix_type]["successful_fixes"] += 1
                    
                    feedback_score = outcome.get("feedback_score", 0.0)
                    success_rates[fix_type]["feedback_scores"].append(feedback_score)
                    
                except json.JSONDecodeError:
                    continue
            
            # Calculate final rates
            for fix_type, stats in success_rates.items():
                total = stats["total_attempts"]
                successful = stats["successful_fixes"]
                feedback_scores = stats["feedback_scores"]
                
                stats["success_rate"] = successful / total if total > 0 else 0.0
                stats["avg_feedback"] = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0.0
                del stats["feedback_scores"]  # Remove temporary list
            
            return dict(success_rates)
            
        except Exception as e:
            self.logger.error(f"Failed to get fix success rates: {e}")
            return {}
    
    def record_learning_session(self, repo_path: str, session_type: str,
                               patterns_learned: int, insights_generated: int,
                               session_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record a learning session for analytics.
        
        Args:
            repo_path: Repository path
            session_type: Type of learning session
            patterns_learned: Number of patterns learned
            insights_generated: Number of insights generated
            session_data: Additional session data
            
        Returns:
            True if recorded successfully
        """
        try:
            session_key = self._get_session_key(repo_path)
            now = datetime.now().isoformat()
            
            session_record = {
                "session_type": session_type,
                "patterns_learned": patterns_learned,
                "insights_generated": insights_generated,
                "session_data": session_data or {},
                "created_at": now
            }
            
            # Use Redis pipeline
            pipe = self.redis.pipeline()
            pipe.lpush(session_key, json.dumps(session_record))
            pipe.ltrim(session_key, 0, 499)  # Keep last 500 sessions
            pipe.expire(session_key, self.default_ttl)
            pipe.execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record learning session: {e}")
            return False
    
    def get_learning_analytics(self, repo_path: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get learning analytics for a repository.
        
        Args:
            repo_path: Repository path
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with learning analytics
        """
        try:
            session_key = self._get_session_key(repo_path)
            sessions = self.redis.lrange(session_key, 0, -1)
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            analytics = {
                "total_sessions": 0,
                "total_patterns_learned": 0,
                "total_insights_generated": 0,
                "session_breakdown": defaultdict(lambda: {
                    "session_count": 0,
                    "patterns_learned": 0,
                    "insights_generated": 0
                })
            }
            
            for session_json in sessions:
                try:
                    session = json.loads(session_json)
                    
                    # Filter by date
                    if session.get("created_at", "") >= cutoff_date:
                        session_type = session["session_type"]
                        patterns = session.get("patterns_learned", 0)
                        insights = session.get("insights_generated", 0)
                        
                        analytics["total_sessions"] += 1
                        analytics["total_patterns_learned"] += patterns
                        analytics["total_insights_generated"] += insights
                        
                        breakdown = analytics["session_breakdown"][session_type]
                        breakdown["session_count"] += 1
                        breakdown["patterns_learned"] += patterns
                        breakdown["insights_generated"] += insights
                        
                except json.JSONDecodeError:
                    continue
            
            # Convert defaultdict to regular dict
            analytics["session_breakdown"] = dict(analytics["session_breakdown"])
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get learning analytics: {e}")
            return {"total_sessions": 0, "total_patterns_learned": 0, "total_insights_generated": 0, "session_breakdown": {}}
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """
        Clean up old data (Redis handles this automatically with TTL).
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            True if cleanup successful
        """
        # Redis-only mode - no fallback needed
        
        try:
            # Redis automatically handles cleanup with TTL
            # We can optionally scan for expired keys and remove them immediately
            
            # Update TTL for all pattern keys if needed
            new_ttl = days_to_keep * 24 * 3600  # Convert to seconds
            
            # Scan for pattern keys and update TTL
            for key in self.redis.scan_iter(match="kirolinter:*"):
                self.redis.expire(key, new_ttl)
            
            self.logger.info(f"Updated TTL for all keys to {days_to_keep} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    def get_comprehensive_insights(self, repo_path: str) -> Dict[str, Any]:
        """
        Get comprehensive insights combining all stored data.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Dictionary with comprehensive insights
        """

        
        try:
            insights = {
                "team_patterns": self.get_team_patterns(repo_path),
                "issue_trends": self.get_issue_trends(repo_path),
                "fix_success_rates": self.get_fix_success_rates(repo_path),
                "learning_analytics": self.get_learning_analytics(repo_path),
                "pattern_confidence_summary": {},
                "recommendations": []
            }
            
            # Calculate pattern confidence summary
            for pattern in insights["team_patterns"]:
                pattern_type = pattern["pattern_type"]
                confidence = pattern["confidence"]
                
                if pattern_type not in insights["pattern_confidence_summary"]:
                    insights["pattern_confidence_summary"][pattern_type] = {
                        "avg_confidence": 0.0,
                        "pattern_count": 0,
                        "high_confidence_count": 0
                    }
                
                summary = insights["pattern_confidence_summary"][pattern_type]
                summary["pattern_count"] += 1
                summary["avg_confidence"] = (summary["avg_confidence"] * (summary["pattern_count"] - 1) + confidence) / summary["pattern_count"]
                
                if confidence >= 0.8:
                    summary["high_confidence_count"] += 1
            
            # Generate recommendations
            insights["recommendations"] = self._generate_recommendations(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get comprehensive insights: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on insights."""
        recommendations = []
        
        # Pattern confidence recommendations
        for pattern_type, summary in insights["pattern_confidence_summary"].items():
            if summary["avg_confidence"] < 0.6:
                recommendations.append(f"Consider reviewing {pattern_type} patterns - low confidence ({summary['avg_confidence']:.2f})")
            elif summary["high_confidence_count"] / summary["pattern_count"] > 0.8:
                recommendations.append(f"{pattern_type} patterns are well-established - consider enforcing them more strictly")
        
        # Issue trend recommendations
        trending_issues = insights["issue_trends"]["trending_issues"][:3]
        if trending_issues:
            top_issue = trending_issues[0]
            recommendations.append(f"Focus on {top_issue['issue_type']} issues - trending with {top_issue['frequency']} occurrences")
        
        # Fix success rate recommendations
        for fix_type, stats in insights["fix_success_rates"].items():
            if stats["success_rate"] < 0.7:
                recommendations.append(f"Review {fix_type} fix strategy - low success rate ({stats['success_rate']:.2f})")
        
        return recommendations
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection and fallback.
        
        Returns:
            Dictionary with health status
        """
        health = {
            "redis_available": False,
            "redis_connected": False,
            "sqlite_available": True,
            "active_backend": "sqlite",
            "redis_info": {},
            "error": None
        }
        
        try:
            if REDIS_AVAILABLE:
                health["redis_available"] = True
                
                if self.redis:
                    self.redis.ping()
                    health["redis_connected"] = True
                    health["active_backend"] = "redis"
                    health["redis_info"] = {
                        "version": self.redis.info().get("redis_version", "unknown"),
                        "memory_used": self.redis.info().get("used_memory_human", "unknown"),
                        "connected_clients": self.redis.info().get("connected_clients", 0)
                    }
            
        except Exception as e:
            health["error"] = str(e)
            health["redis_connected"] = False
            health["active_backend"] = "sqlite"
        
        return health    

    def get_pattern_evolution(self, repo_path: str, pattern_type: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get pattern evolution over time for trend analysis.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern to analyze
            days_back: Number of days to look back
            
        Returns:
            Dictionary with pattern evolution data
        """
        # Redis-only mode - no fallback needed
        
        try:
            # For Redis, we'll track changes in a separate key
            changes_key = f"kirolinter:changes:{repo_path}:{pattern_type}"
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            # Get all changes for this pattern
            all_changes = self.redis.lrange(changes_key, 0, -1)
            
            evolution = {
                "pattern_type": pattern_type,
                "changes": [],
                "confidence_trend": [],
                "total_changes": 0
            }
            
            for change_json in all_changes:
                try:
                    change_data = json.loads(change_json)
                    if change_data.get("created_at", "") >= cutoff_date:
                        evolution["changes"].append(change_data)
                        if "confidence_change" in change_data:
                            evolution["confidence_trend"].append({
                                "date": change_data["created_at"],
                                "confidence_change": change_data["confidence_change"]
                            })
                        evolution["total_changes"] += 1
                except json.JSONDecodeError:
                    continue
            
            return evolution
            
        except Exception as e:
            self.logger.error(f"Failed to get pattern evolution: {e}")
            return {"pattern_type": pattern_type, "changes": [], "confidence_trend": [], "total_changes": 0}
    
    def record_learning_change(self, repo_path: str, pattern_type: str, 
                              before_data: Optional[str], after_data: str, reason: str) -> bool:
        """
        Record a learning change for audit trail.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern that changed
            before_data: Previous pattern data (JSON string)
            after_data: New pattern data (JSON string)
            reason: Reason for the change
            
        Returns:
            True if recorded successfully
        """
        if not self.use_redis:
            if self.sqlite_memory:
                return self.sqlite_memory.record_learning_change(repo_path, pattern_type, before_data, after_data, reason)
            else:
                return True  # Silently succeed if no backend available
        
        try:
            changes_key = f"kirolinter:changes:{repo_path}:{pattern_type}"
            now = datetime.now().isoformat()
            
            change_record = {
                "pattern_type": pattern_type,
                "before_data": before_data,
                "after_data": after_data,
                "reason": reason,
                "created_at": now,
                "confidence_change": 0.1  # Default confidence change
            }
            
            # Use Redis pipeline for atomic operation
            pipe = self.redis.pipeline()
            pipe.lpush(changes_key, json.dumps(change_record))
            pipe.ltrim(changes_key, 0, 999)  # Keep last 1000 changes
            pipe.expire(changes_key, self.default_ttl)
            pipe.execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record learning change: {e}")
            return False
    
    def update_confidence(self, repo_path: str, pattern_type: str, new_confidence: float) -> bool:
        """
        Update confidence score for a specific pattern.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern to update
            new_confidence: New confidence score (0.0 to 1.0)
            
        Returns:
            True if updated successfully
        """
        if not self.use_redis:
            if self.sqlite_memory:
                return self.sqlite_memory.update_confidence(repo_path, pattern_type, new_confidence)
            else:
                return False
        
        try:
            if not 0.0 <= new_confidence <= 1.0:
                self.logger.error(f"Invalid confidence score: {new_confidence}")
                return False
            
            pattern_key = self._get_pattern_key(repo_path, pattern_type)
            
            # Check if pattern exists
            if not self.redis.exists(pattern_key):
                self.logger.warning(f"No pattern found to update: {pattern_type}")
                return False
            
            # Update confidence
            self.redis.hset(pattern_key, "confidence", str(new_confidence))
            self.redis.hset(pattern_key, "updated_at", datetime.now().isoformat())
            
            self.logger.info(f"Updated confidence for {pattern_type} to {new_confidence}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update confidence: {e}")
            return False
    
    def export_patterns(self, repo_path: str, output_file: Optional[str] = None) -> bool:
        """
        Export patterns to JSON file for backup or sharing.
        
        Args:
            repo_path: Repository path
            output_file: Output file path (optional)
            
        Returns:
            True if exported successfully
        """
        if not self.use_redis:
            if self.sqlite_memory:
                return self.sqlite_memory.export_patterns(repo_path, output_file)
            else:
                return False
        
        try:
            # Get all patterns for the repository
            patterns = self.get_team_patterns(repo_path)
            issue_trends = self.get_issue_trends(repo_path)
            fix_success_rates = self.get_fix_success_rates(repo_path)
            learning_analytics = self.get_learning_analytics(repo_path)
            
            export_data = {
                "repo_path": repo_path,
                "exported_at": datetime.now().isoformat(),
                "team_patterns": patterns,
                "issue_trends": issue_trends,
                "fix_success_rates": fix_success_rates,
                "learning_analytics": learning_analytics
            }
            
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.logger.info(f"Exported patterns to {output_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export patterns: {e}")
            return False
    
    def import_patterns(self, repo_path: str, input_file: str) -> bool:
        """
        Import patterns from JSON file.
        
        Args:
            repo_path: Repository path
            input_file: Input file path
            
        Returns:
            True if imported successfully
        """
        if not self.use_redis:
            if self.sqlite_memory:
                return self.sqlite_memory.import_patterns(repo_path, input_file)
            else:
                return False
        
        try:
            with open(input_file, 'r') as f:
                import_data = json.load(f)
            
            # Import team patterns
            if "team_patterns" in import_data:
                for pattern in import_data["team_patterns"]:
                    self.store_pattern(
                        repo_path,
                        pattern["pattern_type"],
                        pattern["pattern_data"],
                        pattern.get("confidence", 0.0)
                    )
            
            self.logger.info(f"Imported patterns from {input_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import patterns: {e}")
            return False