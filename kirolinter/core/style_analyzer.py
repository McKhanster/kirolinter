"""
Team style analyzer that learns coding patterns from commit history.
"""

import re
import ast
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import subprocess

try:
    import git
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class CommitAnalyzer:
    """Analyzes individual commits for coding patterns."""
    
    def __init__(self):
        self.naming_patterns = defaultdict(Counter)
        self.structure_patterns = defaultdict(Counter)
        self.import_patterns = defaultdict(Counter)
    
    def analyze_commit_diff(self, diff_text: str) -> Dict[str, Any]:
        """
        Analyze a commit diff for coding patterns.
        
        Args:
            diff_text: Git diff text
        
        Returns:
            Dictionary containing extracted patterns
        """
        patterns = {
            'naming_conventions': {},
            'code_structure': {},
            'import_style': {}
        }
        
        # Extract added lines (starting with +)
        added_lines = []
        for line in diff_text.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:].strip())
        
        # Analyze naming conventions
        patterns['naming_conventions'] = self._analyze_naming_conventions(added_lines)
        
        # Analyze code structure
        patterns['code_structure'] = self._analyze_code_structure(added_lines)
        
        # Analyze import style
        patterns['import_style'] = self._analyze_import_style(added_lines)
        
        return patterns
    
    def _analyze_naming_conventions(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze naming conventions from code lines."""
        patterns = {
            'variables': Counter(),
            'functions': Counter(),
            'classes': Counter(),
            'constants': Counter(),
            'private_methods': Counter()
        }
        
        for line in lines:
            # Skip comments and empty lines
            if not line or line.strip().startswith('#'):
                continue
            
            try:
                # Try to parse as Python code
                tree = ast.parse(line)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        name_style = self._classify_naming_style(node.name)
                        if node.name.startswith('_'):
                            patterns['private_methods'][name_style] += 1
                        else:
                            patterns['functions'][name_style] += 1
                    
                    elif isinstance(node, ast.ClassDef):
                        name_style = self._classify_naming_style(node.name)
                        patterns['classes'][name_style] += 1
                    
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                name_style = self._classify_naming_style(name)
                                
                                if name.isupper():
                                    patterns['constants'][name_style] += 1
                                else:
                                    patterns['variables'][name_style] += 1
            
            except (SyntaxError, ValueError):
                # If parsing fails, use regex patterns
                self._analyze_naming_with_regex(line, patterns)
        
        return patterns
    
    def _analyze_code_structure(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze code structure patterns."""
        patterns = {
            'function_length': [],
            'complexity_indicators': Counter(),
            'return_style': Counter(),
            'comprehension_usage': Counter(),
            'error_handling': Counter()
        }
        
        current_function_lines = 0
        in_function = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track function definitions
            if stripped.startswith('def '):
                if in_function:
                    patterns['function_length'].append(current_function_lines)
                in_function = True
                current_function_lines = 1
            elif in_function:
                if stripped and not stripped.startswith('#'):
                    current_function_lines += 1
                
                # Check for early returns
                if stripped.startswith('return '):
                    patterns['return_style']['early_return'] += 1
                elif 'return ' in stripped and stripped.endswith(':'):
                    patterns['return_style']['conditional_return'] += 1
            
            # Check for list comprehensions
            if '[' in stripped and 'for ' in stripped and 'in ' in stripped:
                patterns['comprehension_usage']['list_comprehension'] += 1
            elif '{' in stripped and 'for ' in stripped and 'in ' in stripped:
                patterns['comprehension_usage']['dict_comprehension'] += 1
            
            # Check for error handling patterns
            if stripped.startswith('try:'):
                patterns['error_handling']['try_except'] += 1
            elif stripped.startswith('except'):
                if ':' in stripped and stripped.count(':') == 1:
                    patterns['error_handling']['specific_except'] += 1
                else:
                    patterns['error_handling']['bare_except'] += 1
        
        if in_function:
            patterns['function_length'].append(current_function_lines)
        
        return patterns
    
    def _analyze_import_style(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze import style patterns."""
        patterns = {
            'import_types': Counter(),
            'import_grouping': [],
            'import_sorting': Counter(),
            'from_imports': Counter()
        }
        
        import_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_lines.append(stripped)
        
        # Analyze import types
        for import_line in import_lines:
            if import_line.startswith('from '):
                patterns['import_types']['from_import'] += 1
                # Check for relative imports
                if import_line.startswith('from .'):
                    patterns['from_imports']['relative'] += 1
                else:
                    patterns['from_imports']['absolute'] += 1
            else:
                patterns['import_types']['direct_import'] += 1
        
        # Check for import grouping (consecutive imports)
        if len(import_lines) > 1:
            patterns['import_grouping'].append(len(import_lines))
        
        return patterns
    
    def _classify_naming_style(self, name: str) -> str:
        """Classify naming style of a given name."""
        if not name:
            return 'unknown'
        
        if name.isupper():
            return 'UPPER_SNAKE_CASE'
        elif '_' in name and name.islower():
            return 'snake_case'
        elif name[0].isupper() and any(c.isupper() for c in name[1:]):
            return 'PascalCase'
        elif name[0].islower() and any(c.isupper() for c in name[1:]):
            return 'camelCase'
        elif name.islower():
            return 'lowercase'
        else:
            return 'mixed'
    
    def _analyze_naming_with_regex(self, line: str, patterns: Dict[str, Counter]):
        """Fallback regex-based naming analysis."""
        # Function definitions
        func_match = re.search(r'def\s+(\w+)\s*\(', line)
        if func_match:
            name = func_match.group(1)
            style = self._classify_naming_style(name)
            if name.startswith('_'):
                patterns['private_methods'][style] += 1
            else:
                patterns['functions'][style] += 1
        
        # Class definitions
        class_match = re.search(r'class\s+(\w+)', line)
        if class_match:
            name = class_match.group(1)
            style = self._classify_naming_style(name)
            patterns['classes'][style] += 1
        
        # Variable assignments
        var_matches = re.findall(r'(\w+)\s*=', line)
        for name in var_matches:
            style = self._classify_naming_style(name)
            if name.isupper():
                patterns['constants'][style] += 1
            else:
                patterns['variables'][style] += 1


class TeamStyleAnalyzer:
    """Main class for analyzing team coding style from repository history."""
    
    def __init__(self, repo_path: str, config: Dict[str, Any] = None):
        """
        Initialize team style analyzer.
        
        Args:
            repo_path: Path to the Git repository
            config: Configuration for analysis
        """
        self.repo_path = repo_path
        self.config = config or {}
        self.commit_analyzer = CommitAnalyzer()
        
        # Analysis settings
        self.max_commits = self.config.get('analyze_last_n_commits', 100)
        self.min_frequency = self.config.get('min_pattern_frequency', 0.7)
        self.exclude_merges = self.config.get('exclude_merge_commits', True)
        self.exclude_authors = self.config.get('exclude_authors', ['dependabot', 'renovate'])
        
        # Accumulated patterns
        self.team_patterns = {
            'naming_conventions': defaultdict(Counter),
            'code_structure': defaultdict(list),
            'import_style': defaultdict(Counter)
        }
    
    def analyze_repository(self) -> Dict[str, Any]:
        """
        Analyze the entire repository for team coding patterns.
        
        Returns:
            Dictionary containing team style preferences
        """
        if not GIT_AVAILABLE:
            print("Warning: GitPython not available, using default patterns")
            return self._get_default_patterns()
        
        try:
            repo = Repo(self.repo_path)
            commits = self._get_relevant_commits(repo)
            
            print(f"Analyzing {len(commits)} commits for team patterns...")
            
            for commit in commits:
                self._analyze_commit(repo, commit)
            
            return self._extract_team_preferences()
            
        except Exception as e:
            print(f"Error analyzing repository: {e}")
            return self._get_default_patterns()
    
    def _get_relevant_commits(self, repo: Repo) -> List[Any]:
        """Get commits relevant for analysis."""
        commits = []
        
        try:
            for commit in repo.iter_commits(max_count=self.max_commits):
                # Skip merge commits if configured
                if self.exclude_merges and len(commit.parents) > 1:
                    continue
                
                # Skip excluded authors
                if commit.author.name.lower() in [author.lower() for author in self.exclude_authors]:
                    continue
                
                # Only analyze commits that modify Python files
                if self._commit_modifies_python(commit):
                    commits.append(commit)
        
        except Exception as e:
            print(f"Error getting commits: {e}")
        
        return commits
    
    def _commit_modifies_python(self, commit) -> bool:
        """Check if commit modifies Python files."""
        try:
            for item in commit.stats.files:
                if item.endswith('.py'):
                    return True
        except:
            pass
        return False
    
    def _analyze_commit(self, repo: Repo, commit):
        """Analyze a single commit for patterns."""
        try:
            # Get diff for Python files only
            if commit.parents:
                diff = repo.git.diff(commit.parents[0], commit, '--', '*.py')
            else:
                # First commit
                diff = repo.git.show(commit, '--format=', '--', '*.py')
            
            if diff:
                patterns = self.commit_analyzer.analyze_commit_diff(diff)
                self._accumulate_patterns(patterns)
                
        except Exception as e:
            print(f"Error analyzing commit {commit.hexsha[:8]}: {e}")
    
    def _accumulate_patterns(self, patterns: Dict[str, Any]):
        """Accumulate patterns from a single commit."""
        # Accumulate naming conventions
        for category, counter in patterns['naming_conventions'].items():
            for style, count in counter.items():
                self.team_patterns['naming_conventions'][category][style] += count
        
        # Accumulate code structure
        for category, data in patterns['code_structure'].items():
            if isinstance(data, list):
                self.team_patterns['code_structure'][category].extend(data)
            elif isinstance(data, Counter):
                for item, count in data.items():
                    self.team_patterns['code_structure'][category][item] += count
        
        # Accumulate import style
        for category, counter in patterns['import_style'].items():
            if isinstance(counter, Counter):
                for style, count in counter.items():
                    self.team_patterns['import_style'][category][style] += count
            elif isinstance(counter, list):
                self.team_patterns['import_style'][category].extend(counter)
    
    def _extract_team_preferences(self) -> Dict[str, Any]:
        """Extract team preferences from accumulated patterns."""
        preferences = {
            'naming_conventions': {},
            'code_structure': {},
            'import_style': {},
            'confidence_scores': {}
        }
        
        # Extract naming preferences
        for category, counter in self.team_patterns['naming_conventions'].items():
            if counter:
                most_common = counter.most_common(1)[0]
                total = sum(counter.values())
                confidence = most_common[1] / total if total > 0 else 0
                
                if confidence >= self.min_frequency:
                    preferences['naming_conventions'][category] = most_common[0]
                    preferences['confidence_scores'][f'naming_{category}'] = confidence
        
        # Extract structure preferences
        structure_patterns = self.team_patterns['code_structure']
        
        # Function length preference
        if 'function_length' in structure_patterns and structure_patterns['function_length']:
            lengths = structure_patterns['function_length']
            avg_length = sum(lengths) / len(lengths)
            preferences['code_structure']['preferred_function_length'] = int(avg_length)
        
        # Return style preference
        if 'return_style' in structure_patterns:
            return_counter = structure_patterns['return_style']
            if return_counter:
                most_common = return_counter.most_common(1)[0]
                total = sum(return_counter.values())
                confidence = most_common[1] / total if total > 0 else 0
                
                if confidence >= self.min_frequency:
                    preferences['code_structure']['preferred_return_style'] = most_common[0]
                    preferences['confidence_scores']['return_style'] = confidence
        
        # Comprehension usage
        if 'comprehension_usage' in structure_patterns:
            comp_counter = structure_patterns['comprehension_usage']
            total_comp = sum(comp_counter.values())
            if total_comp > 0:
                preferences['code_structure']['uses_comprehensions'] = total_comp > 5
                preferences['confidence_scores']['comprehensions'] = min(total_comp / 20, 1.0)
        
        # Extract import preferences
        import_patterns = self.team_patterns['import_style']
        
        if 'import_types' in import_patterns:
            import_counter = import_patterns['import_types']
            if import_counter:
                from_imports = import_counter.get('from_import', 0)
                direct_imports = import_counter.get('direct_import', 0)
                total = from_imports + direct_imports
                
                if total > 0:
                    preferences['import_style']['prefers_from_imports'] = from_imports > direct_imports
                    preferences['confidence_scores']['import_style'] = max(from_imports, direct_imports) / total
        
        return preferences
    
    def _get_default_patterns(self) -> Dict[str, Any]:
        """Get default patterns when analysis fails."""
        return {
            'naming_conventions': {
                'variables': 'snake_case',
                'functions': 'snake_case',
                'classes': 'PascalCase',
                'constants': 'UPPER_SNAKE_CASE'
            },
            'code_structure': {
                'preferred_function_length': 20,
                'preferred_return_style': 'early_return',
                'uses_comprehensions': True
            },
            'import_style': {
                'prefers_from_imports': True
            },
            'confidence_scores': {
                'naming_variables': 0.5,
                'naming_functions': 0.5,
                'naming_classes': 0.5,
                'default_patterns': True
            }
        }
    
    def get_style_recommendations(self, current_patterns: Dict[str, Any]) -> List[str]:
        """
        Get recommendations based on team style analysis.
        
        Args:
            current_patterns: Current code patterns to compare against
        
        Returns:
            List of style recommendations
        """
        team_prefs = self.analyze_repository()
        recommendations = []
        
        # Check naming conventions
        team_naming = team_prefs.get('naming_conventions', {})
        current_naming = current_patterns.get('naming_conventions', {})
        
        for category, preferred_style in team_naming.items():
            current_style = current_naming.get(category)
            if current_style and current_style != preferred_style:
                confidence = team_prefs['confidence_scores'].get(f'naming_{category}', 0)
                if confidence > 0.7:
                    recommendations.append(
                        f"Consider using {preferred_style} for {category} "
                        f"(team uses this {confidence:.0%} of the time)"
                    )
        
        # Check code structure
        team_structure = team_prefs.get('code_structure', {})
        
        if 'preferred_function_length' in team_structure:
            preferred_length = team_structure['preferred_function_length']
            recommendations.append(
                f"Team prefers functions around {preferred_length} lines long"
            )
        
        if team_structure.get('uses_comprehensions'):
            recommendations.append(
                "Team frequently uses list/dict comprehensions - consider using them for better readability"
            )
        
        return recommendations