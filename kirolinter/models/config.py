"""
Configuration models for KiroLinter.
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class Config:
    """Configuration for KiroLinter analysis."""
    
    enabled_rules: List[str] = field(default_factory=lambda: [
        'unused_variable', 'unused_import', 'dead_code', 'complex_function',
        'sql_injection', 'hardcoded_secret', 'unsafe_eval', 'unsafe_exec',
        'inefficient_loop_concat', 'redundant_len_in_loop'
    ])
    
    min_severity: str = 'low'
    exclude_patterns: List[str] = field(default_factory=lambda: [
        '__pycache__', '.git', '.venv', 'venv', 'env', '.tox', 
        'build', 'dist', '.pytest_cache', 'node_modules'
    ])
    
    max_complexity: int = 10
    max_line_length: int = 88
    
    # GitHub integration settings
    github_token: str = ''
    github_repo: str = ''
    
    # AI settings
    openai_api_key: str = ''
    use_ai_suggestions: bool = True
    fallback_to_rules: bool = True
    
    # Team Style Preferences (learned from commit history)
    team_style: Dict[str, Any] = field(default_factory=lambda: {
        "naming_conventions": {
            "variables": "snake_case",
            "functions": "snake_case", 
            "classes": "PascalCase",
            "constants": "UPPER_SNAKE_CASE",
            "private_methods": "_snake_case",
            "module_names": "snake_case"
        },
        "import_style": {
            "prefer_absolute": True,
            "group_imports": True,
            "sort_imports": True,
            "max_imports_per_line": 1,
            "import_order": ["standard", "third_party", "local"]
        },
        "code_structure": {
            "max_line_length": 88,
            "prefer_list_comprehensions": True,
            "max_function_complexity": 10,
            "prefer_early_returns": True,
            "max_function_length": 50,
            "prefer_explicit_returns": True
        },
        "security_preferences": {
            "env_var_prefix": "APP_",
            "prefer_secrets_manager": False,
            "require_type_hints": False,
            "allowed_eval_contexts": [],
            "require_input_validation": True
        },
        "commit_analysis": {
            "analyze_last_n_commits": 100,
            "min_pattern_frequency": 0.7,
            "exclude_merge_commits": True,
            "exclude_authors": ["dependabot", "renovate"]
        }
    })
    
    # GitHub Integration Settings
    github_integration: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "token": "",
        "repository": "",
        "post_pr_comments": True,
        "post_summary_comment": True,
        "create_status_checks": True,
        "comment_on_lines": True,
        "max_comments_per_pr": 50
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'enabled_rules': self.enabled_rules,
            'min_severity': self.min_severity,
            'exclude_patterns': self.exclude_patterns,
            'max_complexity': self.max_complexity,
            'max_line_length': self.max_line_length,
            'github_token': self.github_token,
            'github_repo': self.github_repo,
            'openai_api_key': self.openai_api_key,
            'use_ai_suggestions': self.use_ai_suggestions,
            'fallback_to_rules': self.fallback_to_rules,
            'team_style': self.team_style,
            'github_integration': self.github_integration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary."""
        default_config = cls()
        return cls(
            enabled_rules=data.get('enabled_rules', default_config.enabled_rules),
            min_severity=data.get('min_severity', 'low'),
            exclude_patterns=data.get('exclude_patterns', default_config.exclude_patterns),
            max_complexity=data.get('max_complexity', 10),
            max_line_length=data.get('max_line_length', 88),
            github_token=data.get('github_token', ''),
            github_repo=data.get('github_repo', ''),
            openai_api_key=data.get('openai_api_key', ''),
            use_ai_suggestions=data.get('use_ai_suggestions', True),
            fallback_to_rules=data.get('fallback_to_rules', True),
            team_style=data.get('team_style', default_config.team_style),
            github_integration=data.get('github_integration', default_config.github_integration)
        )
    
    @classmethod
    def load(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    def save(self, config_path: Path):
        """Save configuration to YAML file."""
        with open(config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    @classmethod
    def default(cls) -> 'Config':
        """Create default configuration."""
        return cls()