"""
AI-powered suggestion engine with rule-based fallback system.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from kirolinter.models.issue import Issue
from kirolinter.models.suggestion import Suggestion, FixType


class RuleBasedSuggester:
    """Rule-based suggestion engine using predefined templates."""
    
    def __init__(self, templates_path: Optional[str] = None):
        self.templates_path = templates_path or self._get_default_templates_path()
        self.templates = self._load_templates()
    
    def _get_default_templates_path(self) -> str:
        """Get the default path for suggestion templates."""
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "config" / "templates")
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load suggestion templates from configuration files."""
        templates = {}
        
        # Default templates (embedded)
        default_templates = {
            "unused_variable": {
                "fix_type": "DELETE",
                "confidence": 0.9,
                "template": "Remove the unused variable assignment on line {line_number}.",
                "explanation": "This variable is assigned but never used, which can be safely removed to clean up the code."
            },
            "unused_import": {
                "fix_type": "DELETE", 
                "confidence": 0.95,
                "template": "Remove the unused import statement on line {line_number}.",
                "explanation": "This import is not used anywhere in the file and can be safely removed."
            },
            "dead_code": {
                "fix_type": "DELETE",
                "confidence": 0.8,
                "template": "Remove the unreachable code on line {line_number}.",
                "explanation": "This code appears after a return statement and will never be executed."
            },
            "hardcoded_secret": {
                "fix_type": "REPLACE",
                "confidence": 0.85,
                "template": "Replace hardcoded secret with environment variable: os.environ.get('{env_var}', 'your_secret_here')",
                "explanation": "Hardcoded secrets pose security risks. Use environment variables to store sensitive data securely.",
                "code_template": "os.environ.get('{env_var}', 'default_value')"
            },
            "hardcoded_password": {
                "fix_type": "REPLACE",
                "confidence": 0.9,
                "template": "Replace hardcoded password with environment variable: os.environ.get('PASSWORD', 'default')",
                "explanation": "Passwords should never be hardcoded. Use environment variables or secure configuration.",
                "code_template": "os.environ.get('PASSWORD', 'your_password_here')"
            },
            "hardcoded_api_key": {
                "fix_type": "REPLACE",
                "confidence": 0.9,
                "template": "Replace hardcoded API key with environment variable: os.environ.get('API_KEY', 'default')",
                "explanation": "API keys should be stored in environment variables to prevent unauthorized access.",
                "code_template": "os.environ.get('API_KEY', 'your_api_key_here')"
            },
            "sql_injection": {
                "fix_type": "REPLACE",
                "confidence": 0.85,
                "template": "Use parameterized queries: cursor.execute('SELECT * FROM table WHERE id = ?', (value,))",
                "explanation": "String formatting in SQL queries can lead to SQL injection vulnerabilities. Use parameterized queries.",
                "code_template": "cursor.execute('SELECT * FROM table WHERE column = ?', (value,))"
            },
            "unsafe_eval": {
                "fix_type": "REPLACE",
                "confidence": 0.9,
                "template": "Replace eval() with safer alternatives like json.loads() or ast.literal_eval().",
                "explanation": "eval() can execute arbitrary code and poses security risks."
            },
            "unsafe_exec": {
                "fix_type": "REPLACE",
                "confidence": 0.9,
                "template": "Avoid using exec() or validate input thoroughly before execution.",
                "explanation": "exec() can execute arbitrary code and poses security risks."
            },
            "complex_function": {
                "fix_type": "REFACTOR",
                "confidence": 0.6,
                "template": "Consider breaking this function into smaller, more focused functions.",
                "explanation": "Functions with high complexity are harder to understand and maintain."
            },
            "inefficient_loop_concat": {
                "fix_type": "REPLACE",
                "confidence": 0.8,
                "template": "Use list comprehension or str.join() instead of concatenation in loops.",
                "explanation": "String concatenation in loops is inefficient due to string immutability."
            },
            "redundant_len_in_loop": {
                "fix_type": "REPLACE",
                "confidence": 0.7,
                "template": "Cache the len() result outside the loop: length = len(container)",
                "explanation": "Calling len() repeatedly in loop conditions is inefficient."
            }
        }
        
        templates.update(default_templates)
        
        # Try to load external templates if available
        try:
            templates_dir = Path(self.templates_path)
            if templates_dir.exists():
                for template_file in templates_dir.glob("*.json"):
                    with open(template_file, 'r') as f:
                        external_templates = json.load(f)
                        templates.update(external_templates)
        except Exception:
            pass  # Use default templates if loading fails
        
        return templates
    
    def generate_suggestion(self, issue: Issue) -> Optional[Suggestion]:
        """
        Generate a rule-based suggestion for an issue.
        
        Args:
            issue: Issue to generate suggestion for
        
        Returns:
            Suggestion object or None if no template available
        """
        template = self.templates.get(issue.rule_id)
        if not template:
            return None
        
        # Generate suggestion based on template
        fix_type = FixType(template["fix_type"].lower())
        confidence = template["confidence"]
        
        # Format template with issue-specific data
        suggestion_text = template["template"].format(
            line_number=issue.line_number,
            env_var=self._generate_env_var_name(issue),
            file_path=issue.file_path
        )
        
        # Generate code suggestion based on issue type
        suggested_code = self._generate_code_suggestion(issue, template)
        
        return Suggestion(
            issue_id=issue.id,
            fix_type=fix_type,
            original_code=self._get_original_code(issue),
            suggested_code=suggested_code,
            confidence=confidence,
            explanation=template["explanation"]
        )
    
    def _generate_env_var_name(self, issue: Issue) -> str:
        """Generate environment variable name from issue context."""
        # Extract variable name from issue message
        if "'" in issue.message:
            var_name = issue.message.split("'")[1]
            return var_name.upper().replace(' ', '_')
        return "SECRET_KEY"
    
    def _generate_code_suggestion(self, issue: Issue, template: Dict[str, Any]) -> str:
        """Generate specific code suggestion based on issue and template."""
        if issue.rule_id == "unused_variable":
            return ""  # Remove the line
        elif issue.rule_id == "unused_import":
            return ""  # Remove the line
        elif issue.rule_id in ["hardcoded_secret", "hardcoded_password", "hardcoded_api_key"]:
            env_var = self._generate_env_var_name(issue)
            code_template = template.get("code_template", 'os.environ.get("{env_var}", "default")')
            return code_template.format(env_var=env_var)
        elif issue.rule_id == "sql_injection":
            # Try to detect the database library and suggest appropriate parameterization
            original_code = self._get_original_code(issue)
            if "sqlite3" in original_code or "cursor.execute" in original_code:
                return "cursor.execute(\"SELECT * FROM table WHERE column = ?\", (value,))"
            elif "psycopg2" in original_code:
                return "cursor.execute(\"SELECT * FROM table WHERE column = %s\", (value,))"
            else:
                return template.get("code_template", "cursor.execute('SELECT * FROM table WHERE column = ?', (value,))")
        elif issue.rule_id == "unsafe_eval":
            return "json.loads(user_input)  # or ast.literal_eval(user_input) for literals"
        elif issue.rule_id == "unsafe_exec":
            return "# Consider safer alternatives: subprocess.run() for commands, importlib for modules"
        elif issue.rule_id == "dead_code":
            return ""  # Remove the dead code
        else:
            return template.get("code_template", "# See suggestion explanation for details")
    
    def _get_original_code(self, issue: Issue) -> str:
        """Get the original code line for the issue."""
        try:
            with open(issue.file_path, 'r') as f:
                lines = f.readlines()
                if 0 <= issue.line_number - 1 < len(lines):
                    return lines[issue.line_number - 1].strip()
        except Exception:
            pass
        return ""


