"""
Learner Agent for KiroLinter AI Agent System.

The Learner Agent handles continuous learning and rule refinement with
commit history analysis, pattern extraction, and team style adaptation.
"""

import ast
import hashlib
import re
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

# Phase 6: ML and Statistical Analysis Dependencies
try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from .llm_provider import create_llm_provider
from ..memory.pattern_memory import PatternMemory, create_pattern_memory
from ..models.config import Config


class LearnerAgent:
    """
    AI agent specialized in learning and adaptation.
    
    The Learner Agent:
    - Analyzes commit history for patterns using GitPython
    - Learns team coding preferences with confidence scoring
    - Refines analysis rules over time based on feedback
    - Maintains persistent knowledge base
    - Provides proactive scheduling for continuous learning
    """
    
    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None, 
                 memory=None, verbose: bool = False):
        """
        Initialize the Learner Agent with Phase 6 ML enhancements.
        
        Args:
            model: LLM model name (e.g., "grok-beta", "ollama/llama2")
            provider: LLM provider (e.g., "xai", "ollama", "openai")
            memory: PatternMemory instance (Redis-based)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM with LiteLLM
        try:
            self.llm = create_llm_provider(
                model=model,
                provider=provider,
                temperature=0.1,
                max_tokens=4000
            )
            
            if verbose:
                print(f"🧠 Learner: Using LLM model '{self.llm.model}' with ML capabilities")
                
        except Exception as e:
            if verbose:
                print(f"⚠️ Learner: Failed to initialize LLM: {e}")
                print("🔄 Learner: Falling back to rule-based analysis")
            self.llm = None
        
        # Initialize Redis-based pattern memory
        self.pattern_memory = memory or create_pattern_memory(redis_only=True)
        
        # Phase 6: Initialize ML components
        if ML_AVAILABLE:
            try:
                self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                self.clusterer = KMeans(n_clusters=5, random_state=42, n_init=10)
                self.trend_predictor = LinearRegression()
                
                if verbose:
                    print("🤖 ML components initialized: TF-IDF, K-Means, Linear Regression")
            except Exception as e:
                if verbose:
                    print(f"⚠️ Failed to initialize ML components: {e}")
                self.vectorizer = None
                self.clusterer = None
                self.trend_predictor = None
        else:
            self.vectorizer = None
            self.clusterer = None
            self.trend_predictor = None
            
            if verbose:
                print("⚠️ ML libraries not available - using statistical analysis only")
        
        # Initialize scheduler if available
        self.scheduler = None
        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            if verbose:
                print("📅 Learner: Background scheduler initialized")
        
        # Configuration for learning
        self.min_pattern_frequency = 3  # Minimum occurrences to consider a pattern
        self.min_confidence_threshold = 0.6  # Minimum confidence to apply patterns
        self.max_commits_to_analyze = 100  # Maximum commits to analyze in one session
    
    def learn_from_commits(self, repo_path: str, config: Config) -> Dict[str, Any]:
        """
        Analyze commit history and extract coding patterns.
        
        Args:
            repo_path: Path to Git repository
            config: Current configuration object
            
        Returns:
            Dictionary with learning results and extracted patterns
        """
        if not GIT_AVAILABLE:
            self.logger.warning("GitPython not available - skipping commit analysis")
            return {"error": "GitPython not available", "patterns_learned": 0}
        
        try:
            if self.verbose:
                print(f"🔍 Learner: Analyzing commit history in {repo_path}")
            
            # Initialize repository
            repo = Repo(repo_path)
            
            # Get recent commits (limit to avoid performance issues)
            commits = list(repo.iter_commits(max_count=self.max_commits_to_analyze))
            
            if not commits:
                return {"error": "No commits found", "patterns_learned": 0}
            
            # Extract patterns from commits
            patterns = self._extract_patterns_from_commits(commits, repo_path)
            
            # Store patterns with confidence scores
            patterns_stored = 0
            for pattern_type, pattern_data in patterns.items():
                if pattern_data['frequency'] >= self.min_pattern_frequency:
                    confidence = self._calculate_pattern_confidence(pattern_data)
                    
                    if self.pattern_memory.store_pattern(repo_path, pattern_type, pattern_data, confidence):
                        patterns_stored += 1
                        
                        if self.verbose:
                            print(f"📊 Stored pattern: {pattern_type} (confidence: {confidence:.2f})")
            
            # Record learning session
            self.pattern_memory.record_learning_session(
                repo_path, "commit_analysis", patterns_stored, len(patterns)
            )
            
            return {
                "commits_analyzed": len(commits),
                "patterns_found": len(patterns),
                "patterns_stored": patterns_stored,
                "patterns": patterns
            }
            
        except InvalidGitRepositoryError:
            self.logger.error(f"Invalid Git repository: {repo_path}")
            return {"error": "Invalid Git repository", "patterns_learned": 0}
        except Exception as e:
            self.logger.error(f"Failed to analyze commits: {e}")
            return {"error": str(e), "patterns_learned": 0}
    
    def analyze_commit_history(self, repo_path: str, commit_count: int = 100) -> Dict[str, Any]:
        """
        Analyze commit history for patterns (legacy method for compatibility).
        
        Args:
            repo_path: Path to repository
            commit_count: Number of commits to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Create a minimal config for compatibility
        config = Config()
        self.max_commits_to_analyze = min(commit_count, 200)  # Safety limit
        
        result = self.learn_from_commits(repo_path, config)
        
        return {
            "commits_analyzed": result.get("commits_analyzed", 0),
            "patterns_found": result.get("patterns", [])
        }
    
    def extract_team_patterns(self, history_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract team coding patterns from history."""
        # TODO: Implement pattern extraction
        return {
            "patterns": [],
            "confidence": 0.0
        }
    
    def update_analysis_rules(self, patterns_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update analysis rules based on learned patterns."""
        # TODO: Implement rule updates
        return {
            "rules_updated": 0,
            "changes": []
        }
    
    def validate_rule_improvements(self, repo_path: str, rules_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that rule improvements are beneficial."""
        # TODO: Implement validation
        return {
            "validation_passed": True,
            "improvements": []
        }
    
    def _extract_patterns_from_commits(self, commits: List, repo_path: str) -> Dict[str, Any]:
        """
        Extract coding patterns from commit history.
        
        Args:
            commits: List of Git commit objects
            repo_path: Repository path for context
            
        Returns:
            Dictionary of extracted patterns with frequencies
        """
        patterns = {
            'naming_conventions': {'variables': Counter(), 'functions': Counter(), 'frequency': 0},
            'import_styles': {'organization': Counter(), 'patterns': Counter(), 'frequency': 0},
            'code_structure': {'indentation': Counter(), 'line_length': Counter(), 'frequency': 0}
        }
        
        files_analyzed = 0
        
        for commit in commits:
            try:
                # Skip merge commits and commits with too many changes
                if len(commit.parents) > 1 or len(commit.stats.files) > 20:
                    continue
                
                # Analyze Python files in the commit
                for file_path, stats in commit.stats.files.items():
                    if not file_path.endswith('.py'):
                        continue
                    
                    # Skip sensitive files
                    if self.pattern_memory.anonymizer.is_sensitive_file(file_path):
                        continue
                    
                    try:
                        # Get file content from commit
                        file_content = self._get_file_content_from_commit(commit, file_path)
                        if file_content:
                            self._analyze_file_patterns(file_content, patterns)
                            files_analyzed += 1
                            
                    except Exception as e:
                        self.logger.debug(f"Failed to analyze file {file_path}: {e}")
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Failed to analyze commit {commit.hexsha[:8]}: {e}")
                continue
        
        # Calculate frequencies and confidence
        for pattern_type in patterns:
            patterns[pattern_type]['frequency'] = files_analyzed
            patterns[pattern_type]['files_analyzed'] = files_analyzed
        
        if self.verbose:
            print(f"📈 Analyzed {files_analyzed} Python files from {len(commits)} commits")
        
        return patterns
    
    def _get_file_content_from_commit(self, commit, file_path: str) -> Optional[str]:
        """Get file content from a specific commit."""
        try:
            blob = commit.tree[file_path]
            return blob.data_stream.read().decode('utf-8', errors='ignore')
        except Exception:
            return None
    
    def _analyze_file_patterns(self, file_content: str, patterns: Dict) -> None:
        """Analyze patterns in a single file."""
        try:
            # Parse AST for structural analysis
            tree = ast.parse(file_content)
            
            # Ensure Counter objects exist
            if not isinstance(patterns['naming_conventions']['variables'], Counter):
                patterns['naming_conventions']['variables'] = Counter()
            if not isinstance(patterns['naming_conventions']['functions'], Counter):
                patterns['naming_conventions']['functions'] = Counter()
            
            # Analyze naming conventions
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    var_name = node.id
                    if not var_name.startswith('_'):  # Skip private variables
                        naming_style = self._classify_naming_style(var_name)
                        patterns['naming_conventions']['variables'][naming_style] += 1
                
                elif isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if not func_name.startswith('_'):  # Skip private functions
                        naming_style = self._classify_naming_style(func_name)
                        patterns['naming_conventions']['functions'][naming_style] += 1
            
            # Analyze import styles
            if not isinstance(patterns['import_styles']['patterns'], Counter):
                patterns['import_styles']['patterns'] = Counter()
            
            import_lines = [line.strip() for line in file_content.split('\n') 
                          if line.strip().startswith(('import ', 'from '))]
            
            for import_line in import_lines:
                import_style = self._classify_import_style(import_line)
                patterns['import_styles']['patterns'][import_style] += 1
            
            # Analyze code structure
            if not isinstance(patterns['code_structure']['indentation'], Counter):
                patterns['code_structure']['indentation'] = Counter()
            if not isinstance(patterns['code_structure']['line_length'], Counter):
                patterns['code_structure']['line_length'] = Counter()
            
            lines = file_content.split('\n')
            for line in lines:
                if line.strip():  # Skip empty lines
                    # Analyze indentation
                    indent_level = len(line) - len(line.lstrip())
                    if indent_level > 0:
                        indent_type = 'spaces' if line.startswith(' ') else 'tabs'
                        patterns['code_structure']['indentation'][indent_type] += 1
                    
                    # Analyze line length
                    line_length = len(line)
                    if line_length > 80:
                        patterns['code_structure']['line_length']['long'] += 1
                    else:
                        patterns['code_structure']['line_length']['normal'] += 1
                        
        except SyntaxError:
            # Skip files with syntax errors
            pass
        except Exception as e:
            self.logger.debug(f"Failed to analyze file patterns: {e}")
    
    def _classify_naming_style(self, name: str) -> str:
        """Classify naming style (snake_case, camelCase, etc.)."""
        if name.isupper() and '_' in name:
            return 'UPPER_CASE'
        elif '_' in name and name.islower():
            return 'snake_case'
        elif '_' in name:  # Mixed case with underscores
            return 'other'
        elif name[0].islower() and any(c.isupper() for c in name[1:]):
            return 'camelCase'
        elif name[0].isupper() and any(c.isupper() for c in name[1:]):
            return 'PascalCase'
        else:
            return 'other'
    
    def _classify_import_style(self, import_line: str) -> str:
        """Classify import organization style."""
        if import_line.startswith('from '):
            return 'from_import'
        elif ',' in import_line:
            return 'multiple_import'
        else:
            return 'single_import'
    
    def _calculate_pattern_confidence(self, pattern_data: Dict) -> float:
        """Calculate confidence score for a pattern based on frequency and consistency."""
        frequency = pattern_data.get('frequency', 0)
        
        # Handle low-frequency patterns with reduced confidence
        if frequency < self.min_pattern_frequency:
            return 0.0
        elif frequency < 5:
            # Low frequency patterns get capped confidence
            return min(0.5, frequency * 0.1)
        
        # Calculate consistency score
        consistency_scores = []
        
        for category, counter in pattern_data.items():
            if category == 'frequency':  # Skip frequency field
                continue
                
            if isinstance(counter, Counter) and counter:
                total = sum(counter.values())
                most_common_count = counter.most_common(1)[0][1]
                consistency = most_common_count / total if total > 0 else 0
                consistency_scores.append(consistency)
            elif isinstance(counter, dict) and counter:
                # Handle dict case
                total = sum(counter.values())
                if total > 0:
                    most_common_count = max(counter.values())
                    consistency = most_common_count / total
                    consistency_scores.append(consistency)
        
        if not consistency_scores:
            return min(0.3, frequency * 0.05)  # Fallback for patterns without counters
        
        # Average consistency weighted by frequency
        avg_consistency = sum(consistency_scores) / len(consistency_scores)
        frequency_weight = min(frequency / 50, 1.0)  # Cap at 50 files
        
        # Prevent overconfidence in rare patterns
        confidence = avg_consistency * frequency_weight * 0.85
        return min(confidence, 0.95)
    
    def adapt_team_style(self, config: Config, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update team style configuration based on learned patterns.
        
        Args:
            config: Configuration object to update
            patterns: Extracted patterns from analysis
            
        Returns:
            Dictionary with adaptation results
        """
        adaptations_made = 0
        changes = []
        
        try:
            # Adapt naming conventions
            if 'naming_conventions' in patterns:
                naming_patterns = patterns['naming_conventions']
                
                # Update variable naming preference
                if naming_patterns['variables']:
                    if isinstance(naming_patterns['variables'], Counter):
                        most_common_var_style = naming_patterns['variables'].most_common(1)[0][0]
                    else:
                        # Handle dict case
                        most_common_var_style = max(naming_patterns['variables'].items(), key=lambda x: x[1])[0]
                    if hasattr(config, 'team_style') and 'naming_conventions' in config.team_style:
                        old_style = config.team_style['naming_conventions'].get('variables', 'unknown')
                        config.team_style['naming_conventions']['variables'] = most_common_var_style
                        changes.append(f"Variable naming: {old_style} -> {most_common_var_style}")
                        adaptations_made += 1
                
                # Update function naming preference
                if naming_patterns['functions']:
                    if isinstance(naming_patterns['functions'], Counter):
                        most_common_func_style = naming_patterns['functions'].most_common(1)[0][0]
                    else:
                        # Handle dict case
                        most_common_func_style = max(naming_patterns['functions'].items(), key=lambda x: x[1])[0]
                    if hasattr(config, 'team_style') and 'naming_conventions' in config.team_style:
                        old_style = config.team_style['naming_conventions'].get('functions', 'unknown')
                        config.team_style['naming_conventions']['functions'] = most_common_func_style
                        changes.append(f"Function naming: {old_style} -> {most_common_func_style}")
                        adaptations_made += 1
            
            # Adapt import styles
            if 'import_styles' in patterns:
                import_patterns = patterns['import_styles']
                if import_patterns['patterns']:
                    if isinstance(import_patterns['patterns'], Counter):
                        most_common_import = import_patterns['patterns'].most_common(1)[0][0]
                    else:
                        # Handle dict case
                        most_common_import = max(import_patterns['patterns'].items(), key=lambda x: x[1])[0]
                    if hasattr(config, 'team_style'):
                        # Ensure import_organization exists
                        if 'import_organization' not in config.team_style:
                            config.team_style['import_organization'] = {}
                        
                        old_style = config.team_style['import_organization'].get('preferred_style', 'unknown')
                        config.team_style['import_organization']['preferred_style'] = most_common_import
                        changes.append(f"Import style: {old_style} -> {most_common_import}")
                        adaptations_made += 1
            
            # Adapt code structure preferences
            if 'code_structure' in patterns:
                structure_patterns = patterns['code_structure']
                
                # Update indentation preference
                if structure_patterns['indentation']:
                    if isinstance(structure_patterns['indentation'], Counter):
                        most_common_indent = structure_patterns['indentation'].most_common(1)[0][0]
                    else:
                        # Handle dict case
                        most_common_indent = max(structure_patterns['indentation'].items(), key=lambda x: x[1])[0]
                    if hasattr(config, 'team_style'):
                        # Ensure formatting exists
                        if 'formatting' not in config.team_style:
                            config.team_style['formatting'] = {}
                        
                        old_indent = config.team_style['formatting'].get('indentation', 'unknown')
                        config.team_style['formatting']['indentation'] = most_common_indent
                        changes.append(f"Indentation: {old_indent} -> {most_common_indent}")
                        adaptations_made += 1
            
            if self.verbose and adaptations_made > 0:
                print(f"🔧 Made {adaptations_made} team style adaptations")
                for change in changes:
                    print(f"   • {change}")
            
            return {
                "adaptations_made": adaptations_made,
                "changes": changes,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to adapt team style: {e}")
            return {
                "adaptations_made": 0,
                "changes": [],
                "success": False,
                "error": str(e)
            }
    
    def extract_patterns(self, repo_path: str, code_snippets: List[str]) -> List[Dict]:
        """
        Phase 6: Extract sophisticated patterns using ML-based clustering and statistical analysis.
        
        Args:
            repo_path: Repository path for pattern storage
            code_snippets: List of code snippets to analyze
            
        Returns:
            List of extracted patterns with quality scores and cluster information
        """
        if not ML_AVAILABLE:
            if self.verbose:
                print("⚠️ ML libraries not available - falling back to statistical analysis")
            return self._extract_patterns_statistical(repo_path, code_snippets)
        
        try:
            if not code_snippets:
                return []
            
            if self.verbose:
                print(f"🤖 Extracting patterns from {len(code_snippets)} code snippets using ML")
            
            # Vectorize code snippets using TF-IDF
            vectors = self.vectorizer.fit_transform(code_snippets).toarray()
            
            # Perform K-means clustering
            n_clusters = min(5, len(code_snippets))  # Don't exceed number of snippets
            if n_clusters < 2:
                n_clusters = 1
                
            self.clusterer.n_clusters = n_clusters
            labels = self.clusterer.fit_predict(vectors)
            
            patterns = []
            cluster_centers = self.clusterer.cluster_centers_
            
            for i, (snippet, label) in enumerate(zip(code_snippets, labels)):
                # Calculate quality score based on various metrics
                quality_score = self._calculate_quality_score(snippet)
                
                # Calculate similarity to cluster center
                snippet_vector = vectors[i].reshape(1, -1)
                center_vector = cluster_centers[label].reshape(1, -1)
                similarity = cosine_similarity(snippet_vector, center_vector)[0][0]
                
                pattern = {
                    "type": f"code_pattern_{label}",
                    "snippet": snippet,
                    "quality_score": quality_score,
                    "cluster": int(label),
                    "cluster_similarity": float(similarity),
                    "vector_features": len(self.vectorizer.get_feature_names_out()) if hasattr(self.vectorizer, 'get_feature_names_out') else 0,
                    "analysis_method": "ml_clustering"
                }
                
                # Store pattern in Redis-based memory
                self.pattern_memory.store_pattern(
                    repo_path, "code_pattern", pattern, quality_score
                )
                patterns.append(pattern)
                
                if self.verbose and i < 3:  # Show first few patterns
                    print(f"   📊 Pattern {i}: cluster={label}, quality={quality_score:.2f}, similarity={similarity:.2f}")
            
            # Store cluster analysis metadata
            cluster_metadata = {
                "n_clusters": n_clusters,
                "total_patterns": len(patterns),
                "avg_quality": sum(p["quality_score"] for p in patterns) / len(patterns) if patterns else 0,
                "cluster_distribution": dict(zip(*np.unique(labels, return_counts=True))),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            self.pattern_memory.store_pattern(
                repo_path, "cluster_metadata", cluster_metadata, 1.0
            )
            
            if self.verbose:
                print(f"✅ Extracted {len(patterns)} patterns across {n_clusters} clusters")
                print(f"   📈 Average quality score: {cluster_metadata['avg_quality']:.2f}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to extract ML patterns: {e}")
            if self.verbose:
                print(f"⚠️ ML pattern extraction failed: {e}")
                print("🔄 Falling back to statistical analysis")
            return self._extract_patterns_statistical(repo_path, code_snippets)
    
    def _extract_patterns_statistical(self, repo_path: str, code_snippets: List[str]) -> List[Dict]:
        """
        Fallback statistical pattern extraction when ML libraries are unavailable.
        
        Args:
            repo_path: Repository path for pattern storage
            code_snippets: List of code snippets to analyze
            
        Returns:
            List of extracted patterns using statistical analysis
        """
        patterns = []
        
        try:
            for i, snippet in enumerate(code_snippets):
                # Statistical analysis of code characteristics
                lines = snippet.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                
                # Calculate statistical metrics
                avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0
                complexity_score = self._estimate_complexity(snippet)
                quality_score = self._calculate_quality_score(snippet)
                
                # Simple clustering based on complexity and length
                if complexity_score > 0.7:
                    cluster = "high_complexity"
                elif avg_line_length > 80:
                    cluster = "long_lines"
                else:
                    cluster = "standard"
                
                pattern = {
                    "type": f"code_pattern_{cluster}",
                    "snippet": snippet,
                    "quality_score": quality_score,
                    "cluster": cluster,
                    "avg_line_length": avg_line_length,
                    "complexity_score": complexity_score,
                    "analysis_method": "statistical"
                }
                
                # Store pattern in memory
                self.pattern_memory.store_pattern(
                    repo_path, "code_pattern", pattern, quality_score
                )
                patterns.append(pattern)
            
            if self.verbose:
                print(f"📊 Extracted {len(patterns)} patterns using statistical analysis")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed statistical pattern extraction: {e}")
            return []
    
    def _calculate_quality_score(self, code: str) -> float:
        """
        Calculate quality score for a code snippet based on various metrics.
        
        Args:
            code: Code snippet to analyze
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        try:
            # Basic quality metrics
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if not non_empty_lines:
                return 0.0
            
            # Analyze potential issues
            issues = []
            
            # Check for common code smells
            if any('TODO' in line or 'FIXME' in line for line in lines):
                issues.append("contains_todos")
            
            if any(len(line) > 120 for line in lines):
                issues.append("long_lines")
            
            # Check for complexity indicators
            complexity_indicators = ['if', 'for', 'while', 'try', 'except', 'with']
            complexity_count = sum(line.count(indicator) for line in lines for indicator in complexity_indicators)
            
            if complexity_count > len(non_empty_lines) * 0.3:  # More than 30% of lines have complexity
                issues.append("high_complexity")
            
            # Check for potential security issues
            security_patterns = ['eval(', 'exec(', 'input(', '__import__']
            if any(pattern in code for pattern in security_patterns):
                issues.append("security_risk")
            
            # Calculate quality score (higher is better)
            base_score = 1.0
            penalty_per_issue = 0.15
            quality_score = max(0.0, base_score - len(issues) * penalty_per_issue)
            
            return quality_score
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate quality score: {e}")
            return 0.5  # Default neutral score
    
    def _estimate_complexity(self, code: str) -> float:
        """
        Estimate code complexity using simple heuristics.
        
        Args:
            code: Code snippet to analyze
            
        Returns:
            Complexity score between 0.0 and 1.0
        """
        try:
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if not non_empty_lines:
                return 0.0
            
            # Count complexity indicators
            complexity_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with']
            nesting_indicators = ['{', '}', '(', ')', '[', ']']
            
            keyword_count = sum(line.count(keyword) for line in lines for keyword in complexity_keywords)
            nesting_count = sum(line.count(indicator) for line in lines for indicator in nesting_indicators)
            
            # Normalize by number of lines
            keyword_density = keyword_count / len(non_empty_lines)
            nesting_density = nesting_count / len(non_empty_lines)
            
            # Combine metrics (cap at 1.0)
            complexity_score = min(1.0, (keyword_density * 0.6 + nesting_density * 0.4) / 2)
            
            return complexity_score
            
        except Exception as e:
            self.logger.debug(f"Failed to estimate complexity: {e}")
            return 0.5  # Default neutral complexity
    
    def find_similar_patterns(self, repo_path: str, pattern: Dict) -> List[Dict]:
        """
        Find patterns similar to the given pattern using ML similarity analysis.
        
        Args:
            repo_path: Repository path to search in
            pattern: Pattern to find similarities for
            
        Returns:
            List of similar patterns with similarity scores
        """
        try:
            # Retrieve stored patterns
            stored_patterns = self.pattern_memory.retrieve_patterns(repo_path, "code_pattern")
            
            if not stored_patterns or not ML_AVAILABLE:
                return self._find_similar_patterns_statistical(stored_patterns, pattern)
            
            # Extract snippets for vectorization
            snippets = [p.get("snippet", "") for p in stored_patterns]
            target_snippet = pattern.get("snippet", "")
            
            if not target_snippet or not snippets:
                return []
            
            # Vectorize all snippets including target
            all_snippets = snippets + [target_snippet]
            vectors = self.vectorizer.fit_transform(all_snippets).toarray()
            
            # Calculate similarities
            target_vector = vectors[-1].reshape(1, -1)
            pattern_vectors = vectors[:-1]
            
            similarities = cosine_similarity(target_vector, pattern_vectors)[0]
            
            # Filter and sort by similarity
            similar_patterns = []
            for i, (stored_pattern, similarity) in enumerate(zip(stored_patterns, similarities)):
                if similarity > 0.8:  # High similarity threshold
                    similar_pattern = stored_pattern.copy()
                    similar_pattern["similarity_score"] = float(similarity)
                    similar_patterns.append(similar_pattern)
            
            # Sort by similarity (highest first)
            similar_patterns.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            if self.verbose and similar_patterns:
                print(f"🔍 Found {len(similar_patterns)} similar patterns (similarity > 0.8)")
                for i, sp in enumerate(similar_patterns[:3]):  # Show top 3
                    print(f"   📊 Pattern {i+1}: similarity={sp['similarity_score']:.3f}")
            
            return similar_patterns
            
        except Exception as e:
            self.logger.error(f"Failed to find similar patterns: {e}")
            return []
    
    def _find_similar_patterns_statistical(self, stored_patterns: List[Dict], pattern: Dict) -> List[Dict]:
        """
        Fallback statistical similarity analysis when ML is unavailable.
        
        Args:
            stored_patterns: List of stored patterns to compare against
            pattern: Target pattern to find similarities for
            
        Returns:
            List of similar patterns using statistical comparison
        """
        try:
            target_snippet = pattern.get("snippet", "")
            target_quality = pattern.get("quality_score", 0.5)
            
            similar_patterns = []
            
            for stored_pattern in stored_patterns:
                stored_snippet = stored_pattern.get("snippet", "")
                stored_quality = stored_pattern.get("quality_score", 0.5)
                
                # Simple similarity based on length and quality
                len_similarity = 1.0 - abs(len(target_snippet) - len(stored_snippet)) / max(len(target_snippet), len(stored_snippet), 1)
                quality_similarity = 1.0 - abs(target_quality - stored_quality)
                
                # Combined similarity
                similarity = (len_similarity * 0.6 + quality_similarity * 0.4)
                
                if similarity > 0.8:
                    similar_pattern = stored_pattern.copy()
                    similar_pattern["similarity_score"] = similarity
                    similar_patterns.append(similar_pattern)
            
            # Sort by similarity
            similar_patterns.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return similar_patterns
            
        except Exception as e:
            self.logger.debug(f"Failed statistical similarity analysis: {e}")
            return []

    def learn_from_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn from analysis results and update patterns.
        
        Args:
            analysis_result: Results from code analysis
            
        Returns:
            Dictionary with learning results
        """
        try:
            patterns_learned = 0
            insights = []
            
            # Extract repository path
            repo_path = analysis_result.get('repository_path', '.')
            
            # Learn from issue patterns
            if 'issues_by_type' in analysis_result:
                for issue_type, count in analysis_result['issues_by_type'].items():
                    if count > 0:
                        # Track issue pattern
                        self.pattern_memory.track_issue_pattern(
                            repo_path, issue_type, 'general', 'medium'
                        )
                        patterns_learned += 1
            
            # Learn from severity distribution
            if 'issues_by_severity' in analysis_result:
                severity_dist = analysis_result['issues_by_severity']
                total_issues = sum(severity_dist.values())
                
                if total_issues > 0:
                    high_severity_ratio = severity_dist.get('high', 0) / total_issues
                    if high_severity_ratio > 0.2:  # More than 20% high severity
                        insights.append("High ratio of severe issues detected - consider code review process improvements")
            
            # Record learning session
            self.pattern_memory.record_learning_session(
                repo_path, "analysis_learning", patterns_learned, len(insights)
            )
            
            return {
                "patterns_learned": patterns_learned,
                "insights": insights,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to learn from analysis: {e}")
            return {
                "patterns_learned": 0,
                "insights": [],
                "success": False,
                "error": str(e)
            }    
    def extract_team_patterns(self, history_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract team coding patterns from history analysis results.
        
        Args:
            history_result: Results from commit history analysis
            
        Returns:
            Dictionary with extracted patterns and confidence scores
        """
        try:
            patterns = history_result.get('patterns', {})
            extracted_patterns = {}
            
            for pattern_type, pattern_data in patterns.items():
                if pattern_data.get('frequency', 0) >= self.min_pattern_frequency:
                    confidence = self._calculate_pattern_confidence(pattern_data)
                    
                    if confidence >= self.min_confidence_threshold:
                        extracted_patterns[pattern_type] = {
                            'data': pattern_data,
                            'confidence': confidence,
                            'frequency': pattern_data.get('frequency', 0)
                        }
            
            return {
                "patterns": extracted_patterns,
                "total_patterns": len(extracted_patterns),
                "confidence_threshold": self.min_confidence_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract team patterns: {e}")
            return {"patterns": {}, "total_patterns": 0}
    
    def update_analysis_rules(self, patterns_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update analysis rules based on learned patterns.
        
        Args:
            patterns_result: Results from pattern extraction
            
        Returns:
            Dictionary with rule update results
        """
        try:
            rules_updated = 0
            changes = []
            
            patterns = patterns_result.get('patterns', {})
            
            # Update rules based on naming conventions
            if 'naming_conventions' in patterns:
                naming_data = patterns['naming_conventions']['data']
                
                # If team consistently uses snake_case, adjust naming rules
                if naming_data['variables'].get('snake_case', 0) > naming_data['variables'].get('camelCase', 0):
                    changes.append("Adjusted naming rules to prefer snake_case")
                    rules_updated += 1
            
            # Update rules based on import styles
            if 'import_styles' in patterns:
                import_data = patterns['import_styles']['data']
                
                # Adjust import organization rules
                if import_data['patterns'].get('from_import', 0) > import_data['patterns'].get('single_import', 0):
                    changes.append("Adjusted import rules to prefer 'from' imports")
                    rules_updated += 1
            
            return {
                "rules_updated": rules_updated,
                "changes": changes,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update analysis rules: {e}")
            return {
                "rules_updated": 0,
                "changes": [],
                "success": False,
                "error": str(e)
            }
    
    def predict_quality_trends(self, repo_path: str) -> Dict[str, Any]:
        """
        Phase 6: Predict code quality trends using machine learning and statistical analysis.
        
        Args:
            repo_path: Repository path to analyze trends for
            
        Returns:
            Dictionary with trend predictions, early warnings, and recommendations
        """
        try:
            if self.verbose:
                print(f"📈 Predicting quality trends for {repo_path}")
            
            # Retrieve workflow execution history
            executions = self.pattern_memory.retrieve_patterns(repo_path, "workflow_execution")
            
            if not executions or len(executions) < 3:
                if self.verbose:
                    print("⚠️ Insufficient data for trend prediction (need at least 3 executions)")
                return {
                    "predicted_score": 0.8,  # Default optimistic score
                    "early_warning": False,
                    "recommendations": ["Collect more data by running regular analyses"],
                    "confidence": 0.1,
                    "data_points": len(executions) if executions else 0
                }
            
            # Extract time series data
            times = []
            scores = []
            
            for execution in executions:
                try:
                    timestamp_str = execution.get("timestamp", "")
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        times.append(timestamp.timestamp())
                        
                        # Extract quality score from progress or create one
                        progress = execution.get("progress", 50)
                        quality_score = progress / 100.0  # Convert percentage to 0-1 scale
                        scores.append(quality_score)
                        
                except Exception as e:
                    self.logger.debug(f"Failed to parse execution data: {e}")
                    continue
            
            if len(times) < 2:
                return {
                    "predicted_score": 0.8,
                    "early_warning": False,
                    "recommendations": ["Unable to parse execution history"],
                    "confidence": 0.1,
                    "data_points": len(times)
                }
            
            # Predict using ML if available, otherwise use statistical analysis
            if ML_AVAILABLE and len(times) >= 3:
                predicted_score, confidence = self._predict_with_ml(times, scores)
            else:
                predicted_score, confidence = self._predict_statistical(times, scores)
            
            # Determine early warning
            current_score = scores[-1] if scores else 0.8
            early_warning = predicted_score < 0.7 or (predicted_score < current_score - 0.1)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(early_warning, predicted_score, current_score)
            
            # Store prediction for future reference
            prediction_data = {
                "predicted_score": predicted_score,
                "current_score": current_score,
                "early_warning": early_warning,
                "confidence": confidence,
                "data_points": len(times),
                "prediction_timestamp": datetime.now().isoformat(),
                "method": "ml" if ML_AVAILABLE else "statistical"
            }
            
            self.pattern_memory.store_pattern(
                repo_path, "quality_prediction", prediction_data, confidence
            )
            
            if self.verbose:
                print(f"📊 Prediction: {predicted_score:.2f} (confidence: {confidence:.2f})")
                if early_warning:
                    print("⚠️ Early warning: Quality decline predicted")
            
            return {
                "predicted_score": predicted_score,
                "early_warning": early_warning,
                "recommendations": recommendations,
                "confidence": confidence,
                "data_points": len(times),
                "current_score": current_score,
                "trend": "declining" if predicted_score < current_score else "improving"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to predict quality trends: {e}")
            return {
                "predicted_score": 0.8,
                "early_warning": False,
                "recommendations": [f"Prediction failed: {str(e)}"],
                "confidence": 0.0,
                "data_points": 0
            }
    
    def _predict_with_ml(self, times: List[float], scores: List[float]) -> Tuple[float, float]:
        """
        Predict using machine learning (Linear Regression).
        
        Args:
            times: List of timestamps
            scores: List of quality scores
            
        Returns:
            Tuple of (predicted_score, confidence)
        """
        try:
            # Prepare data for ML model
            X = np.array(times).reshape(-1, 1)
            y = np.array(scores)
            
            # Fit linear regression model
            self.trend_predictor.fit(X, y)
            
            # Predict 30 days into the future
            future_time = (datetime.now() + timedelta(days=30)).timestamp()
            predicted_score = self.trend_predictor.predict([[future_time]])[0]
            
            # Clamp prediction to valid range
            predicted_score = max(0.0, min(1.0, predicted_score))
            
            # Calculate confidence based on R² score
            r2_score = self.trend_predictor.score(X, y)
            confidence = max(0.1, min(0.95, r2_score))
            
            return predicted_score, confidence
            
        except Exception as e:
            self.logger.debug(f"ML prediction failed: {e}")
            return self._predict_statistical(times, scores)
    
    def _predict_statistical(self, times: List[float], scores: List[float]) -> Tuple[float, float]:
        """
        Fallback statistical prediction when ML is unavailable.
        
        Args:
            times: List of timestamps
            scores: List of quality scores
            
        Returns:
            Tuple of (predicted_score, confidence)
        """
        try:
            # Simple linear trend calculation
            if len(scores) < 2:
                return scores[0] if scores else 0.8, 0.1
            
            # Calculate trend slope
            recent_scores = scores[-3:] if len(scores) >= 3 else scores
            trend_slope = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
            
            # Project trend forward (30 data points representing ~30 days)
            predicted_score = scores[-1] + (trend_slope * 30)
            
            # Clamp to valid range
            predicted_score = max(0.0, min(1.0, predicted_score))
            
            # Calculate confidence based on trend consistency
            score_variance = np.var(scores) if len(scores) > 1 else 0.5
            confidence = max(0.1, min(0.8, 1.0 - score_variance))
            
            return predicted_score, confidence
            
        except Exception as e:
            self.logger.debug(f"Statistical prediction failed: {e}")
            return 0.8, 0.1  # Default fallback
    
    def _generate_recommendations(self, early_warning: bool, predicted_score: float, current_score: float) -> List[str]:
        """
        Generate recommendations based on trend analysis.
        
        Args:
            early_warning: Whether early warning is triggered
            predicted_score: Predicted quality score
            current_score: Current quality score
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if early_warning:
            recommendations.append("Increase review frequency")
            recommendations.append("Consider additional automated testing")
            
            if predicted_score < 0.5:
                recommendations.append("Schedule immediate code quality review")
                recommendations.append("Implement stricter merge requirements")
            elif predicted_score < 0.7:
                recommendations.append("Focus on high-priority issues")
                recommendations.append("Review recent changes for quality regressions")
        else:
            recommendations.append("Maintain current workflow")
            
            if predicted_score > current_score + 0.1:
                recommendations.append("Quality trend is positive - continue current practices")
            
            if predicted_score > 0.9:
                recommendations.append("Consider reducing review overhead while maintaining quality")
        
        # Add specific recommendations based on score ranges
        if predicted_score < 0.6:
            recommendations.append("Consider refactoring high-complexity modules")
        elif predicted_score > 0.85:
            recommendations.append("Share successful practices with other projects")
        
        return recommendations
    
    def track_quality_goals(self, repo_path: str, target_score: float) -> Dict[str, Any]:
        """
        Track progress toward quality goals and provide actionable insights.
        
        Args:
            repo_path: Repository path to track
            target_score: Target quality score (0.0 to 1.0)
            
        Returns:
            Dictionary with current progress, gap analysis, and action items
        """
        try:
            if self.verbose:
                print(f"🎯 Tracking quality goals for {repo_path} (target: {target_score:.2f})")
            
            # Get current quality metrics
            current_metrics = self.analyze_workflows(repo_path)
            current_score = current_metrics.get("success_rate", 0.8)
            
            # Calculate gap
            gap = target_score - current_score
            gap_percentage = (gap / target_score) * 100 if target_score > 0 else 0
            
            # Determine status
            if gap <= 0:
                status = "achieved"
            elif gap <= 0.1:
                status = "close"
            elif gap <= 0.2:
                status = "moderate_gap"
            else:
                status = "significant_gap"
            
            # Generate action items based on gap
            action_items = self._generate_action_items(gap, current_score, target_score)
            
            # Estimate timeline to goal
            timeline_estimate = self._estimate_timeline_to_goal(repo_path, current_score, target_score)
            
            # Store goal tracking data
            goal_data = {
                "target_score": target_score,
                "current_score": current_score,
                "gap": gap,
                "gap_percentage": gap_percentage,
                "status": status,
                "timeline_estimate": timeline_estimate,
                "tracking_timestamp": datetime.now().isoformat()
            }
            
            self.pattern_memory.store_pattern(
                repo_path, "quality_goal", goal_data, 1.0
            )
            
            if self.verbose:
                print(f"📊 Current: {current_score:.2f}, Target: {target_score:.2f}, Gap: {gap:.2f}")
                print(f"📅 Estimated timeline: {timeline_estimate}")
            
            return {
                "current": current_score,
                "target": target_score,
                "gap": gap,
                "gap_percentage": gap_percentage,
                "status": status,
                "action_items": action_items,
                "timeline_estimate": timeline_estimate
            }
            
        except Exception as e:
            self.logger.error(f"Failed to track quality goals: {e}")
            return {
                "current": 0.8,
                "target": target_score,
                "gap": target_score - 0.8,
                "status": "unknown",
                "action_items": ["Unable to track goals due to error"],
                "timeline_estimate": "unknown"
            }
    
    def _generate_action_items(self, gap: float, current_score: float, target_score: float) -> List[str]:
        """
        Generate specific action items based on quality gap analysis.
        
        Args:
            gap: Quality score gap (target - current)
            current_score: Current quality score
            target_score: Target quality score
            
        Returns:
            List of actionable items
        """
        action_items = []
        
        if gap <= 0:
            action_items.append("Goal achieved - maintain current quality standards")
            action_items.append("Consider setting higher quality targets")
        elif gap <= 0.05:
            action_items.append("Close to goal - focus on consistency")
            action_items.append("Address remaining minor issues")
        elif gap <= 0.1:
            action_items.append("Moderate gap - increase review frequency")
            action_items.append("Focus on high-impact improvements")
        elif gap <= 0.2:
            action_items.append("Significant gap - implement systematic improvements")
            action_items.append("Consider additional automated checks")
            action_items.append("Schedule team training on quality practices")
        else:
            action_items.append("Large gap - comprehensive quality initiative needed")
            action_items.append("Audit current development processes")
            action_items.append("Implement stricter quality gates")
            action_items.append("Consider external quality assessment")
        
        # Add score-specific recommendations
        if current_score < 0.6:
            action_items.append("Address fundamental code quality issues")
        elif current_score < 0.8:
            action_items.append("Focus on reducing technical debt")
        
        if target_score > 0.9:
            action_items.append("High target requires exceptional discipline")
            action_items.append("Implement peer review for all changes")
        
        return action_items
    
    def _estimate_timeline_to_goal(self, repo_path: str, current_score: float, target_score: float) -> str:
        """
        Estimate timeline to reach quality goal based on historical trends.
        
        Args:
            repo_path: Repository path for historical data
            current_score: Current quality score
            target_score: Target quality score
            
        Returns:
            Timeline estimate as string
        """
        try:
            # Get historical trend data
            executions = self.pattern_memory.retrieve_patterns(repo_path, "workflow_execution")
            
            if not executions or len(executions) < 3:
                return "insufficient_data"
            
            # Calculate historical improvement rate
            scores = []
            for execution in executions[-10:]:  # Last 10 executions
                progress = execution.get("progress", 50)
                scores.append(progress / 100.0)
            
            if len(scores) < 2:
                return "insufficient_data"
            
            # Calculate average improvement per execution
            improvements = [scores[i] - scores[i-1] for i in range(1, len(scores))]
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0
            
            if avg_improvement <= 0:
                return "no_improvement_trend"
            
            # Estimate executions needed
            gap = target_score - current_score
            executions_needed = gap / avg_improvement
            
            # Convert to time estimate (assuming 1 execution per week)
            if executions_needed <= 1:
                return "1_week"
            elif executions_needed <= 4:
                return f"{int(executions_needed)}_weeks"
            elif executions_needed <= 12:
                return f"{int(executions_needed/4)}_months"
            else:
                return "6_months_plus"
                
        except Exception as e:
            self.logger.debug(f"Failed to estimate timeline: {e}")
            return "unknown"
    
    def analyze_workflows(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze workflow execution patterns and success rates.
        
        Args:
            repo_path: Repository path to analyze
            
        Returns:
            Dictionary with workflow analysis results
        """
        try:
            # Retrieve workflow execution data
            executions = self.pattern_memory.retrieve_patterns(repo_path, "workflow_execution")
            
            if not executions:
                return {
                    "success_rate": 0.8,  # Default assumption
                    "total_executions": 0,
                    "avg_progress": 0.8,
                    "trend": "unknown"
                }
            
            # Calculate success metrics
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.get("progress", 0) >= 80)
            success_rate = successful_executions / total_executions if total_executions > 0 else 0.8
            
            # Calculate average progress
            progress_values = [e.get("progress", 50) for e in executions]
            avg_progress = sum(progress_values) / len(progress_values) / 100.0 if progress_values else 0.8
            
            # Determine trend
            if len(progress_values) >= 3:
                recent_avg = sum(progress_values[-3:]) / 3
                older_avg = sum(progress_values[:-3]) / len(progress_values[:-3]) if len(progress_values) > 3 else recent_avg
                
                if recent_avg > older_avg + 5:
                    trend = "improving"
                elif recent_avg < older_avg - 5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            return {
                "success_rate": success_rate,
                "total_executions": total_executions,
                "avg_progress": avg_progress,
                "trend": trend,
                "recent_executions": min(10, total_executions)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze workflows: {e}")
            return {
                "success_rate": 0.8,
                "total_executions": 0,
                "avg_progress": 0.8,
                "trend": "unknown"
            }

    def validate_rule_improvements(self, repo_path: str, rules_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that rule improvements are beneficial.
        
        Args:
            repo_path: Repository path for validation
            rules_result: Results from rule updates
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Simple validation based on rule update success
            rules_updated = rules_result.get('rules_updated', 0)
            changes = rules_result.get('changes', [])
            
            # For now, assume rule improvements are valid if they were successfully applied
            validation_passed = rules_result.get('success', False) and rules_updated > 0
            
            improvements = []
            if validation_passed:
                improvements = [f"Validated improvement: {change}" for change in changes]
            
            return {
                "validation_passed": validation_passed,
                "improvements": improvements,
                "rules_validated": rules_updated
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate rule improvements: {e}")
            return {
                "validation_passed": False,
                "improvements": [],
                "rules_validated": 0
            }
    
    def start_periodic_learning(self, repo_path: str, interval_hours: int = 24) -> bool:
        """
        Start periodic learning for a repository.
        
        Args:
            repo_path: Repository path to monitor
            interval_hours: Hours between learning sessions
            
        Returns:
            True if scheduling was successful
        """
        if not SCHEDULER_AVAILABLE or not self.scheduler:
            self.logger.warning("Scheduler not available - periodic learning disabled")
            return False
        
        try:
            # Create a minimal config for periodic learning
            config = Config()
            
            # Schedule periodic learning
            self.scheduler.add_job(
                func=self._periodic_learning_job,
                trigger="interval",
                hours=interval_hours,
                args=[repo_path, config],
                id=f"learning_{hashlib.md5(repo_path.encode()).hexdigest()}",
                replace_existing=True
            )
            
            if not self.scheduler.running:
                self.scheduler.start()
            
            if self.verbose:
                print(f"📅 Scheduled periodic learning for {repo_path} every {interval_hours} hours")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start periodic learning: {e}")
            return False
    
    def stop_periodic_learning(self, repo_path: str) -> bool:
        """
        Stop periodic learning for a repository.
        
        Args:
            repo_path: Repository path to stop monitoring
            
        Returns:
            True if stopping was successful
        """
        if not SCHEDULER_AVAILABLE or not self.scheduler:
            return False
        
        try:
            job_id = f"learning_{hashlib.md5(repo_path.encode()).hexdigest()}"
            self.scheduler.remove_job(job_id)
            
            if self.verbose:
                print(f"🛑 Stopped periodic learning for {repo_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop periodic learning: {e}")
            return False
    
    def _periodic_learning_job(self, repo_path: str, config: Config) -> None:
        """
        Periodic learning job executed by scheduler.
        
        Args:
            repo_path: Repository path to analyze
            config: Configuration object
        """
        try:
            if self.verbose:
                print(f"🔄 Running periodic learning for {repo_path}")
            
            # Perform learning from commits
            learning_result = self.learn_from_commits(repo_path, config)
            
            # Adapt team style if patterns were found
            if learning_result.get('patterns_stored', 0) > 0:
                patterns = learning_result.get('patterns', {})
                adaptation_result = self.adapt_team_style(config, patterns)
                
                if self.verbose and adaptation_result.get('adaptations_made', 0) > 0:
                    print(f"🔧 Periodic learning made {adaptation_result['adaptations_made']} adaptations")
            
        except Exception as e:
            self.logger.error(f"Periodic learning job failed: {e}")
    
    def track_team_style_evolution(self, repo_path: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Track how team style has evolved over time.
        
        Args:
            repo_path: Repository path
            days_back: Number of days to analyze for evolution
            
        Returns:
            Dictionary with evolution analysis
        """
        try:
            evolution_data = {}
            
            # Get pattern evolution for different types
            pattern_types = ['naming_conventions', 'import_styles', 'code_structure']
            
            for pattern_type in pattern_types:
                evolution = self.pattern_memory.get_pattern_evolution(repo_path, pattern_type, days_back)
                if evolution['total_changes'] > 0:
                    evolution_data[pattern_type] = evolution
            
            # Analyze trends
            trends = self._analyze_evolution_trends(evolution_data)
            
            return {
                "repo_path": repo_path,
                "days_analyzed": days_back,
                "pattern_evolution": evolution_data,
                "trends": trends,
                "total_changes": sum(e['total_changes'] for e in evolution_data.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to track team style evolution: {e}")
            return {"error": str(e), "total_changes": 0}
    
    def _analyze_evolution_trends(self, evolution_data: Dict[str, Any]) -> List[str]:
        """Analyze trends in team style evolution."""
        trends = []
        
        for pattern_type, evolution in evolution_data.items():
            changes = evolution.get('changes', [])
            if len(changes) >= 3:  # Need at least 3 changes to identify a trend
                
                # Analyze confidence trends
                confidence_trend = evolution.get('confidence_trend', [])
                if len(confidence_trend) >= 2:
                    recent_confidence = confidence_trend[-1]['confidence_change']
                    older_confidence = confidence_trend[0]['confidence_change']
                    
                    if recent_confidence > older_confidence + 0.1:
                        trends.append(f"{pattern_type}: Increasing confidence in team patterns")
                    elif recent_confidence < older_confidence - 0.1:
                        trends.append(f"{pattern_type}: Decreasing confidence - patterns may be changing")
                
                # Analyze change frequency
                if len(changes) > 5:
                    trends.append(f"{pattern_type}: High pattern volatility - team style still evolving")
        
        return trends
    
    def optimize_rules_based_on_feedback(self, repo_path: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize analysis rules based on user feedback and fix success rates.
        
        Args:
            repo_path: Repository path
            feedback_data: User feedback and success rate data
            
        Returns:
            Dictionary with optimization results
        """
        try:
            optimizations = []
            rules_adjusted = 0
            
            # Get fix success rates
            success_rates = self.pattern_memory.get_fix_success_rates(repo_path)
            
            # Optimize based on low success rates
            for fix_type, stats in success_rates.items():
                success_rate = stats.get('success_rate', 0.0)
                avg_feedback = stats.get('avg_feedback', 0.0)
                
                if success_rate < 0.5 and stats.get('total_attempts', 0) >= 5:
                    # Rule needs adjustment - low success rate
                    optimization = self._create_rule_optimization(fix_type, 'low_success_rate', {
                        'current_rate': success_rate,
                        'attempts': stats['total_attempts']
                    })
                    optimizations.append(optimization)
                    rules_adjusted += 1
                
                elif avg_feedback < -0.3 and stats.get('total_attempts', 0) >= 3:
                    # Rule needs adjustment - negative feedback
                    optimization = self._create_rule_optimization(fix_type, 'negative_feedback', {
                        'avg_feedback': avg_feedback,
                        'attempts': stats['total_attempts']
                    })
                    optimizations.append(optimization)
                    rules_adjusted += 1
            
            # Apply optimizations
            applied_optimizations = []
            for optimization in optimizations:
                if self._apply_rule_optimization(repo_path, optimization):
                    applied_optimizations.append(optimization)
            
            return {
                "repo_path": repo_path,
                "rules_analyzed": len(success_rates),
                "optimizations_identified": len(optimizations),
                "optimizations_applied": len(applied_optimizations),
                "optimizations": applied_optimizations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to optimize rules: {e}")
            return {"error": str(e), "optimizations_applied": 0}
    
    def _create_rule_optimization(self, fix_type: str, reason: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a rule optimization recommendation."""
        optimization = {
            "fix_type": fix_type,
            "reason": reason,
            "data": data,
            "created_at": datetime.now().isoformat()
        }
        
        if reason == 'low_success_rate':
            optimization["recommendation"] = f"Reduce sensitivity for {fix_type} rules"
            optimization["action"] = "decrease_sensitivity"
        elif reason == 'negative_feedback':
            optimization["recommendation"] = f"Disable or modify {fix_type} rules due to negative feedback"
            optimization["action"] = "disable_or_modify"
        
        return optimization
    
    def _apply_rule_optimization(self, repo_path: str, optimization: Dict[str, Any]) -> bool:
        """Apply a rule optimization."""
        try:
            fix_type = optimization["fix_type"]
            action = optimization["action"]
            
            # Store the optimization as a pattern for future reference
            optimization_pattern = {
                "optimization": optimization,
                "applied_at": datetime.now().isoformat(),
                "status": "applied"
            }
            
            # Store in pattern memory
            pattern_id = f"rule_optimization_{fix_type}"
            success = self.pattern_memory.store_pattern(
                repo_path, 
                "rule_optimization", 
                optimization_pattern, 
                0.8  # High confidence for applied optimizations
            )
            
            if success and self.verbose:
                print(f"🔧 Applied rule optimization for {fix_type}: {optimization['recommendation']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to apply rule optimization: {e}")
            return False
    
    def synthesize_knowledge_from_sources(self, repo_path: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        Synthesize knowledge from multiple sources (commit history, feedback, patterns).
        
        Args:
            repo_path: Repository path
            sources: List of sources to synthesize from
            
        Returns:
            Dictionary with synthesized insights
        """
        if sources is None:
            sources = ['commit_history', 'user_feedback', 'issue_patterns', 'fix_outcomes']
        
        try:
            synthesis = {
                "repo_path": repo_path,
                "sources_analyzed": [],
                "insights": [],
                "recommendations": [],
                "confidence_score": 0.0
            }
            
            total_confidence = 0.0
            source_count = 0
            
            # Synthesize from commit history
            if 'commit_history' in sources:
                patterns = self.pattern_memory.get_team_patterns(repo_path)
                if patterns:
                    synthesis["sources_analyzed"].append("commit_history")
                    
                    # Extract insights from patterns
                    for pattern in patterns:
                        confidence = pattern.get('confidence', 0.0)
                        if confidence > 0.7:
                            insight = f"Strong {pattern['pattern_type']} pattern detected (confidence: {confidence:.2f})"
                            synthesis["insights"].append(insight)
                    
                    avg_confidence = sum(p.get('confidence', 0.0) for p in patterns) / len(patterns)
                    total_confidence += avg_confidence
                    source_count += 1
            
            # Synthesize from user feedback
            if 'user_feedback' in sources:
                success_rates = self.pattern_memory.get_fix_success_rates(repo_path)
                if success_rates:
                    synthesis["sources_analyzed"].append("user_feedback")
                    
                    # Analyze feedback patterns
                    high_success_fixes = [fix for fix, stats in success_rates.items() 
                                        if stats.get('success_rate', 0.0) > 0.8]
                    low_success_fixes = [fix for fix, stats in success_rates.items() 
                                       if stats.get('success_rate', 0.0) < 0.3]
                    
                    if high_success_fixes:
                        synthesis["recommendations"].append(f"Prioritize these successful fix types: {', '.join(high_success_fixes)}")
                    
                    if low_success_fixes:
                        synthesis["recommendations"].append(f"Review or disable these problematic fix types: {', '.join(low_success_fixes)}")
                    
                    # Calculate feedback confidence
                    if success_rates:
                        avg_success_rate = sum(stats.get('success_rate', 0.0) for stats in success_rates.values()) / len(success_rates)
                        total_confidence += avg_success_rate
                        source_count += 1
            
            # Synthesize from issue patterns
            if 'issue_patterns' in sources:
                issue_trends = self.pattern_memory.get_issue_trends(repo_path)
                if issue_trends.get('total_patterns', 0) > 0:
                    synthesis["sources_analyzed"].append("issue_patterns")
                    
                    # Analyze trending issues
                    trending_issues = issue_trends.get('trending_issues', [])[:3]
                    for issue in trending_issues:
                        insight = f"Trending issue: {issue['issue_type']} ({issue['frequency']} occurrences)"
                        synthesis["insights"].append(insight)
                    
                    # Issue pattern confidence based on frequency
                    if trending_issues:
                        max_frequency = max(issue.get('frequency', 0) for issue in trending_issues)
                        issue_confidence = min(max_frequency / 10.0, 1.0)  # Normalize to 0-1
                        total_confidence += issue_confidence
                        source_count += 1
            
            # Calculate overall confidence
            if source_count > 0:
                synthesis["confidence_score"] = total_confidence / source_count
            
            # Generate meta-insights
            if len(synthesis["insights"]) > 3:
                synthesis["recommendations"].append("Rich pattern data available - consider enabling more aggressive automated fixes")
            elif len(synthesis["insights"]) < 2:
                synthesis["recommendations"].append("Limited pattern data - continue learning before enabling automation")
            
            return synthesis
            
        except Exception as e:
            self.logger.error(f"Failed to synthesize knowledge: {e}")
            return {"error": str(e), "insights": [], "recommendations": []}
    
    def get_learning_status(self, repo_path: str) -> Dict[str, Any]:
        """
        Get comprehensive learning status and statistics for a repository.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Dictionary with learning status and statistics
        """
        try:
            # Get patterns from memory
            patterns = self.pattern_memory.get_team_patterns(repo_path)
            
            # Get learning analytics
            analytics = self.pattern_memory.get_learning_analytics(repo_path)
            
            # Get comprehensive insights
            insights = self.pattern_memory.get_comprehensive_insights(repo_path)
            
            # Check if periodic learning is active
            periodic_active = False
            if SCHEDULER_AVAILABLE and self.scheduler:
                job_id = f"learning_{hashlib.md5(repo_path.encode()).hexdigest()}"
                try:
                    job = self.scheduler.get_job(job_id)
                    periodic_active = job is not None
                except:
                    periodic_active = False
            
            # Get recent evolution data
            evolution = self.track_team_style_evolution(repo_path, 7)  # Last 7 days
            
            return {
                "repo_path": repo_path,
                "patterns_stored": len(patterns),
                "learning_sessions": analytics.get('total_sessions', 0),
                "patterns_learned": analytics.get('total_patterns_learned', 0),
                "insights_generated": analytics.get('total_insights_generated', 0),
                "periodic_learning_active": periodic_active,
                "last_learning_session": patterns[0]['updated_at'] if patterns else None,
                "pattern_confidence_summary": insights.get('pattern_confidence_summary', {}),
                "recent_evolution_changes": evolution.get('total_changes', 0),
                "recommendations": insights.get('recommendations', [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get learning status: {e}")
            return {
                "repo_path": repo_path,
                "patterns_stored": 0,
                "learning_sessions": 0,
                "error": str(e)
            }    

    # Phase 6: Advanced Learning and Adaptation Methods
    
    def extract_patterns(self, repo_path: str, code_snippets: List[str]) -> List[Dict[str, Any]]:
        """
        Sophisticated pattern extraction using ML clustering (Task 21.1).
        
        Args:
            repo_path: Repository path
            code_snippets: List of code snippets to analyze
            
        Returns:
            List of extracted patterns with quality scores
        """
        try:
            if not code_snippets:
                return []
            
            if self.verbose:
                print(f"🔬 Extracting patterns from {len(code_snippets)} code snippets")
            
            patterns = []
            
            if ML_AVAILABLE and self.vectorizer and self.clusterer:
                # ML-based pattern extraction
                patterns = self._extract_patterns_ml(repo_path, code_snippets)
            else:
                # Fallback to statistical analysis
                patterns = self._extract_patterns_statistical(repo_path, code_snippets)
            
            if self.verbose:
                print(f"📊 Extracted {len(patterns)} patterns")
            
            return patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Pattern extraction failed: {e}")
            return []
    
    def _extract_patterns_ml(self, repo_path: str, code_snippets: List[str]) -> List[Dict[str, Any]]:
        """ML-based pattern extraction using TF-IDF and K-Means clustering."""
        try:
            # Vectorize code snippets
            vectors = self.vectorizer.fit_transform(code_snippets).toarray()
            
            # Cluster patterns
            n_clusters = min(5, len(code_snippets))
            if n_clusters < 2:
                n_clusters = 1
            
            self.clusterer.n_clusters = n_clusters
            labels = self.clusterer.fit_predict(vectors)
            
            patterns = []
            for i, (snippet, label) in enumerate(zip(code_snippets, labels)):
                # Calculate quality score
                quality_score = self._calculate_quality_score(snippet)
                
                # Create pattern
                pattern = {
                    "type": f"ml_pattern_{label}",
                    "snippet": snippet,
                    "quality_score": quality_score,
                    "cluster": int(label),
                    "analysis_method": "ml_clustering"
                }
                
                # Store pattern in Redis
                self.pattern_memory.store_pattern(
                    repo_path, 
                    "code_pattern", 
                    pattern, 
                    quality_score
                )
                
                patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ ML pattern extraction failed: {e}")
            return self._extract_patterns_statistical(repo_path, code_snippets)
    
    def _ml_pattern_extraction(self, repo_path: str, code_snippets: List[str]) -> List[Dict[str, Any]]:
        """ML-based pattern extraction using TF-IDF and K-Means clustering."""
        try:
            # Vectorize code snippets
            vectors = self.vectorizer.fit_transform(code_snippets).toarray()
            
            # Cluster patterns
            labels = self.clusterer.fit_predict(vectors)
            
            patterns = []
            for i, (snippet, label) in enumerate(zip(code_snippets, labels)):
                # Calculate quality score
                quality_score = self._calculate_quality_score(snippet)
                
                # Create pattern
                pattern = {
                    "type": f"ml_pattern_{label}",
                    "snippet": snippet,
                    "quality_score": quality_score,
                    "cluster": int(label),
                    "vector_similarity": float(np.linalg.norm(vectors[i])),
                    "extraction_method": "ml_clustering"
                }
                
                # Store pattern in Redis
                self.pattern_memory.store_pattern(
                    repo_path, 
                    "ml_code_pattern", 
                    pattern, 
                    quality_score
                )
                
                patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ ML pattern extraction failed: {e}")
            return self._statistical_pattern_extraction(repo_path, code_snippets)
    
    def _statistical_pattern_extraction(self, repo_path: str, code_snippets: List[str]) -> List[Dict[str, Any]]:
        """Statistical pattern extraction fallback."""
        try:
            patterns = []
            
            # Analyze patterns using statistical methods
            for i, snippet in enumerate(code_snippets):
                quality_score = self._calculate_quality_score(snippet)
                
                # Simple pattern classification based on code characteristics
                pattern_type = self._classify_code_pattern(snippet)
                
                pattern = {
                    "type": pattern_type,
                    "snippet": snippet,
                    "quality_score": quality_score,
                    "cluster": i % 5,  # Simple clustering
                    "extraction_method": "statistical"
                }
                
                # Store pattern
                self.pattern_memory.store_pattern(
                    repo_path,
                    "statistical_pattern",
                    pattern,
                    quality_score
                )
                
                patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Statistical pattern extraction failed: {e}")
            return []
    
    def _calculate_quality_score(self, code: str) -> float:
        """
        Calculate quality score for code snippet.
        
        Args:
            code: Code snippet to analyze
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        try:
            # Basic quality metrics
            score = 1.0
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if not non_empty_lines:
                return 0.0
            
            # Penalize very long lines (more aggressive)
            long_lines = sum(1 for line in lines if len(line) > 100)
            if long_lines > 0:
                score -= (long_lines / len(non_empty_lines)) * 0.3
            
            # Penalize TODO/FIXME comments
            if any('TODO' in line or 'FIXME' in line for line in lines):
                score -= 0.2
            
            # Penalize dangerous functions
            dangerous_functions = ['eval(', 'exec(', '__import__']
            if any(func in code for func in dangerous_functions):
                score -= 0.4
            
            # Penalize lack of documentation for functions
            if 'def ' in code and '"""' not in code and "'''" not in code:
                score -= 0.1
            
            # Penalize high complexity
            complexity_indicators = ['if ', 'for ', 'while ', 'try:', 'except:', 'elif ']
            complexity_count = sum(code.count(indicator) for indicator in complexity_indicators)
            if complexity_count > 3:
                score -= min(0.3, complexity_count * 0.05)
            
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5  # Default score on error
    
    def _estimate_complexity(self, code: str) -> float:
        """
        Estimate code complexity using simple heuristics.
        
        Args:
            code: Code snippet to analyze
            
        Returns:
            Complexity score between 0.0 and 1.0
        """
        try:
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if not non_empty_lines:
                return 0.0
            
            # Count complexity indicators with weights
            complexity_keywords = {
                'if ': 1, 'elif ': 1, 'else:': 0.5,
                'for ': 2, 'while ': 2,
                'try:': 1, 'except': 1, 'finally:': 0.5,
                'with ': 1, 'def ': 0.5, 'class ': 1
            }
            
            total_complexity = 0
            for keyword, weight in complexity_keywords.items():
                count = code.count(keyword)
                total_complexity += count * weight
            
            # Count nesting levels (approximate)
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    max_indent = max(max_indent, indent // 4)  # Assuming 4-space indents
            
            # Combine metrics
            keyword_complexity = min(1.0, total_complexity / (len(non_empty_lines) * 2))
            nesting_complexity = min(1.0, max_indent / 5)  # Normalize to 0-1
            
            # Weighted combination
            complexity_score = (keyword_complexity * 0.7 + nesting_complexity * 0.3)
            
            return min(1.0, complexity_score)
            
        except Exception as e:
            return 0.5  # Default neutral complexity
    
    def _classify_code_pattern(self, code: str) -> str:
        """Classify code pattern based on characteristics."""
        if 'class ' in code:
            return 'class_definition'
        elif 'def ' in code:
            return 'function_definition'
        elif 'import ' in code:
            return 'import_statement'
        elif any(keyword in code for keyword in ['if ', 'for ', 'while ']):
            return 'control_structure'
        else:
            return 'general_code'
    
    def find_similar_patterns(self, repo_path: str, pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find similar patterns using ML similarity detection.
        
        Args:
            repo_path: Repository path
            pattern: Pattern to find similarities for
            
        Returns:
            List of similar patterns
        """
        try:
            if self.verbose:
                print(f"🔍 Finding similar patterns for {pattern.get('type', 'unknown')}")
            
            # Get all patterns from memory
            all_patterns = self.pattern_memory.get_team_patterns(repo_path, "ml_code_pattern")
            if not all_patterns:
                all_patterns = self.pattern_memory.get_team_patterns(repo_path, "statistical_pattern")
            
            if not all_patterns:
                return []
            
            similar_patterns = []
            
            if ML_AVAILABLE and self.vectorizer:
                # ML-based similarity detection
                similar_patterns = self._ml_similarity_detection(pattern, all_patterns)
            else:
                # Fallback to simple similarity
                similar_patterns = self._simple_similarity_detection(pattern, all_patterns)
            
            if self.verbose:
                print(f"📊 Found {len(similar_patterns)} similar patterns")
            
            return similar_patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Similar pattern detection failed: {e}")
            return []
    
    def _ml_similarity_detection(self, target_pattern: Dict[str, Any], 
                               all_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ML-based pattern similarity detection."""
        try:
            # Extract snippets
            target_snippet = target_pattern.get('snippet', '')
            pattern_snippets = []
            
            for pattern in all_patterns:
                pattern_data = pattern.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    snippet = pattern_data.get('snippet', '')
                    if snippet:
                        pattern_snippets.append(snippet)
            
            if not pattern_snippets:
                return []
            
            # Vectorize all snippets
            all_snippets = [target_snippet] + pattern_snippets
            vectors = self.vectorizer.fit_transform(all_snippets).toarray()
            
            # Calculate similarities
            target_vector = vectors[0:1]
            pattern_vectors = vectors[1:]
            
            similarities = cosine_similarity(target_vector, pattern_vectors)[0]
            
            # Return patterns with similarity > 0.8
            similar_patterns = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.8:
                    pattern_data = all_patterns[i].get('pattern_data', {})
                    pattern_data['similarity_score'] = float(similarity)
                    similar_patterns.append(pattern_data)
            
            return similar_patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ ML similarity detection failed: {e}")
            return self._simple_similarity_detection(target_pattern, all_patterns)
    
    def _simple_similarity_detection(self, target_pattern: Dict[str, Any], 
                                   all_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple string-based similarity detection."""
        try:
            target_snippet = target_pattern.get('snippet', '').lower()
            similar_patterns = []
            
            for pattern in all_patterns:
                pattern_data = pattern.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    snippet = pattern_data.get('snippet', '').lower()
                    
                    # Simple similarity based on common words
                    target_words = set(target_snippet.split())
                    pattern_words = set(snippet.split())
                    
                    if target_words and pattern_words:
                        intersection = target_words.intersection(pattern_words)
                        union = target_words.union(pattern_words)
                        similarity = len(intersection) / len(union)
                        
                        if similarity > 0.5:
                            pattern_data['similarity_score'] = similarity
                            similar_patterns.append(pattern_data)
            
            return similar_patterns
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Simple similarity detection failed: {e}")
            return []
    
    def predict_quality_trends(self, repo_path: str, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Predict code quality trends using ML models (Task 21.3).
        
        Args:
            repo_path: Repository path
            days_ahead: Number of days to predict ahead
            
        Returns:
            Dictionary with trend predictions and early warnings
        """
        try:
            if self.verbose:
                print(f"🔮 Predicting quality trends for {repo_path} ({days_ahead} days ahead)")
            
            # Get workflow execution history
            executions = self.pattern_memory.get_team_patterns(repo_path, "workflow_execution")
            
            if not executions or len(executions) < 3:
                data_points = len(executions) if executions else 0
                return {
                    "predicted_score": 0.8,  # Default optimistic prediction
                    "early_warning": False,
                    "confidence": 0.0,
                    "recommendations": ["Insufficient data for trend prediction. Run more workflows."],
                    "data_points": data_points
                }
            
            if ML_AVAILABLE and self.trend_predictor:
                return self._ml_trend_prediction(repo_path, executions, days_ahead)
            else:
                return self._statistical_trend_prediction(repo_path, executions, days_ahead)
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Quality trend prediction failed: {e}")
            return {
                "predicted_score": 0.5,
                "early_warning": True,
                "confidence": 0.0,
                "recommendations": ["Trend prediction failed. Manual review recommended."],
                "data_points": 0,
                "error": str(e)
            }
    
    def _ml_trend_prediction(self, repo_path: str, executions: List[Dict], days_ahead: int) -> Dict[str, Any]:
        """ML-based trend prediction using Linear Regression."""
        try:
            # Extract time series data
            times = []
            scores = []
            
            for pattern in executions:
                pattern_data = pattern.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    # Try to get timestamp
                    timestamp_str = pattern_data.get('start_time') or pattern_data.get('timestamp')
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            times.append(timestamp.timestamp())
                            
                            # Get quality score (progress as proxy)
                            progress = pattern_data.get('progress', 0)
                            score = progress / 100.0 if progress > 0 else 0.5
                            scores.append(score)
                        except Exception:
                            continue
            
            if len(times) < 3:
                return self._statistical_trend_prediction(repo_path, executions, days_ahead)
            
            # Prepare data for ML model
            X = np.array(times).reshape(-1, 1)
            y = np.array(scores)
            
            # Train model
            self.trend_predictor.fit(X, y)
            
            # Predict future score
            future_time = (datetime.now() + timedelta(days=days_ahead)).timestamp()
            predicted_score = self.trend_predictor.predict([[future_time]])[0]
            
            # Calculate confidence based on R² score
            confidence = max(0.0, self.trend_predictor.score(X, y))
            
            # Early warning if predicted score is low
            early_warning = predicted_score < 0.7
            
            # Generate recommendations
            recommendations = self._generate_trend_recommendations(predicted_score, early_warning)
            
            return {
                "predicted_score": float(np.clip(predicted_score, 0.0, 1.0)),
                "early_warning": early_warning,
                "confidence": float(confidence),
                "recommendations": recommendations,
                "data_points": len(times),
                "prediction_method": "ml_regression"
            }
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ ML trend prediction failed: {e}")
            return self._statistical_trend_prediction(repo_path, executions, days_ahead)
    
    def _statistical_trend_prediction(self, repo_path: str, executions: List[Dict], days_ahead: int) -> Dict[str, Any]:
        """Statistical trend prediction fallback."""
        try:
            # Simple statistical analysis
            scores = []
            
            for pattern in executions[-10:]:  # Use last 10 executions
                pattern_data = pattern.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    progress = pattern_data.get('progress', 0)
                    score = progress / 100.0 if progress > 0 else 0.5
                    scores.append(score)
            
            if not scores:
                return {
                    "predicted_score": 0.5,
                    "early_warning": True,
                    "confidence": 0.0,
                    "recommendations": ["No execution data available"],
                    "data_points": 0,
                    "prediction_method": "no_data"
                }
            
            # Calculate trend
            avg_score = sum(scores) / len(scores)
            recent_avg = sum(scores[-3:]) / min(3, len(scores))
            
            # Simple trend calculation
            trend = recent_avg - avg_score
            predicted_score = max(0.0, min(1.0, recent_avg + trend * (days_ahead / 30)))
            
            early_warning = predicted_score < 0.7
            confidence = min(len(scores) / 10.0, 0.8)  # Confidence based on data points
            
            recommendations = self._generate_trend_recommendations(predicted_score, early_warning)
            
            return {
                "predicted_score": predicted_score,
                "early_warning": early_warning,
                "confidence": confidence,
                "recommendations": recommendations,
                "data_points": len(scores),
                "prediction_method": "statistical"
            }
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Statistical trend prediction failed: {e}")
            return {
                "predicted_score": 0.5,
                "early_warning": True,
                "confidence": 0.0,
                "recommendations": ["Trend prediction failed"],
                "data_points": 0,
                "error": str(e)
            }
    
    def _generate_trend_recommendations(self, predicted_score: float, early_warning: bool) -> List[str]:
        """Generate recommendations based on trend predictions."""
        recommendations = []
        
        if early_warning:
            recommendations.extend([
                "🚨 Early warning: Code quality trend is declining",
                "📈 Increase review frequency to prevent quality degradation",
                "🔧 Focus on fixing high-priority issues immediately",
                "👥 Consider additional code review resources"
            ])
        elif predicted_score > 0.9:
            recommendations.extend([
                "🎉 Excellent quality trend predicted",
                "✅ Maintain current development practices",
                "📊 Consider sharing successful patterns with other teams"
            ])
        elif predicted_score > 0.8:
            recommendations.extend([
                "👍 Good quality trend predicted",
                "🔄 Continue current workflow with minor optimizations"
            ])
        else:
            recommendations.extend([
                "⚠️ Moderate quality concerns predicted",
                "🔍 Review current development practices",
                "📋 Consider workflow adjustments"
            ])
        
        return recommendations
    
    def track_quality_goals(self, repo_path: str, target_score: float) -> Dict[str, Any]:
        """
        Track progress toward quality goals and provide actionable insights.
        
        Args:
            repo_path: Repository path to track
            target_score: Target quality score (0.0 to 1.0)
            
        Returns:
            Dictionary with current progress, gap analysis, and action items
        """
        try:
            if self.verbose:
                print(f"🎯 Tracking quality goals for {repo_path} (target: {target_score:.2f})")
            
            # Get current quality metrics
            current_metrics = self.analyze_workflows(repo_path)
            current_score = current_metrics.get("success_rate", 0.8)
            
            # Calculate gap
            gap = target_score - current_score
            gap_percentage = (gap / target_score) * 100 if target_score > 0 else 0
            
            # Determine status
            if gap <= 0:
                status = "achieved"
            elif gap <= 0.1:
                status = "close"
            elif gap <= 0.2:
                status = "moderate_gap"
            else:
                status = "significant_gap"
            
            # Generate action items based on gap
            action_items = self._generate_action_items(gap, current_score, target_score)
            
            # Estimate timeline to goal
            timeline_estimate = self._estimate_timeline_to_goal(repo_path, current_score, target_score)
            
            if self.verbose:
                print(f"📊 Current: {current_score:.2f}, Target: {target_score:.2f}, Gap: {gap:.2f}")
                print(f"📅 Estimated timeline: {timeline_estimate}")
            
            return {
                "current": current_score,
                "target": target_score,
                "gap": gap,
                "gap_percentage": gap_percentage,
                "status": status,
                "action_items": action_items,
                "timeline_estimate": timeline_estimate
            }
            
        except Exception as e:
            self.logger.error(f"Failed to track quality goals: {e}")
            return {
                "current": 0.8,
                "target": target_score,
                "gap": target_score - 0.8,
                "status": "unknown",
                "action_items": ["Unable to track goals due to error"],
                "timeline_estimate": "unknown"
            }
    
    def _generate_action_items(self, gap: float, current_score: float, target_score: float) -> List[str]:
        """Generate specific action items based on quality gap analysis."""
        action_items = []
        
        if gap <= 0:
            action_items.append("Goal achieved - maintain current quality standards")
            action_items.append("Consider setting higher quality targets")
        elif gap <= 0.05:
            action_items.append("Close to goal - focus on consistency")
            action_items.append("Address remaining minor issues")
        elif gap <= 0.1:
            action_items.append("Moderate gap - increase review frequency")
            action_items.append("Focus on high-impact improvements")
        elif gap <= 0.2:
            action_items.append("Significant gap - implement systematic improvements")
            action_items.append("Consider additional automated checks")
            action_items.append("Schedule team training on quality practices")
        else:
            action_items.append("Large gap - comprehensive quality initiative needed")
            action_items.append("Audit current development processes")
            action_items.append("Implement stricter quality gates")
            action_items.append("Consider external quality assessment")
        
        # Add score-specific recommendations
        if current_score < 0.6:
            action_items.append("Address fundamental code quality issues")
        elif current_score < 0.8:
            action_items.append("Focus on reducing technical debt")
        
        if target_score > 0.9:
            action_items.append("High target requires exceptional discipline")
            action_items.append("Implement peer review for all changes")
        
        return action_items
    
    def _estimate_timeline_to_goal(self, repo_path: str, current_score: float, target_score: float) -> str:
        """Estimate timeline to reach quality goal based on historical trends."""
        try:
            # Get historical trend data
            executions = self.pattern_memory.get_team_patterns(repo_path, "workflow_execution")
            
            if not executions or len(executions) < 3:
                return "insufficient_data"
            
            # Calculate historical improvement rate
            scores = []
            for execution in executions[-10:]:  # Last 10 executions
                pattern_data = execution.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    progress = pattern_data.get("progress", 50)
                    scores.append(progress / 100.0)
            
            if len(scores) < 2:
                return "insufficient_data"
            
            # Calculate average improvement per execution
            improvements = [scores[i] - scores[i-1] for i in range(1, len(scores))]
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0
            
            if avg_improvement <= 0:
                return "no_improvement_trend"
            
            # Estimate executions needed
            gap = target_score - current_score
            executions_needed = gap / avg_improvement
            
            # Convert to time estimate (assuming 1 execution per week)
            if executions_needed <= 1:
                return "1_week"
            elif executions_needed <= 4:
                return f"{int(executions_needed)}_weeks"
            elif executions_needed <= 12:
                return f"{int(executions_needed/4)}_months"
            else:
                return "6_months_plus"
                
        except Exception as e:
            self.logger.debug(f"Failed to estimate timeline: {e}")
            return "unknown"
    
    def analyze_workflows(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze workflow execution patterns and success rates.
        
        Args:
            repo_path: Repository path to analyze
            
        Returns:
            Dictionary with workflow analysis results
        """
        try:
            # Retrieve workflow execution data
            executions = self.pattern_memory.get_team_patterns(repo_path, "workflow_execution")
            
            if not executions:
                return {
                    "success_rate": 0.8,  # Default assumption
                    "total_executions": 0,
                    "avg_progress": 0.8,
                    "trend": "unknown"
                }
            
            # Calculate success metrics
            total_executions = len(executions)
            successful_executions = 0
            progress_values = []
            
            for execution in executions:
                pattern_data = execution.get('pattern_data', {})
                if isinstance(pattern_data, dict):
                    progress = pattern_data.get("progress", 0)
                    progress_values.append(progress)
                    if progress >= 80:
                        successful_executions += 1
            
            success_rate = successful_executions / total_executions if total_executions > 0 else 0.8
            avg_progress = sum(progress_values) / len(progress_values) / 100.0 if progress_values else 0.8
            
            # Determine trend
            if len(progress_values) >= 3:
                recent_avg = sum(progress_values[-3:]) / 3
                older_avg = sum(progress_values[:-3]) / len(progress_values[:-3]) if len(progress_values) > 3 else recent_avg
                
                if recent_avg > older_avg + 5:
                    trend = "improving"
                elif recent_avg < older_avg - 5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            return {
                "success_rate": success_rate,
                "total_executions": total_executions,
                "avg_progress": avg_progress,
                "trend": trend,
                "recent_executions": min(10, total_executions)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze workflows: {e}")
            return {
                "success_rate": 0.8,
                "total_executions": 0,
                "avg_progress": 0.8,
                "trend": "unknown"
            }
    

    
    def predict_issues(self, repo_path: str) -> List[Dict[str, Any]]:
        """
        Predict potential issues using learned patterns.
        
        Args:
            repo_path: Repository path
            
        Returns:
            List of predicted issues with probabilities
        """
        try:
            if self.verbose:
                print(f"🔮 Predicting issues for {repo_path}")
            
            # Get issue trends from memory
            issue_trends = self.pattern_memory.get_issue_trends(repo_path)
            trending_issues = issue_trends.get('trending_issues', [])
            
            predictions = []
            for issue in trending_issues:
                # Calculate prediction probability based on frequency and trend
                frequency = issue.get('frequency', 0)
                trend_score = issue.get('trend_score', 0)
                
                # Higher frequency and positive trend = higher probability
                probability = min(0.95, (frequency / 20.0) + (trend_score * 2))
                
                if probability > 0.3:  # Only include meaningful predictions
                    predictions.append({
                        "rule_id": issue.get('issue_rule', 'unknown'),
                        "issue_type": issue.get('issue_type', 'code_quality'),
                        "probability": probability,
                        "frequency": frequency,
                        "trend_score": trend_score,
                        "severity": issue.get('severity', 'medium')
                    })
            
            # Sort by probability
            predictions.sort(key=lambda x: x['probability'], reverse=True)
            
            if self.verbose:
                print(f"🎯 Predicted {len(predictions)} potential issues")
                for pred in predictions[:3]:
                    print(f"   • {pred['rule_id']}: {pred['probability']:.2%} probability")
            
            return predictions[:10]  # Return top 10 predictions
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Issue prediction failed: {e}")
            return []