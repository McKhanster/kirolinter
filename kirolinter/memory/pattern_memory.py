"""
Pattern Memory for KiroLinter AI Agent System.

This module provides persistent storage and retrieval of learned patterns,
team style preferences, and code analysis insights for the agentic system.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import hashlib


class PatternMemory:
    """
    Persistent memory system for storing and retrieving learned patterns.
    
    Features:
    - Stores team coding style preferences
    - Tracks issue patterns and frequencies
    - Maintains fix success rates
    - Supports pattern evolution over time
    - Provides confidence scoring for patterns
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize pattern memory with SQLite backend.
        
        Args:
            db_path: Optional path to SQLite database file
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default to .kiro directory
            kiro_dir = Path.cwd() / ".kiro" / "agent_memory"
            kiro_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = kiro_dir / "pattern_memory.db"
        
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS team_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_path TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    frequency INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(repo_path, pattern_type, pattern_name)
                );
                
                CREATE TABLE IF NOT EXISTS issue_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_path TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    issue_rule TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    severity TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    trend_score REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    UNIQUE(repo_path, issue_type, issue_rule)
                );
                
                CREATE TABLE IF NOT EXISTS fix_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_path TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    fix_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    applied_at TEXT NOT NULL,
                    feedback_score REAL DEFAULT 0.0,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_path TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    patterns_learned INTEGER DEFAULT 0,
                    insights_generated INTEGER DEFAULT 0,
                    session_data TEXT,
                    created_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_team_patterns_repo ON team_patterns(repo_path);
                CREATE INDEX IF NOT EXISTS idx_issue_patterns_repo ON issue_patterns(repo_path);
                CREATE INDEX IF NOT EXISTS idx_fix_outcomes_repo ON fix_outcomes(repo_path);
            """)
    
    def store_team_pattern(self, repo_path: str, pattern_type: str, 
                          pattern_name: str, pattern_data: Dict[str, Any],
                          confidence: float = 0.0) -> bool:
        """
        Store or update a team coding pattern.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern (e.g., 'naming', 'imports', 'structure')
            pattern_name: Specific pattern name (e.g., 'variable_naming')
            pattern_data: Pattern details and rules
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                
                # Try to update existing pattern
                cursor = conn.execute("""
                    UPDATE team_patterns 
                    SET pattern_data = ?, confidence = ?, frequency = frequency + 1, updated_at = ?
                    WHERE repo_path = ? AND pattern_type = ? AND pattern_name = ?
                """, (json.dumps(pattern_data), confidence, now, repo_path, pattern_type, pattern_name))
                
                # If no rows updated, insert new pattern
                if cursor.rowcount == 0:
                    conn.execute("""
                        INSERT INTO team_patterns 
                        (repo_path, pattern_type, pattern_name, pattern_data, confidence, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (repo_path, pattern_type, pattern_name, json.dumps(pattern_data), confidence, now, now))
                
                return True
                
        except Exception as e:
            print(f"Failed to store team pattern: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT * FROM team_patterns 
                    WHERE repo_path = ? AND confidence >= ?
                """
                params = [repo_path, min_confidence]
                
                if pattern_type:
                    query += " AND pattern_type = ?"
                    params.append(pattern_type)
                
                query += " ORDER BY confidence DESC, frequency DESC"
                
                cursor = conn.execute(query, params)
                patterns = []
                
                for row in cursor.fetchall():
                    pattern = dict(row)
                    pattern['pattern_data'] = json.loads(pattern['pattern_data'])
                    patterns.append(pattern)
                
                return patterns
                
        except Exception as e:
            print(f"Failed to retrieve team patterns: {e}")
            return []
    
    def track_issue_pattern(self, repo_path: str, issue_type: str, 
                           issue_rule: str, severity: str) -> bool:
        """
        Track occurrence of an issue pattern.
        
        Args:
            repo_path: Repository path
            issue_type: Type of issue (e.g., 'style', 'security', 'performance')
            issue_rule: Specific rule that triggered (e.g., 'E501', 'unused_import')
            severity: Issue severity level
            
        Returns:
            True if tracked successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                
                # Try to update existing issue pattern
                cursor = conn.execute("""
                    UPDATE issue_patterns 
                    SET frequency = frequency + 1, last_seen = ?, trend_score = trend_score + 0.1
                    WHERE repo_path = ? AND issue_type = ? AND issue_rule = ?
                """, (now, repo_path, issue_type, issue_rule))
                
                # If no rows updated, insert new issue pattern
                if cursor.rowcount == 0:
                    conn.execute("""
                        INSERT INTO issue_patterns 
                        (repo_path, issue_type, issue_rule, severity, last_seen, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (repo_path, issue_type, issue_rule, severity, now, now))
                
                return True
                
        except Exception as e:
            print(f"Failed to track issue pattern: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                cursor = conn.execute("""
                    SELECT issue_type, issue_rule, severity, frequency, trend_score, last_seen
                    FROM issue_patterns 
                    WHERE repo_path = ? AND last_seen >= ?
                    ORDER BY trend_score DESC, frequency DESC
                    LIMIT 20
                """, (repo_path, cutoff_date))
                
                trends = {
                    "trending_issues": [],
                    "issue_distribution": Counter(),
                    "severity_distribution": Counter(),
                    "total_patterns": 0
                }
                
                for row in cursor.fetchall():
                    issue_data = dict(row)
                    trends["trending_issues"].append(issue_data)
                    trends["issue_distribution"][issue_data["issue_type"]] += issue_data["frequency"]
                    trends["severity_distribution"][issue_data["severity"]] += issue_data["frequency"]
                    trends["total_patterns"] += 1
                
                return trends
                
        except Exception as e:
            print(f"Failed to get issue trends: {e}")
            return {"trending_issues": [], "issue_distribution": {}, "severity_distribution": {}, "total_patterns": 0}
    
    def record_fix_outcome(self, repo_path: str, issue_type: str, fix_type: str,
                          success: bool, feedback_score: float = 0.0,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record the outcome of an applied fix.
        
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
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT INTO fix_outcomes 
                    (repo_path, issue_type, fix_type, success, applied_at, feedback_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (repo_path, issue_type, fix_type, success, now, feedback_score, 
                     json.dumps(metadata) if metadata else None))
                
                return True
                
        except Exception as e:
            print(f"Failed to record fix outcome: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT fix_type, 
                           COUNT(*) as total_attempts,
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_fixes,
                           AVG(feedback_score) as avg_feedback
                    FROM fix_outcomes 
                    WHERE repo_path = ?
                    GROUP BY fix_type
                    ORDER BY successful_fixes DESC
                """, (repo_path,))
                
                success_rates = {}
                for row in cursor.fetchall():
                    fix_type, total, successful, avg_feedback = row
                    success_rates[fix_type] = {
                        "total_attempts": total,
                        "successful_fixes": successful,
                        "success_rate": successful / total if total > 0 else 0.0,
                        "avg_feedback": avg_feedback or 0.0
                    }
                
                return success_rates
                
        except Exception as e:
            print(f"Failed to get fix success rates: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT INTO learning_sessions 
                    (repo_path, session_type, patterns_learned, insights_generated, session_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (repo_path, session_type, patterns_learned, insights_generated,
                     json.dumps(session_data) if session_data else None, now))
                
                return True
                
        except Exception as e:
            print(f"Failed to record learning session: {e}")
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
            with sqlite3.connect(self.db_path) as conn:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                cursor = conn.execute("""
                    SELECT session_type, 
                           COUNT(*) as session_count,
                           SUM(patterns_learned) as total_patterns,
                           SUM(insights_generated) as total_insights
                    FROM learning_sessions 
                    WHERE repo_path = ? AND created_at >= ?
                    GROUP BY session_type
                """, (repo_path, cutoff_date))
                
                analytics = {
                    "total_sessions": 0,
                    "total_patterns_learned": 0,
                    "total_insights_generated": 0,
                    "session_breakdown": {}
                }
                
                for row in cursor.fetchall():
                    session_type, count, patterns, insights = row
                    analytics["session_breakdown"][session_type] = {
                        "session_count": count,
                        "patterns_learned": patterns,
                        "insights_generated": insights
                    }
                    analytics["total_sessions"] += count
                    analytics["total_patterns_learned"] += patterns or 0
                    analytics["total_insights_generated"] += insights or 0
                
                return analytics
                
        except Exception as e:
            print(f"Failed to get learning analytics: {e}")
            return {"total_sessions": 0, "total_patterns_learned": 0, "total_insights_generated": 0, "session_breakdown": {}}
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """
        Clean up old data to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            True if cleanup successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                # Clean up old fix outcomes
                conn.execute("DELETE FROM fix_outcomes WHERE applied_at < ?", (cutoff_date,))
                
                # Clean up old learning sessions
                conn.execute("DELETE FROM learning_sessions WHERE created_at < ?", (cutoff_date,))
                
                # Update trend scores (decay over time)
                conn.execute("""
                    UPDATE issue_patterns 
                    SET trend_score = trend_score * 0.9 
                    WHERE last_seen < ?
                """, (cutoff_date,))
                
                return True
                
        except Exception as e:
            print(f"Failed to cleanup old data: {e}")
            return False
    
    def export_patterns(self, repo_path: str, export_path: str) -> bool:
        """
        Export learned patterns to a JSON file.
        
        Args:
            repo_path: Repository path
            export_path: Path to export file
            
        Returns:
            True if export successful
        """
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "repo_path": repo_path,
                "team_patterns": self.get_team_patterns(repo_path),
                "issue_trends": self.get_issue_trends(repo_path),
                "fix_success_rates": self.get_fix_success_rates(repo_path),
                "learning_analytics": self.get_learning_analytics(repo_path)
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Failed to export patterns: {e}")
            return False