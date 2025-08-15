"""
Data anonymization utilities for KiroLinter pattern memory.

Provides comprehensive data anonymization for pattern storage to ensure
no sensitive information is stored in the pattern memory system.
"""

import re
import logging
from pathlib import Path
from typing import Dict


class DataAnonymizer:
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
        r'.*\.key',
        r'.*\.pem',
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
        import json
        data_str = json.dumps(data)
        
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, data_str):
                self.logger.error(f"Anonymization validation failed: sensitive pattern found")
                return False
        
        return True