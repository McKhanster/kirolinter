"""
Unit tests for CVE database integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path

from kirolinter.integrations.cve_database import CVEDatabase, CVEInfo
from kirolinter.models.issue import Issue, IssueType, Severity


class TestCVEDatabase:
    """Test cases for CVE database integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.cache_dir = self.temp_dir.name
        self.cve_db = CVEDatabase(cache_dir=self.cache_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_init_cache_db(self):
        """Test cache database initialization."""
        cache_db_path = Path(self.cache_dir) / 'cve_cache.db'
        assert cache_db_path.exists()
        
        # Verify tables were created
        with sqlite3.connect(cache_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert 'cve_cache' in tables
            assert 'pattern_cache' in tables
    
    def test_identify_vulnerability_pattern(self):
        """Test vulnerability pattern identification."""
        # Test eval pattern
        eval_issue = Issue(
            id="test_eval",
            type=IssueType.SECURITY,
            severity=Severity.CRITICAL,
            file_path="test.py",
            line_number=1,
            column=0,
            message="Unsafe use of eval() function",
            rule_id="unsafe_eval"
        )
        
        pattern = self.cve_db._identify_vulnerability_pattern(eval_issue)
        assert pattern is not None
        assert pattern['pattern'] == 'eval'
        assert 'python eval injection' in pattern['cve_search']
        assert pattern['severity_boost'] == 0.3
        
        # Test SQL injection pattern
        sql_issue = Issue(
            id="test_sql",
            type=IssueType.SECURITY,
            severity=Severity.HIGH,
            file_path="test.py",
            line_number=1,
            column=0,
            message="Potential SQL injection in cursor.execute",
            rule_id="sql_injection"
        )
        
        pattern = self.cve_db._identify_vulnerability_pattern(sql_issue)
        assert pattern is not None
        assert pattern['pattern'] == 'sql_injection'
        assert 'python sql injection' in pattern['cve_search']
        assert pattern['severity_boost'] == 0.4
    
    def test_identify_unknown_pattern(self):
        """Test handling of unknown vulnerability patterns."""
        unknown_issue = Issue(
            id="test_unknown",
            type=IssueType.SECURITY,
            severity=Severity.MEDIUM,
            file_path="test.py",
            line_number=1,
            column=0,
            message="Unknown security issue",
            rule_id="unknown_rule"
        )
        
        pattern = self.cve_db._identify_vulnerability_pattern(unknown_issue)
        assert pattern is None
    
    @patch('requests.get')
    def test_search_cves_success(self, mock_get):
        """Test successful CVE search."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'vulnerabilities': [
                {
                    'cve': {
                        'id': 'CVE-2023-1234',
                        'descriptions': [{'value': 'Python eval vulnerability'}],
                        'metrics': {
                            'cvssMetricV31': [{
                                'cvssData': {
                                    'baseSeverity': 'HIGH',
                                    'baseScore': 8.5
                                }
                            }]
                        },
                        'published': '2023-01-01T00:00:00.000Z',
                        'lastModified': '2023-01-02T00:00:00.000Z',
                        'references': [{'url': 'https://example.com/cve-2023-1234'}],
                        'configurations': [{
                            'nodes': [{
                                'cpeMatch': [{
                                    'criteria': 'cpe:2.3:a:python:python:*:*:*:*:*:*:*:*'
                                }]
                            }]
                        }]
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        cves = self.cve_db._search_cves('python eval injection')
        
        assert len(cves) == 1
        cve = cves[0]
        assert cve.cve_id == 'CVE-2023-1234'
        assert cve.description == 'Python eval vulnerability'
        assert cve.severity == 'HIGH'
        assert cve.score == 8.5
        assert len(cve.references) == 1
        assert len(cve.affected_products) == 1
    
    @patch('requests.get')
    def test_search_cves_failure(self, mock_get):
        """Test CVE search failure handling."""
        mock_get.side_effect = Exception("API Error")
        
        cves = self.cve_db._search_cves('python eval injection')
        assert cves == []
    
    def test_select_most_relevant_cve(self):
        """Test CVE relevance scoring."""
        issue = Issue(
            id="test_eval",
            type=IssueType.SECURITY,
            severity=Severity.CRITICAL,
            file_path="test.py",
            line_number=1,
            column=0,
            message="eval vulnerability in python code",
            rule_id="unsafe_eval"
        )
        
        # Create test CVEs with different scores
        cve1 = CVEInfo(
            cve_id='CVE-2023-0001',
            description='Low score vulnerability',
            severity='MEDIUM',
            score=5.0,
            published_date='2023-01-01T00:00:00.000Z',
            modified_date='2023-01-01T00:00:00.000Z',
            references=[],
            affected_products=[]
        )
        
        cve2 = CVEInfo(
            cve_id='CVE-2023-0002',
            description='High score python eval vulnerability',
            severity='HIGH',
            score=8.5,
            published_date='2023-06-01T00:00:00.000Z',
            modified_date='2023-06-01T00:00:00.000Z',
            references=[],
            affected_products=['cpe:2.3:a:python:python:*:*:*:*:*:*:*:*']
        )
        
        cves = [cve1, cve2]
        selected = self.cve_db._select_most_relevant_cve(cves, issue)
        
        # Should select CVE2 due to higher score, Python relevance, and keyword match
        assert selected.cve_id == 'CVE-2023-0002'
    
    def test_calculate_enhanced_severity(self):
        """Test severity enhancement based on CVE data."""
        pattern_info = {'severity_boost': 0.3}
        
        # Test critical CVE score
        critical_cve = CVEInfo(
            cve_id='CVE-2023-0001',
            description='Critical vulnerability',
            severity='CRITICAL',
            score=9.5,
            published_date='2023-01-01T00:00:00.000Z',
            modified_date='2023-01-01T00:00:00.000Z',
            references=[],
            affected_products=[]
        )
        
        enhanced_severity = self.cve_db._calculate_enhanced_severity(
            Severity.MEDIUM, critical_cve, pattern_info
        )
        assert enhanced_severity == Severity.CRITICAL
        
        # Test medium CVE score
        medium_cve = CVEInfo(
            cve_id='CVE-2023-0002',
            description='Medium vulnerability',
            severity='MEDIUM',
            score=5.0,
            published_date='2023-01-01T00:00:00.000Z',
            modified_date='2023-01-01T00:00:00.000Z',
            references=[],
            affected_products=[]
        )
        
        enhanced_severity = self.cve_db._calculate_enhanced_severity(
            Severity.LOW, medium_cve, pattern_info
        )
        assert enhanced_severity == Severity.MEDIUM
    
    def test_apply_cve_enhancement(self):
        """Test applying CVE enhancement to an issue."""
        original_issue = Issue(
            id="test_eval",
            type=IssueType.SECURITY,
            severity=Severity.MEDIUM,
            file_path="test.py",
            line_number=1,
            column=0,
            message="Unsafe eval usage",
            rule_id="unsafe_eval"
        )
        
        cve = CVEInfo(
            cve_id='CVE-2023-1234',
            description='Python eval vulnerability allowing code execution',
            severity='HIGH',
            score=8.5,
            published_date='2023-01-01T00:00:00.000Z',
            modified_date='2023-01-01T00:00:00.000Z',
            references=['https://example.com/cve-2023-1234'],
            affected_products=['python']
        )
        
        pattern_info = {'severity_boost': 0.3}
        
        enhanced_issue = self.cve_db._apply_cve_enhancement(original_issue, cve, pattern_info)
        
        assert enhanced_issue.cve_id == 'CVE-2023-1234'
        assert 'CVE-2023-1234' in enhanced_issue.message
        assert enhanced_issue.severity == Severity.HIGH  # Enhanced from MEDIUM
        assert hasattr(enhanced_issue, 'cve_info')
        assert enhanced_issue.cve_info['cve_id'] == 'CVE-2023-1234'
        assert enhanced_issue.cve_info['score'] == 8.5
    
    @patch.object(CVEDatabase, '_search_cves')
    def test_enhance_security_issues(self, mock_search):
        """Test enhancing multiple security issues."""
        # Mock CVE search results
        mock_cve = CVEInfo(
            cve_id='CVE-2023-1234',
            description='Test vulnerability',
            severity='HIGH',
            score=8.0,
            published_date='2023-01-01T00:00:00.000Z',
            modified_date='2023-01-01T00:00:00.000Z',
            references=[],
            affected_products=[]
        )
        mock_search.return_value = [mock_cve]
        
        # Create test issues
        security_issue = Issue(
            id="security_1",
            type=IssueType.SECURITY,
            severity=Severity.MEDIUM,
            file_path="test.py",
            line_number=1,
            column=0,
            message="eval vulnerability",
            rule_id="unsafe_eval"
        )
        
        code_smell_issue = Issue(
            id="code_smell_1",
            type=IssueType.CODE_SMELL,
            severity=Severity.LOW,
            file_path="test.py",
            line_number=2,
            column=0,
            message="unused variable",
            rule_id="unused_variable"
        )
        
        issues = [security_issue, code_smell_issue]
        enhanced_issues = self.cve_db.enhance_security_issues(issues)
        
        # Security issue should be enhanced
        security_enhanced = next(i for i in enhanced_issues if i.id == "security_1")
        assert security_enhanced.cve_id == 'CVE-2023-1234'
        assert security_enhanced.severity == Severity.HIGH
        
        # Code smell issue should remain unchanged
        code_smell_unchanged = next(i for i in enhanced_issues if i.id == "code_smell_1")
        assert not hasattr(code_smell_unchanged, 'cve_id') or code_smell_unchanged.cve_id is None
        assert code_smell_unchanged.severity == Severity.LOW
    
    def test_get_vulnerability_stats(self):
        """Test vulnerability statistics retrieval."""
        stats = self.cve_db.get_vulnerability_stats()
        
        assert 'cached_cves' in stats
        assert 'cached_patterns' in stats
        assert 'cache_location' in stats
        assert 'supported_patterns' in stats
        assert isinstance(stats['supported_patterns'], list)
        assert 'eval' in stats['supported_patterns']
        assert 'sql_injection' in stats['supported_patterns']
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add some test data to cache
        with sqlite3.connect(self.cve_db.cache_db) as conn:
            conn.execute(
                'INSERT INTO cve_cache (cve_id, data, expires_at) VALUES (?, ?, ?)',
                ('CVE-2023-TEST', '{"test": "data"}', '2025-01-01T00:00:00')
            )
        
        # Verify data exists
        with sqlite3.connect(self.cve_db.cache_db) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM cve_cache')
            count_before = cursor.fetchone()[0]
            assert count_before > 0
        
        # Clear cache
        self.cve_db.clear_cache()
        
        # Verify data is cleared
        with sqlite3.connect(self.cve_db.cache_db) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM cve_cache')
            count_after = cursor.fetchone()[0]
            assert count_after == 0
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Test that rate limiting doesn't block immediately
        start_time = self.cve_db.last_request_time
        self.cve_db._wait_for_rate_limit()
        
        # Should update last request time
        assert self.cve_db.last_request_time >= start_time
    
    def test_parse_cve_response_empty(self):
        """Test parsing empty CVE response."""
        empty_response = {'vulnerabilities': []}
        cves = self.cve_db._parse_cve_response(empty_response)
        assert cves == []
    
    def test_parse_cve_response_malformed(self):
        """Test parsing malformed CVE response."""
        malformed_response = {'invalid': 'data'}
        cves = self.cve_db._parse_cve_response(malformed_response)
        assert cves == []


# Inline AI Coding Prompts for CVE Database Enhancement:

"""
Recommended prompts for enhancing CVE database functionality using Kiro's inline AI coding:

1. "Generate code to parse CVSS v4.0 metrics from NVD API responses and calculate enhanced severity scores"

2. "Create pattern matching logic for detecting framework-specific vulnerabilities (Django, Flask, FastAPI) in Python code"

3. "Generate code to analyze dependency files (requirements.txt, Pipfile) and match against known vulnerable package versions"

4. "Create intelligent caching strategy that prioritizes recent and high-severity CVEs for faster lookup"

5. "Generate code to extract vulnerability patterns from code context (function names, variable usage, import statements)"

6. "Create integration with multiple vulnerability databases (NVD, GitHub Security Advisory, Snyk) for comprehensive coverage"

7. "Generate machine learning model to predict vulnerability likelihood based on code patterns and historical CVE data"

8. "Create code to generate security-focused suggestions that reference specific CVE mitigation strategies"

9. "Generate vulnerability trend analysis that tracks emerging threats and updates detection patterns automatically"

10. "Create integration with SAST tools (Bandit, Semgrep) to enhance detection accuracy using multiple analysis engines"

Usage Example:
```python
# Use these prompts with Kiro's inline AI to enhance CVE database functionality
# Select relevant code section and use Ctrl+K or Cmd+K to invoke AI assistance
# Paste the prompt and let Kiro generate enhanced detection and analysis logic
```
"""