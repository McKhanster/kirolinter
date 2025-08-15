"""
Cross-Repository Learner for KiroLinter AI Agent System.

The Cross-Repository Learner enables pattern sharing, similarity detection,
and community-driven learning across multiple repositories while maintaining
privacy and security.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from ..agents.learner import LearnerAgent
from ..memory.pattern_memory import PatternMemory


class CrossRepoLearner:
    """
    Cross-repository learning system for pattern sharing and knowledge transfer.
    
    The CrossRepoLearner:
    - Shares patterns safely between repositories
    - Detects repository similarity for pattern transfer
    - Implements privacy-preserving pattern learning
    - Provides pattern marketplace functionality
    """
    
    def __init__(self, memory: PatternMemory, verbose: bool = False):
        """
        Initialize the Cross-Repository Learner.
        
        Args:
            memory: PatternMemory instance (Redis-based)
            verbose: Enable verbose logging
        """
        self.memory = memory
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        
        # Initialize learner agent for pattern analysis
        self.learner = LearnerAgent(memory=memory, verbose=verbose)
        
        # Initialize ML components if available
        if ML_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            if verbose:
                print("🤖 Cross-repo ML components initialized")
        else:
            self.vectorizer = None
            if verbose:
                print("⚠️ ML libraries not available - using statistical analysis")
        
        # Privacy and security patterns
        self.sensitive_patterns = [
            r'password\s*=',
            r'api[_-]?key\s*=',
            r'secret\s*=',
            r'token\s*=',
            r'auth[_-]?key\s*=',
            r'private[_-]?key',
            r'access[_-]?token',
            r'client[_-]?secret',
            r'database[_-]?url',
            r'connection[_-]?string',
            r'\.env',
            r'config\.py',
            r'settings\.py',
            r'credentials',
            r'localhost',
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email addresses
        ]
        
        # Compile regex patterns for efficiency
        self.sensitive_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns]
    
    def share_patterns(self, source_repo: str, target_repo: str, pattern_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Share patterns from source repository to target repository with privacy checks.
        
        Args:
            source_repo: Source repository path
            target_repo: Target repository path
            pattern_types: Optional list of pattern types to share (default: all safe patterns)
            
        Returns:
            Dictionary with sharing results and statistics
        """
        try:
            if self.verbose:
                print(f"🔄 Sharing patterns from {source_repo} to {target_repo}")
            
            # Default pattern types to share
            if pattern_types is None:
                pattern_types = ["code_pattern", "naming_conventions", "import_styles", "code_structure"]
            
            patterns_shared = 0
            patterns_rejected = 0
            shared_patterns = []
            
            for pattern_type in pattern_types:
                # Retrieve patterns from source repository
                source_patterns = self.memory.retrieve_patterns(source_repo, pattern_type)
                
                if not source_patterns:
                    continue
                
                for pattern in source_patterns:
                    # Check if pattern is safe to share
                    if self._is_safe_to_share(pattern):
                        # Create shared pattern with metadata
                        shared_pattern = self._create_shared_pattern(pattern, source_repo, target_repo)
                        
                        # Store in target repository
                        success = self.memory.store_pattern(
                            target_repo, 
                            "shared_pattern", 
                            shared_pattern, 
                            pattern.get("quality_score", 0.8)
                        )
                        
                        if success:
                            patterns_shared += 1
                            shared_patterns.append({
                                "type": pattern_type,
                                "quality_score": pattern.get("quality_score", 0.8),
                                "source": source_repo
                            })
                            
                            if self.verbose and patterns_shared <= 3:  # Show first few
                                print(f"   ✅ Shared {pattern_type} pattern (quality: {pattern.get('quality_score', 0.8):.2f})")
                        else:
                            patterns_rejected += 1
                    else:
                        patterns_rejected += 1
                        if self.verbose:
                            print(f"   🚫 Rejected unsafe pattern from {pattern_type}")
            
            # Record sharing session
            sharing_data = {
                "source_repo": source_repo,
                "target_repo": target_repo,
                "patterns_shared": patterns_shared,
                "patterns_rejected": patterns_rejected,
                "pattern_types": pattern_types,
                "sharing_timestamp": datetime.now().isoformat()
            }
            
            self.memory.store_pattern(
                target_repo, "sharing_session", sharing_data, 1.0
            )
            
            if self.verbose:
                print(f"📊 Shared {patterns_shared} patterns, rejected {patterns_rejected}")
            
            return {
                "patterns_shared": patterns_shared,
                "patterns_rejected": patterns_rejected,
                "shared_patterns": shared_patterns,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to share patterns: {e}")
            return {
                "patterns_shared": 0,
                "patterns_rejected": 0,
                "shared_patterns": [],
                "success": False,
                "error": str(e)
            }
    
    def _is_safe_to_share(self, pattern: Dict[str, Any]) -> bool:
        """
        Check if a pattern is safe to share (no sensitive data).
        
        Args:
            pattern: Pattern dictionary to check
            
        Returns:
            True if pattern is safe to share, False otherwise
        """
        try:
            # Get pattern content to analyze
            content_fields = ["snippet", "description", "example", "code"]
            content_to_check = []
            
            for field in content_fields:
                if field in pattern and isinstance(pattern[field], str):
                    content_to_check.append(pattern[field].lower())
            
            # Check all content against sensitive patterns
            for content in content_to_check:
                for regex in self.sensitive_regex:
                    if regex.search(content):
                        if self.verbose:
                            print(f"   🔒 Pattern contains sensitive data: {regex.pattern}")
                        return False
            
            # Additional checks for specific pattern types
            if pattern.get("type") == "file_path" and any(
                sensitive in str(pattern).lower() 
                for sensitive in ["secret", "key", "password", "token", "config", ".env"]
            ):
                return False
            
            # Check for hardcoded values that might be sensitive
            if "=" in str(pattern) and any(
                keyword in str(pattern).lower() 
                for keyword in ["password", "key", "secret", "token"]
            ):
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error checking pattern safety: {e}")
            return False  # Err on the side of caution
    
    def _create_shared_pattern(self, pattern: Dict[str, Any], source_repo: str, target_repo: str) -> Dict[str, Any]:
        """
        Create a shared pattern with appropriate metadata and anonymization.
        
        Args:
            pattern: Original pattern to share
            source_repo: Source repository path
            target_repo: Target repository path
            
        Returns:
            Anonymized shared pattern with metadata
        """
        # Create a copy to avoid modifying original
        shared_pattern = pattern.copy()
        
        # Add sharing metadata
        shared_pattern.update({
            "shared_from": source_repo,
            "shared_to": target_repo,
            "sharing_timestamp": datetime.now().isoformat(),
            "is_shared_pattern": True,
            "original_quality_score": pattern.get("quality_score", 0.8)
        })
        
        # Anonymize sensitive fields if they exist
        if "snippet" in shared_pattern:
            shared_pattern["snippet"] = self._anonymize_content(shared_pattern["snippet"])
        
        if "description" in shared_pattern:
            shared_pattern["description"] = self._anonymize_content(shared_pattern["description"])
        
        # Remove potentially sensitive metadata
        sensitive_keys = ["file_path", "absolute_path", "user", "author", "commit_hash"]
        for key in sensitive_keys:
            shared_pattern.pop(key, None)
        
        return shared_pattern
    
    def _anonymize_content(self, content: str) -> str:
        """
        Anonymize content by replacing sensitive patterns with placeholders.
        
        Args:
            content: Content to anonymize
            
        Returns:
            Anonymized content
        """
        anonymized = content
        
        # Replace common sensitive patterns
        replacements = {
            r'password\s*=\s*["\'][^"\']+["\']': 'password="[REDACTED]"',
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']': 'api_key="[REDACTED]"',
            r'secret\s*=\s*["\'][^"\']+["\']': 'secret="[REDACTED]"',
            r'token\s*=\s*["\'][^"\']+["\']': 'token="[REDACTED]"',
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}': '[IP_ADDRESS]',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}': '[EMAIL]',
            r'/home/[^/\s]+': '/home/[USER]',
            r'/Users/[^/\s]+': '/Users/[USER]',
        }
        
        for pattern, replacement in replacements.items():
            anonymized = re.sub(pattern, replacement, anonymized, flags=re.IGNORECASE)
        
        return anonymized
    
    def detect_repo_similarity(self, repo_a: str, repo_b: str) -> float:
        """
        Detect similarity between two repositories based on their patterns.
        
        Args:
            repo_a: First repository path
            repo_b: Second repository path
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            if self.verbose:
                print(f"🔍 Detecting similarity between {repo_a} and {repo_b}")
            
            # Retrieve patterns from both repositories
            patterns_a = self._get_repo_patterns(repo_a)
            patterns_b = self._get_repo_patterns(repo_b)
            
            if not patterns_a or not patterns_b:
                if self.verbose:
                    print("⚠️ Insufficient patterns for similarity analysis")
                return 0.0
            
            # Use ML-based similarity if available
            if ML_AVAILABLE and self.vectorizer:
                similarity = self._calculate_ml_similarity(patterns_a, patterns_b)
            else:
                similarity = self._calculate_statistical_similarity(patterns_a, patterns_b)
            
            # Store similarity result
            similarity_data = {
                "repo_a": repo_a,
                "repo_b": repo_b,
                "similarity_score": similarity,
                "patterns_a_count": len(patterns_a),
                "patterns_b_count": len(patterns_b),
                "analysis_timestamp": datetime.now().isoformat(),
                "method": "ml" if ML_AVAILABLE else "statistical"
            }
            
            self.memory.store_pattern(
                repo_a, "repo_similarity", similarity_data, similarity
            )
            
            if self.verbose:
                print(f"📊 Repository similarity: {similarity:.3f}")
            
            return similarity
            
        except Exception as e:
            self.logger.error(f"Failed to detect repository similarity: {e}")
            return 0.0
    
    def _get_repo_patterns(self, repo_path: str) -> List[str]:
        """
        Get all pattern snippets from a repository for similarity analysis.
        
        Args:
            repo_path: Repository path
            
        Returns:
            List of pattern snippets
        """
        pattern_types = ["code_pattern", "naming_conventions", "import_styles", "code_structure"]
        all_snippets = []
        
        for pattern_type in pattern_types:
            patterns = self.memory.retrieve_patterns(repo_path, pattern_type)
            
            for pattern in patterns:
                # Extract text content for analysis
                if "snippet" in pattern:
                    all_snippets.append(pattern["snippet"])
                elif "description" in pattern:
                    all_snippets.append(pattern["description"])
                elif isinstance(pattern, str):
                    all_snippets.append(pattern)
        
        return all_snippets
    
    def _calculate_ml_similarity(self, patterns_a: List[str], patterns_b: List[str]) -> float:
        """
        Calculate similarity using ML-based vectorization and cosine similarity.
        
        Args:
            patterns_a: Patterns from first repository
            patterns_b: Patterns from second repository
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Combine all patterns for vectorization
            all_patterns = patterns_a + patterns_b
            
            if len(all_patterns) < 2:
                return 0.0
            
            # Vectorize patterns
            vectors = self.vectorizer.fit_transform(all_patterns).toarray()
            
            # Split vectors back
            vectors_a = vectors[:len(patterns_a)]
            vectors_b = vectors[len(patterns_a):]
            
            if len(vectors_a) == 0 or len(vectors_b) == 0:
                return 0.0
            
            # Calculate average similarity between all pattern pairs
            similarities = []
            for vec_a in vectors_a:
                for vec_b in vectors_b:
                    sim = cosine_similarity([vec_a], [vec_b])[0][0]
                    similarities.append(sim)
            
            # Return average similarity
            avg_similarity = np.mean(similarities) if similarities else 0.0
            return float(avg_similarity)
            
        except Exception as e:
            self.logger.debug(f"ML similarity calculation failed: {e}")
            return self._calculate_statistical_similarity(patterns_a, patterns_b)
    
    def _calculate_statistical_similarity(self, patterns_a: List[str], patterns_b: List[str]) -> float:
        """
        Fallback statistical similarity calculation.
        
        Args:
            patterns_a: Patterns from first repository
            patterns_b: Patterns from second repository
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Simple word-based similarity
            words_a = set()
            words_b = set()
            
            for pattern in patterns_a:
                words_a.update(pattern.lower().split())
            
            for pattern in patterns_b:
                words_b.update(pattern.lower().split())
            
            if not words_a or not words_b:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(words_a.intersection(words_b))
            union = len(words_a.union(words_b))
            
            similarity = intersection / union if union > 0 else 0.0
            return similarity
            
        except Exception as e:
            self.logger.debug(f"Statistical similarity calculation failed: {e}")
            return 0.0
    
    def pattern_marketplace(self, repo_path: str, community_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Integrate community patterns from a pattern marketplace.
        
        Args:
            repo_path: Target repository path
            community_patterns: List of community-contributed patterns
            
        Returns:
            Dictionary with integration results
        """
        try:
            if self.verbose:
                print(f"🏪 Integrating {len(community_patterns)} community patterns into {repo_path}")
            
            patterns_integrated = 0
            patterns_rejected = 0
            integrated_patterns = []
            
            for pattern in community_patterns:
                # Validate pattern safety and quality
                if self._is_safe_to_share(pattern) and self._is_quality_pattern(pattern):
                    # Create community pattern with metadata
                    community_pattern = self._create_community_pattern(pattern, repo_path)
                    
                    # Store pattern
                    quality_score = pattern.get("quality_score", 0.8)
                    success = self.memory.store_pattern(
                        repo_path, "community_pattern", community_pattern, quality_score
                    )
                    
                    if success:
                        patterns_integrated += 1
                        integrated_patterns.append({
                            "type": pattern.get("type", "unknown"),
                            "quality_score": quality_score,
                            "source": pattern.get("source", "community")
                        })
                        
                        if self.verbose and patterns_integrated <= 3:  # Show first few
                            print(f"   ✅ Integrated community pattern (quality: {quality_score:.2f})")
                    else:
                        patterns_rejected += 1
                else:
                    patterns_rejected += 1
                    if self.verbose:
                        print("   🚫 Rejected unsafe or low-quality community pattern")
            
            # Record marketplace integration
            marketplace_data = {
                "repo_path": repo_path,
                "patterns_integrated": patterns_integrated,
                "patterns_rejected": patterns_rejected,
                "total_offered": len(community_patterns),
                "integration_timestamp": datetime.now().isoformat()
            }
            
            self.memory.store_pattern(
                repo_path, "marketplace_integration", marketplace_data, 1.0
            )
            
            if self.verbose:
                print(f"📊 Integrated {patterns_integrated} patterns, rejected {patterns_rejected}")
            
            return {
                "patterns_integrated": patterns_integrated,
                "patterns_rejected": patterns_rejected,
                "integrated_patterns": integrated_patterns,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to integrate community patterns: {e}")
            return {
                "patterns_integrated": 0,
                "patterns_rejected": 0,
                "integrated_patterns": [],
                "success": False,
                "error": str(e)
            }
    
    def _is_quality_pattern(self, pattern: Dict[str, Any]) -> bool:
        """
        Check if a pattern meets quality standards for integration.
        
        Args:
            pattern: Pattern to evaluate
            
        Returns:
            True if pattern meets quality standards
        """
        try:
            # Check minimum quality score
            quality_score = pattern.get("quality_score", 0.0)
            if quality_score < 0.6:  # Minimum quality threshold
                return False
            
            # Check for required fields
            required_fields = ["type"]
            if not all(field in pattern for field in required_fields):
                return False
            
            # Check pattern has meaningful content
            content_fields = ["snippet", "description", "example"]
            has_content = any(
                field in pattern and isinstance(pattern[field], str) and len(pattern[field].strip()) > 10
                for field in content_fields
            )
            
            if not has_content:
                return False
            
            # Additional quality checks based on pattern type
            pattern_type = pattern.get("type", "")
            
            if pattern_type == "code_pattern":
                # Code patterns should have actual code
                snippet = pattern.get("snippet", "")
                if not any(keyword in snippet for keyword in ["def ", "class ", "import ", "from ", "if ", "for "]):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error checking pattern quality: {e}")
            return False
    
    def _create_community_pattern(self, pattern: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """
        Create a community pattern with appropriate metadata.
        
        Args:
            pattern: Original community pattern
            repo_path: Target repository path
            
        Returns:
            Community pattern with metadata
        """
        # Create a copy to avoid modifying original
        community_pattern = pattern.copy()
        
        # Add community metadata
        community_pattern.update({
            "integrated_to": repo_path,
            "integration_timestamp": datetime.now().isoformat(),
            "is_community_pattern": True,
            "original_source": pattern.get("source", "community"),
            "community_rating": pattern.get("rating", 0.8)
        })
        
        # Anonymize content for safety
        if "snippet" in community_pattern:
            community_pattern["snippet"] = self._anonymize_content(community_pattern["snippet"])
        
        if "description" in community_pattern:
            community_pattern["description"] = self._anonymize_content(community_pattern["description"])
        
        return community_pattern
    
    def get_cross_repo_insights(self, repo_path: str) -> Dict[str, Any]:
        """
        Get insights from cross-repository learning activities.
        
        Args:
            repo_path: Repository path to analyze
            
        Returns:
            Dictionary with cross-repository insights
        """
        try:
            insights = {
                "shared_patterns_received": 0,
                "shared_patterns_given": 0,
                "community_patterns_integrated": 0,
                "similar_repositories": [],
                "learning_opportunities": []
            }
            
            # Count shared patterns received
            shared_patterns = self.memory.retrieve_patterns(repo_path, "shared_pattern")
            insights["shared_patterns_received"] = len(shared_patterns)
            
            # Count community patterns integrated
            community_patterns = self.memory.retrieve_patterns(repo_path, "community_pattern")
            insights["community_patterns_integrated"] = len(community_patterns)
            
            # Get sharing sessions (patterns given)
            sharing_sessions = self.memory.retrieve_patterns(repo_path, "sharing_session")
            insights["shared_patterns_given"] = sum(
                session.get("patterns_shared", 0) for session in sharing_sessions
            )
            
            # Get similar repositories
            similarity_data = self.memory.retrieve_patterns(repo_path, "repo_similarity")
            for sim in similarity_data:
                if sim.get("similarity_score", 0) > 0.7:  # High similarity threshold
                    insights["similar_repositories"].append({
                        "repo": sim.get("repo_b", "unknown"),
                        "similarity": sim.get("similarity_score", 0)
                    })
            
            # Generate learning opportunities
            if insights["shared_patterns_received"] == 0:
                insights["learning_opportunities"].append("Consider sharing patterns with similar repositories")
            
            if insights["community_patterns_integrated"] == 0:
                insights["learning_opportunities"].append("Explore community pattern marketplace")
            
            if len(insights["similar_repositories"]) > 0:
                insights["learning_opportunities"].append("Learn from similar repositories")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get cross-repo insights: {e}")
            return {
                "shared_patterns_received": 0,
                "shared_patterns_given": 0,
                "community_patterns_integrated": 0,
                "similar_repositories": [],
                "learning_opportunities": ["Unable to analyze cross-repo data"]
            }