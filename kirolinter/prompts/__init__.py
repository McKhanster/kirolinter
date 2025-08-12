"""
KiroLinter Agent Prompts

This module contains specialized prompts for each AI agent in the system.
Each agent has tailored prompts for different tasks and scenarios.
"""

from .reviewer_prompts import ReviewerPrompts
# from .fixer_prompts import FixerPrompts          # TODO: Implement
# from .integrator_prompts import IntegratorPrompts # TODO: Implement
# from .learner_prompts import LearnerPrompts       # TODO: Implement

__all__ = [
    'ReviewerPrompts',
    # 'FixerPrompts',
    # 'IntegratorPrompts', 
    # 'LearnerPrompts'
]