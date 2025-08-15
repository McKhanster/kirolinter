"""
Pattern Memory for KiroLinter AI Agent System.

This module provides persistent storage and retrieval of learned patterns,
team style preferences, and code analysis insights for the agentic system.
Includes comprehensive data anonymization and security measures.

Now with Redis support for zero-concurrency issues and high performance.
"""

import json
import sqlite3
import re
import hashlib
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from contextlib import contextmanager

# Try to import Redis support
try:
    from .redis_pattern_memory import RedisPatternMemory, REDIS_AVAILABLE
    REDIS_IMPORT_SUCCESS = True
except ImportError:
    REDIS_AVAILABLE = False
    REDIS_IMPORT_SUCCESS = False
    RedisPatternMemory = None


# Import DataAnonymizer from separate module to avoid circular imports
from .anonymizer import DataAnonymizer

# Placeholder class to be removed
class _DataAnonymizer_PLACEHOLDER:
    """Comprehensive data anonymization for pattern storage."""
    
    # Configurable sensitive data patterns
    SENSITIVE_PATTERNS = [
        r'(?i)(password|passwd|pwd|secret|key|token|api_key)\s*[=:]\s*["\']([^"\']+)["\']',
        r'(?i)(bearer|basic)\s+([a-zA-Z0-9+/=]+)',
        r'(?i)(sk-[a-zA-Z0-9]{48})',  # OpenAI API keys
        r'(?i)(xai-[a-zA-Z0-9]{48})',  # xAI API keys
        r'(?i)([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Email addresses
        r'(?i)(https?://[^\s]+)',  # URLs (may contain sensitive info)
        r'(?i)([a-f0-9]{32,})',  # Potential hashes/tokens (moved to end to avoid conflicts)
    ]
    
    # Sensitive file patterns to exclude
    SENSITIVE_FILES = [
        r'\.env.*',
        r'.*secrets.*\.ya?ml',
        r'.*config.*\.json',
        r'.*\.key$',
        r'.*\.pem$',
        r'.*credentials.*',
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def is_sensitive_file(self, file_path: str) -> bool:
        """Check if file contains potentially sensitive information."""
        file_name = Path(file_path).name.lower()
        return any(re.match(pattern, file_name) for pattern in self.SENSITIVE_FILES)
    
    def anonymize_code_snippet(self, code: str) -> str:
        """Anonymize sensitive data in code snippets."""
        if not code:
            return code
            
        anonymized = code
        secrets_found = 0
        
        for pattern in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, anonymized)
            if matches:
                secrets_found += len(matches)
                # Different replacement patterns based on the regex structure
                if 'password|passwd|pwd|secret|key|token|api_key' in pattern:
                    anonymized = re.sub(pattern, r'\1="<REDACTED>"', anonymized)
                elif '@' in pattern:  # Email pattern
                    anonymized = re.sub(pattern, '<REDACTED_EMAIL>', anonymized)
                elif 'https?://' in pattern:  # URL pattern
                    anonymized = re.sub(pattern, '<REDACTED_URL>', anonymized)
                else:
                    anonymized = re.sub(pattern, '<REDACTED>', anonymized)
        
        if secrets_found > 0:
            self.logger.info(f"Anonymized {secrets_found} potential secrets in code snippet")
        
        return anonymized
    
    def anonymize_pattern_data(self, pattern_data: Dict) -> Dict:
        """Anonymize pattern data before storage."""
        if not isinstance(pattern_data, dict):
            return pattern_data
        
        anonymized_data = pattern_data.copy()
        
        # Anonymize code examples
        if 'examples' in anonymized_data:
            anonymized_data['examples'] = [
                self.anonymize_code_snippet(str(example)) 
                for example in anonymized_data['examples']
            ]
        
        # Anonymize code samples
        if 'code_samples' in anonymized_data:
            anonymized_data['code_samples'] = {
                key: self.anonymize_code_snippet(str(value))
                for key, value in anonymized_data['code_samples'].items()
            }
        
        # Anonymize any string values that might contain code
        for key, value in anonymized_data.items():
            if isinstance(value, str) and len(value) > 20:  # Likely code snippet
                anonymized_data[key] = self.anonymize_code_snippet(value)
        
        return anonymized_data
    
    def validate_anonymization(self, data: Dict) -> bool:
        """Validate that data has been properly anonymized."""
        data_str = json.dumps(data)
        
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, data_str):
                self.logger.error(f"Anonymization validation failed: sensitive pattern found")
                return False
        
        return True


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
            # Default to project root for easier access
            self.db_path = Path.cwd() / "kirolinter_memory.db"
        
        self.anonymizer = DataAnonymizer()
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
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
                
                CREATE TABLE IF NOT EXISTS learning_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_id TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    before_data TEXT,
                    after_data TEXT,
                    reason TEXT NOT NULL,
                    confidence_change REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_team_patterns_repo ON team_patterns(repo_path);
                CREATE INDEX IF NOT EXISTS idx_issue_patterns_repo ON issue_patterns(repo_path);
                CREATE INDEX IF NOT EXISTS idx_fix_outcomes_repo ON fix_outcomes(repo_path);
                """)
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            # Create a fallback in-memory database for testing
            self.db_path = ":memory:"
    
    @contextmanager
    def get_transaction(self, retries: int = 3):
        """Get database transaction with automatic rollback on error and retry logic."""
        for attempt in range(retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
                conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
                try:
                    yield conn
                    conn.commit()
                    return
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                raise
    
    def store_pattern(self, repo_path: str, pattern_type: str, 
                     pattern_data: Dict[str, Any], confidence: float = 0.0) -> bool:
        """
        Store a pattern with comprehensive security and error handling.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern (e.g., 'naming', 'imports', 'structure')
            pattern_data: Pattern details and rules
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
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
            
            # Store with transaction safety
            with self.get_transaction() as conn:
                now = datetime.now().isoformat()
                pattern_json = json.dumps(anonymized_data)
                
                # Check if pattern already exists
                cursor = conn.execute("""
                    SELECT id, pattern_data, confidence FROM team_patterns 
                    WHERE repo_path = ? AND pattern_type = ?
                """, (repo_path, pattern_type))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing pattern
                    old_confidence = existing[2]
                    conn.execute("""
                        UPDATE team_patterns 
                        SET pattern_data = ?, confidence = ?, frequency = frequency + 1, updated_at = ?
                        WHERE repo_path = ? AND pattern_type = ?
                    """, (pattern_json, confidence, now, repo_path, pattern_type))
                    
                    # Log the change
                    self.record_learning_change(
                        repo_path, pattern_type, existing[1], pattern_json, 
                        f"Updated pattern confidence from {old_confidence} to {confidence}"
                    )
                else:
                    # Insert new pattern
                    conn.execute("""
                        INSERT INTO team_patterns 
                        (repo_path, pattern_type, pattern_name, pattern_data, confidence, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (repo_path, pattern_type, pattern_type, pattern_json, confidence, now, now))
                    
                    # Log the creation
                    self.record_learning_change(
                        repo_path, pattern_type, None, pattern_json, 
                        f"Created new pattern with confidence {confidence}"
                    )
                
                self.logger.info(f"Successfully stored pattern: {pattern_type} for {repo_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            return False
    
    def store_team_pattern(self, repo_path: str, pattern_type: str, 
                          pattern_name: str, pattern_data: Dict[str, Any],
                          confidence: float = 0.0) -> bool:
        """
        Store or update a team coding pattern (legacy method for compatibility).
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern (e.g., 'naming', 'imports', 'structure')
            pattern_name: Specific pattern name (e.g., 'variable_naming')
            pattern_data: Pattern details and rules
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
        # Use the enhanced store_pattern method
        enhanced_data = pattern_data.copy()
        enhanced_data['pattern_name'] = pattern_name
        return self.store_pattern(repo_path, pattern_type, enhanced_data, confidence)
    
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
    
    def record_learning_change(self, repo_path: str, pattern_type: str, 
                              before_data: Optional[str], after_data: str, reason: str) -> bool:
        """
        Record a learning change for audit and analysis purposes.
        
        Args:
            repo_path: Repository path
            pattern_type: Type of pattern that changed
            before_data: Previous pattern data (None for new patterns)
            after_data: New pattern data
            reason: Reason for the change
            
        Returns:
            True if recorded successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                change_id = hashlib.md5(f"{repo_path}_{pattern_type}_{datetime.now().isoformat()}".encode()).hexdigest()
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT INTO learning_history 
                    (change_id, repo_path, before_data, after_data, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (change_id, repo_path, before_data, after_data, reason, now))
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to record learning change: {e}")
            return False
    
    def retrieve_patterns(self, repo_path: str, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve patterns for a repository (simplified method for compatibility).
        
        Args:
            repo_path: Repository path
            pattern_type: Optional filter by pattern type
            
        Returns:
            List of matching patterns
        """
        return self.get_team_patterns(repo_path, pattern_type)
    
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
        try:
            if not 0.0 <= new_confidence <= 1.0:
                self.logger.error(f"Invalid confidence score: {new_confidence}")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE team_patterns 
                    SET confidence = ?, updated_at = ?
                    WHERE repo_path = ? AND pattern_type = ?
                """, (new_confidence, datetime.now().isoformat(), repo_path, pattern_type))
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Updated confidence for {pattern_type} to {new_confidence}")
                    return True
                else:
                    self.logger.warning(f"No pattern found to update: {pattern_type}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to update confidence: {e}")
            return False
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize data (public method for external use).
        
        Args:
            data: Data to anonymize
            
        Returns:
            Anonymized data
        """
        return self.anonymizer.anonymize_pattern_data(data)
    
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
                
                # Clean up old learning history
                conn.execute("DELETE FROM learning_history WHERE created_at < ?", (cutoff_date,))
                
                self.logger.info(f"Cleaned up data older than {days_to_keep} days")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return False
    
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
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                cursor = conn.execute("""
                    SELECT before_data, after_data, reason, confidence_change, created_at
                    FROM learning_history 
                    WHERE repo_path = ? AND change_id LIKE ? AND created_at >= ?
                    ORDER BY created_at ASC
                """, (repo_path, f"%{pattern_type}%", cutoff_date))
                
                evolution = {
                    "pattern_type": pattern_type,
                    "changes": [],
                    "confidence_trend": [],
                    "total_changes": 0
                }
                
                for row in cursor.fetchall():
                    change_data = dict(row)
                    evolution["changes"].append(change_data)
                    evolution["confidence_trend"].append({
                        "date": change_data["created_at"],
                        "confidence_change": change_data["confidence_change"]
                    })
                    evolution["total_changes"] += 1
                
                return evolution
                
        except Exception as e:
            self.logger.error(f"Failed to get pattern evolution: {e}")
            return {"pattern_type": pattern_type, "changes": [], "confidence_trend": [], "total_changes": 0}
    
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
    
    def export_patterns(self, repo_path: str, output_file: Optional[str] = None) -> bool:
        """
        Export patterns to JSON file for backup or sharing.
        
        Args:
            repo_path: Repository path
            output_file: Optional output file path
            
        Returns:
            True if export successful
        """
        try:
            insights = self.get_comprehensive_insights(repo_path)
            
            if output_file is None:
                output_file = f"kirolinter_patterns_{repo_path.replace('/', '_')}.json"
            
            # Ensure all data is anonymized before export
            anonymized_insights = self.anonymizer.anonymize_pattern_data(insights)
            
            # Validate anonymization
            if not self.anonymizer.validate_anonymization(anonymized_insights):
                self.logger.error("Export failed - anonymization validation failed")
                return False
            
            with open(output_file, 'w') as f:
                json.dump(anonymized_insights, f, indent=2, default=str)
            
            self.logger.info(f"Patterns exported to {output_file}")
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
            True if import successful
        """
        try:
            with open(input_file, 'r') as f:
                imported_data = json.load(f)
            
            # Import team patterns
            if "team_patterns" in imported_data:
                for pattern in imported_data["team_patterns"]:
                    self.store_pattern(
                        repo_path,
                        pattern["pattern_type"],
                        pattern["pattern_data"],
                        pattern["confidence"]
                    )
            
            self.logger.info(f"Patterns imported from {input_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import patterns: {e}")
            return False

def create_pattern_memory(redis_url: Optional[str] = None, 
                         redis_only: bool = True,
                         **kwargs) -> 'RedisPatternMemory':
    """
    Factory function to create Redis-only PatternMemory.
    
    Args:
        redis_url: Redis connection URL (default: redis://localhost:6379)
        redis_only: Must be True (Redis-only mode)
        **kwargs: Ignored (for backward compatibility)
        
    Returns:
        RedisPatternMemory instance
    """
    if not redis_only:
        raise Exception("Only Redis-only mode is supported")
    
    if not REDIS_AVAILABLE or not REDIS_IMPORT_SUCCESS:
        raise Exception("Redis-only mode requested but Redis not available")
    
    try:
        return RedisPatternMemory(redis_url=redis_url or "redis://localhost:6379")
    except Exception as e:
        # If Redis connection fails, treat it as Redis not available
        raise Exception("Redis-only mode requested but Redis not available")