class OpenAISuggester:
    """AI-powered suggestion engine using OpenAI API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client if API key is available."""
        if not self.api_key:
            return
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            print("Warning: OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI client: {e}")
    
    def generate_suggestion(self, issue: Issue, context: str = "") -> Optional[Suggestion]:
        """
        Generate AI-powered suggestion for an issue.
        
        Args:
            issue: Issue to generate suggestion for
            context: Additional context about the code
        
        Returns:
            Suggestion object or None if generation fails
        """
        if not self.client:
            return None
        
        try:
            # Prepare prompt for OpenAI
            prompt = self._create_prompt(issue, context)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a code review assistant that provides specific, actionable suggestions for fixing code issues."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            suggestion_text = response.choices[0].message.content.strip()
            
            # Parse the response and create suggestion
            return self._parse_ai_response(issue, suggestion_text)
            
        except Exception as e:
            print(f"Warning: OpenAI suggestion generation failed: {e}")
            return None
    
    def _create_prompt(self, issue: Issue, context: str) -> str:
        """Create a prompt for OpenAI based on the issue."""
        original_code = self._get_original_code(issue)
        
        prompt = f"""
Code Issue Analysis:
- File: {issue.file_path}
- Line: {issue.line_number}
- Issue Type: {issue.type.value}
- Rule: {issue.rule_id}
- Message: {issue.message}

Original Code:
{original_code}

Context:
{context}

Please provide a specific code suggestion to fix this issue. Include:
1. The corrected code
2. A brief explanation of the fix
3. Confidence level (0.0-1.0)

Format your response as:
SUGGESTED_CODE: [your code here]
EXPLANATION: [brief explanation]
CONFIDENCE: [0.0-1.0]
"""
        return prompt
    
    def _parse_ai_response(self, issue: Issue, response: str) -> Suggestion:
        """Parse OpenAI response into a Suggestion object."""
        lines = response.split('\n')
        
        suggested_code = ""
        explanation = ""
        confidence = 0.7  # Default confidence
        
        for line in lines:
            if line.startswith("SUGGESTED_CODE:"):
                suggested_code = line.replace("SUGGESTED_CODE:", "").strip()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.7
        
        return Suggestion(
            issue_id=issue.id,
            fix_type=FixType.REPLACE,  # Default to replace
            original_code=self._get_original_code(issue),
            suggested_code=suggested_code,
            confidence=confidence,
            explanation=explanation or "AI-generated suggestion"
        )
    
    def _get_original_code(self, issue: Issue) -> str:
        """Get the original code line for the issue."""
        try:
            with open(issue.file_path, 'r') as f:
                lines = f.readlines()
                if 0 <= issue.line_number - 1 < len(lines):
                    return lines[issue.line_number - 1].strip()
        except Exception:
            pass
        return ""


