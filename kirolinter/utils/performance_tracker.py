"""
Performance tracking utilities for KiroLinter.
"""

import time
from typing import Optional


class PerformanceTracker:
    """Track performance metrics during analysis."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
        self.end_time = None
    
    def stop(self) -> float:
        """Stop timing and return elapsed time in seconds."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        self.end_time = time.time()
        return self.end_time - self.start_time
    
    def elapsed(self) -> float:
        """Get elapsed time without stopping the timer."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        current_time = time.time()
        return current_time - self.start_time
    
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self.start_time is not None and self.end_time is None