"""
Automation module for KiroLinter.

Provides background daemon and proactive analysis capabilities.
"""

from .daemon import AnalysisDaemon

__all__ = ['AnalysisDaemon']