class TeamStyleAnalyzer:
    """Analyze team coding style for personalized suggestions."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.style_patterns = {}
        self.team_preferences = self.analyze_team_style()
    
    def analyze_team_style(self) -> Dict[str, Any]:
        """
        Analyze team coding style from commit history.
        
        Returns:
            Dictionary containing style patterns and preferences
        """
        # Enhanced stub implementation with more realistic patterns
        return {
            "naming_conventions": {
                "variables": "snake_case",
                "functions": "snake_case", 
                "classes": "PascalCase",
                "constants": "UPPER_SNAKE_CASE"
            },
            "import_style": {
                "prefer_absolute": True,
                "group_imports": True,
                "sort_imports": True,
                "max_imports_per_line": 1
            },
            "code_structure": {
                "max_line_length": 88,
                "prefer_list_comprehensions": True,
                "max_function_complexity": 10,
                "prefer_early_returns": True
            },
            "security_preferences": {
                "env_var_prefix": "APP_",
                "prefer_secrets_manager": False,
                "require_type_hints": True
            },
            "priority_rules": {
                "security": 1.0,  # Highest priority
                "performance": 0.8,
                "code_smell": 0.6
            }
        }
    
    def prioritize_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Prioritize suggestions based on team style preferences and issue severity.
        
        Args:
            suggestions: List of suggestions to prioritize
        
        Returns:
            Prioritized list of suggestions
        """
        def calculate_priority(suggestion: Suggestion) -> float:
            """Calculate priority score for a suggestion."""
            base_confidence = suggestion.confidence
            
            # Get issue from suggestion ID to determine type
            issue_type = "code_smell"  # Default
            if "security" in suggestion.issue_id or "secret" in suggestion.issue_id:
                issue_type = "security"
            elif "performance" in suggestion.issue_id or "inefficient" in suggestion.issue_id:
                issue_type = "performance"
            
            # Apply team priority multiplier
            priority_multiplier = self.team_preferences["priority_rules"].get(issue_type, 0.5)
            
            # Boost priority for certain patterns team prefers
            if suggestion.fix_type == FixType.DELETE and self.team_preferences["code_structure"]["prefer_early_returns"]:
                priority_multiplier *= 1.1
            
            return base_confidence * priority_multiplier
        
        # Sort by calculated priority (highest first)
        return sorted(suggestions, key=calculate_priority, reverse=True)
    
    def customize_suggestion(self, suggestion: Suggestion) -> Suggestion:
        """
        Customize suggestion based on team preferences.
        
        Args:
            suggestion: Original suggestion
        
        Returns:
            Customized suggestion
        """
        # Customize environment variable names based on team prefix
        if "os.environ.get" in suggestion.suggested_code:
            env_prefix = self.team_preferences["security_preferences"]["env_var_prefix"]
            # Simple customization - in real implementation would be more sophisticated
            if not suggestion.suggested_code.startswith(f'os.environ.get("{env_prefix}'):
                suggestion.explanation += f" (Team prefers {env_prefix} prefix for environment variables)"
        
        return suggestion


