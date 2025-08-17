"""
Fixer Agent for KiroLinter AI Agent System - Phase 4 Enhanced.

The Fixer Agent performs proactive, safety-first fix application with
validation, backup management, and outcome learning using Redis-based PatternMemory.
"""

import os
import shutil
import ast
import tempfile
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .llm_config import get_chat_model, get_model_info
from .reviewer import ReviewerAgent
from ..memory.pattern_memory import create_pattern_memory
from ..models.suggestion import Suggestion


class FixerAgent:
    """
    AI agent specialized in proactive, safety-first code fix application.
    
    Phase 4 Enhanced Features:
    - Safety-first fix validation with multiple criteria
    - Automatic backup creation and intelligent rollback
    - Outcome learning and adaptive fix strategies
    - Risk assessment integration with ReviewerAgent
    """
    
    def __init__(self, model_provider: Optional[str] = None, memory=None, verbose: bool = False):
        """
        Initialize the Fixer Agent with Phase 4 enhancements.
        
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
                print(f"🔧 Fixer: Using {preferred.get('description', 'Unknown')} model with Redis PatternMemory")
        except Exception as e:
            if verbose:
                print(f"⚠️ Fixer: Failed to initialize LLM: {e}")
            raise
        
        # Initialize adaptive confidence threshold
        self.confidence_threshold = 0.9
        self.repo_path = None  # Set during fix application
    
    # Phase 4 Enhanced Methods
    
    def apply_fixes(self, suggestions: List[Suggestion], auto_apply: bool = True) -> List[str]:
        """
        Safety-first fix application with validation (Task 18.1).
        
        Args:
            suggestions: List of Suggestion objects to apply
            auto_apply: Whether to automatically apply safe fixes
            
        Returns:
            List of successfully applied fix IDs
        """
        applied = []
        
        if not suggestions:
            return applied
        
        # Set repo path from first suggestion
        if suggestions:
            self.repo_path = suggestions[0].file_path.rsplit('/', 1)[0] if '/' in suggestions[0].file_path else '.'
        
        if self.verbose:
            print(f"🔧 Applying {len(suggestions)} fixes (auto_apply: {auto_apply})")
        
        # Initialize reviewer for risk assessment
        reviewer = ReviewerAgent(memory=self.memory, verbose=self.verbose)
        
        for suggestion in suggestions:
            try:
                # Only auto-apply high-confidence, validated, low-risk fixes
                if auto_apply and self._should_auto_apply(suggestion, reviewer):
                    if self._apply_single_fix(suggestion):
                        applied.append(suggestion.issue_id)
                        
                        # Store successful fix pattern
                        self.memory.store_pattern(
                            self.repo_path,
                            "fix_success",
                            {
                                "issue_id": suggestion.issue_id,
                                "file": suggestion.file_path,
                                "fix_type": suggestion.fix_type,
                                "confidence": suggestion.confidence
                            },
                            0.95
                        )
                        
                        if self.verbose:
                            print(f"✅ Applied fix for {suggestion.issue_id}")
                    else:
                        if self.verbose:
                            print(f"❌ Failed to apply fix for {suggestion.issue_id}")
                elif self.verbose:
                    print(f"⏭️  Skipped fix for {suggestion.issue_id} (safety/confidence)")
                    
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Error applying fix {suggestion.issue_id}: {e}")
        
        if self.verbose:
            print(f"🎯 Successfully applied {len(applied)}/{len(suggestions)} fixes")
        
        return applied
    
    def _should_auto_apply(self, suggestion: Suggestion, reviewer: ReviewerAgent) -> bool:
        """
        Determine if a fix should be automatically applied based on safety criteria.
        
        Args:
            suggestion: Suggestion to evaluate
            reviewer: ReviewerAgent for risk assessment
            
        Returns:
            True if fix should be auto-applied
        """
        # Check confidence threshold
        if suggestion.confidence < self.confidence_threshold:
            return False
        
        # Validate fix safety
        if not self._validate_fix(suggestion):
            return False
        
        # Assess risk using reviewer
        from ..models.issue import Issue, IssueSeverity
        issue = Issue(
            file_path=suggestion.file_path,
            line_number=suggestion.line_number,
            rule_id=suggestion.issue_id,
            message=f"Fix for {suggestion.issue_id}",
            severity=IssueSeverity.MEDIUM,
            issue_type=suggestion.fix_type
        )
        
        risk = reviewer.assess_risk(issue)
        
        # Only auto-apply low-risk fixes
        return risk < 0.5
    
    def _validate_fix(self, suggestion: Suggestion) -> bool:
        """
        Comprehensive fix safety validation using multiple criteria.
        
        Args:
            suggestion: Suggestion to validate
            
        Returns:
            True if fix is safe to apply
        """
        try:
            # Check fix type is safe for automation
            safe_fix_types = ['replace', 'delete', 'insert', 'format']
            if suggestion.fix_type not in safe_fix_types:
                return False
            
            # Check suggested code size (avoid large changes)
            if len(suggestion.suggested_code) > 1000:
                return False
            
            # Check syntax if it's Python code
            if suggestion.file_path.endswith('.py'):
                if not self._check_syntax(suggestion.suggested_code):
                    return False
            
            # Check for dangerous patterns
            dangerous_patterns = [
                'exec(', 'eval(', '__import__', 'subprocess.call',
                'os.system', 'shell=True', 'rm -rf', 'DROP TABLE'
            ]
            
            for pattern in dangerous_patterns:
                if pattern in suggestion.suggested_code:
                    return False
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Fix validation failed: {e}")
            return False
    
    def _check_syntax(self, code: str) -> bool:
        """
        Check if Python code has valid syntax.
        
        Args:
            code: Python code to check
            
        Returns:
            True if syntax is valid
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
        except Exception:
            return False
    
    def _apply_single_fix(self, suggestion: Suggestion) -> bool:
        """
        Apply a single fix with backup creation.
        
        Args:
            suggestion: Suggestion to apply
            
        Returns:
            True if fix was applied successfully
        """
        try:
            # Create backup before applying fix
            if not self._backup_file(suggestion.file_path):
                return False
            
            # Apply the fix based on type
            if suggestion.fix_type == 'replace':
                return self._apply_replace_fix(suggestion)
            elif suggestion.fix_type == 'delete':
                return self._apply_delete_fix(suggestion)
            elif suggestion.fix_type == 'insert':
                return self._apply_insert_fix(suggestion)
            else:
                if self.verbose:
                    print(f"⚠️ Unsupported fix type: {suggestion.fix_type}")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to apply fix: {e}")
            
            # Attempt rollback on failure
            self.rollback_fix(suggestion.issue_id, suggestion.file_path)
            return False
    
    def _backup_file(self, file_path: str) -> bool:
        """
        Create backup of file before modification.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            True if backup was created successfully
        """
        try:
            backup_dir = os.path.join(os.path.dirname(file_path), '.kirolinter_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{os.path.basename(file_path)}.{timestamp}.backup"
            backup_path = os.path.join(backup_dir, backup_name)
            
            shutil.copy2(file_path, backup_path)
            
            if self.verbose:
                print(f"💾 Created backup: {backup_path}")
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to create backup: {e}")
            return False
    
    def _apply_replace_fix(self, suggestion: Suggestion) -> bool:
        """Apply a replace-type fix."""
        try:
            with open(suggestion.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Replace the line (1-indexed to 0-indexed)
            if 1 <= suggestion.line_number <= len(lines):
                lines[suggestion.line_number - 1] = suggestion.suggested_code + '\n'
                
                with open(suggestion.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return True
            
            return False
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Replace fix failed: {e}")
            return False
    
    def _apply_delete_fix(self, suggestion: Suggestion) -> bool:
        """Apply a delete-type fix."""
        try:
            with open(suggestion.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Delete the line (1-indexed to 0-indexed)
            if 1 <= suggestion.line_number <= len(lines):
                del lines[suggestion.line_number - 1]
                
                with open(suggestion.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return True
            
            return False
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Delete fix failed: {e}")
            return False
    
    def _apply_insert_fix(self, suggestion: Suggestion) -> bool:
        """Apply an insert-type fix."""
        try:
            with open(suggestion.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Insert the line (1-indexed to 0-indexed)
            if 0 <= suggestion.line_number <= len(lines):
                lines.insert(suggestion.line_number, suggestion.suggested_code + '\n')
                
                with open(suggestion.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return True
            
            return False
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Insert fix failed: {e}")
            return False
    
    def rollback_fix(self, issue_id: str, file_path: str):
        """
        Intelligent rollback with change impact assessment.
        
        Args:
            issue_id: ID of the issue/fix to rollback
            file_path: Path to file to rollback
        """
        try:
            if self.verbose:
                print(f"🔄 Rolling back fix for {issue_id}")
            
            # Find most recent backup
            backup_dir = os.path.join(os.path.dirname(file_path), '.kirolinter_backups')
            if not os.path.exists(backup_dir):
                if self.verbose:
                    print(f"⚠️ No backup directory found for {file_path}")
                return
            
            # Get all backups for this file
            file_name = os.path.basename(file_path)
            backups = [f for f in os.listdir(backup_dir) if f.startswith(file_name)]
            
            if not backups:
                if self.verbose:
                    print(f"⚠️ No backups found for {file_path}")
                return
            
            # Use most recent backup
            latest_backup = sorted(backups)[-1]
            backup_path = os.path.join(backup_dir, latest_backup)
            
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            
            # Store rollback pattern
            if self.repo_path:
                self.memory.store_pattern(
                    self.repo_path,
                    "fix_rollback",
                    {
                        "issue_id": issue_id,
                        "file": file_path,
                        "backup_used": latest_backup
                    },
                    1.0
                )
            
            if self.verbose:
                print(f"✅ Rollback completed using {latest_backup}")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Rollback failed: {e}")
    
    def learn_from_fixes(self, issue_id: str, success: bool, feedback: str = None):
        """
        Track fix outcomes and adapt strategies (Task 18.2).
        
        Args:
            issue_id: ID of the fixed issue
            success: Whether the fix was successful
            feedback: Optional user feedback
        """
        try:
            if not self.repo_path:
                return
            
            outcome = {
                "issue_id": issue_id,
                "success": success,
                "feedback": feedback or "",
                "timestamp": datetime.now().isoformat()
            }
            
            # Store outcome pattern
            self.memory.store_pattern(
                self.repo_path,
                "fix_outcome",
                outcome,
                1.0 if success else 0.5
            )
            
            # Optimize fix strategy based on outcomes
            self._optimize_fix_strategy()
            
            if self.verbose:
                print(f"📊 Learned from fix {issue_id}: {'success' if success else 'failure'}")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to learn from fix: {e}")
    
    def _optimize_fix_strategy(self):
        """
        Optimize fix strategy based on historical success rates.
        """
        try:
            if not self.repo_path:
                return
            
            # Get fix outcomes from memory
            outcomes = self.memory.get_team_patterns(self.repo_path, "fix_outcome")
            
            if not outcomes:
                return
            
            # Calculate success rate
            total_fixes = len(outcomes)
            successful_fixes = sum(1 for pattern in outcomes 
                                 if pattern.get('pattern_data', {}).get('success', False))
            
            success_rate = successful_fixes / total_fixes if total_fixes > 0 else 0
            
            # Adjust confidence threshold based on success rate
            # Higher success rate -> lower threshold (more aggressive)
            # Lower success rate -> higher threshold (more conservative)
            base_threshold = 0.9
            adjustment = (0.5 - success_rate) * 0.1  # ±0.05 max adjustment (inverted for correct direction)
            self.confidence_threshold = max(0.8, min(0.95, base_threshold + adjustment))
            
            if self.verbose:
                print(f"📈 Fix strategy optimized: {success_rate:.2f} success rate, "
                      f"threshold: {self.confidence_threshold:.2f}")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Fix strategy optimization failed: {e}")
    
    # Legacy methods for backward compatibility
    
    def identify_fixable_issues(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Identify issues that can be automatically fixed."""
        # TODO: Implement fixable issue identification
        return {
            "total_fixable": 0,
            "issues": [],
            "fix_types": []
        }
    
    def generate_fixes(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate fixes for the given issues."""
        # TODO: Implement fix generation
        return {
            "total_fixes": 0,
            "fixes": []
        }
    
    def apply_fixes_safely(self, fixes: List[Dict[str, Any]], create_backup: bool = True) -> Dict[str, Any]:
        """Apply fixes with safety checks and backup creation."""
        # TODO: Implement safe fix application
        return {
            "fixes_applied": 0,
            "backup_created": create_backup,
            "errors": []
        }