class SuggestionEngine:
    """Main suggestion engine that orchestrates different suggestion providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rule_based = RuleBasedSuggester()
        
        # Initialize OpenAI suggester if API key is available
        openai_key = config.get('openai_api_key', '')
        self.openai_suggester = OpenAISuggester(openai_key) if openai_key else None
        
        # Initialize team style analyzer
        self.team_analyzer = None  # Will be set when analyzing a repository
    
    def generate_suggestions(self, issues: List[Issue], repo_path: str = "") -> Dict[str, Suggestion]:
        """
        Generate suggestions for a list of issues.
        
        Args:
            issues: List of issues to generate suggestions for
            repo_path: Path to repository for team style analysis
        
        Returns:
            Dictionary mapping issue IDs to suggestions
        """
        suggestions = {}
        
        # Initialize team analyzer if repo path is provided
        if repo_path and not self.team_analyzer:
            self.team_analyzer = TeamStyleAnalyzer(repo_path)
        
        # Generate suggestions for each issue
        suggestion_list = []
        for issue in issues:
            suggestion = self._generate_single_suggestion(issue)
            if suggestion:
                # Customize suggestion based on team style
                if self.team_analyzer:
                    suggestion = self.team_analyzer.customize_suggestion(suggestion)
                suggestions[issue.id] = suggestion
                suggestion_list.append(suggestion)
        
        # Prioritize suggestions if team analyzer is available
        if self.team_analyzer and suggestion_list:
            prioritized = self.team_analyzer.prioritize_suggestions(suggestion_list)
            # Update confidence scores based on prioritization
            for i, suggestion in enumerate(prioritized):
                # Slightly boost confidence for higher priority suggestions
                boost = (len(prioritized) - i) / len(prioritized) * 0.1
                suggestion.confidence = min(1.0, suggestion.confidence + boost)
        
        return suggestions
    
    def _generate_single_suggestion(self, issue: Issue) -> Optional[Suggestion]:
        """Generate a suggestion for a single issue."""
        suggestion = None
        
        # Try OpenAI first if available and enabled
        if (self.config.get('use_ai_suggestions', True) and 
            self.openai_suggester and 
            issue.severity.value in ['high', 'critical']):
            
            suggestion = self.openai_suggester.generate_suggestion(issue)
        
        # Fallback to rule-based suggestions
        if not suggestion and self.config.get('fallback_to_rules', True):
            suggestion = self.rule_based.generate_suggestion(issue)
        
        return suggestion