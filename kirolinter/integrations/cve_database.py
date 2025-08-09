"""
CVE database integration for enhanced security vulnerability detection.
"""

import json
import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib
import sqlite3
from datetime import datetime, timedelta

from kirolinter.models.issue import Issue, IssueType, Severity


@dataclass
class CVEInfo:
    """Information about a CVE vulnerability."""
    cve_id: str
    description: str
    severity: str
    score: float
    published_date: str
    modified_date: str
    references: List[str]
    affected_products: List[str]


class CVEDatabase:
    """CVE database client for vulnerability lookups."""
    
    def __init__(self, cache_dir: str = None, api_key: str = None):
        """
        Initialize CVE database client.
        
        Args:
            cache_dir: Directory for caching CVE data
            api_key: Optional API key for enhanced rate limits
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.kirolinter' / 'cve_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.api_key = api_key
        self.base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        
        # Initialize local cache database
        self.cache_db = self.cache_dir / 'cve_cache.db'
        self._init_cache_db()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 6.0 if not api_key else 0.6  # 10 requests/min without key, 100/min with key
        
        # Vulnerability patterns for Python
        self.python_patterns = {
            'eval': {
                'keywords': ['eval', 'exec', 'compile'],
                'cve_search': 'python eval injection',
                'severity_boost': 0.3
            },
            'sql_injection': {
                'keywords': ['execute', 'cursor', 'query', '%s', 'format'],
                'cve_search': 'python sql injection',
                'severity_boost': 0.4
            },
            'pickle': {
                'keywords': ['pickle.loads', 'pickle.load', 'cPickle'],
                'cve_search': 'python pickle deserialization',
                'severity_boost': 0.5
            },
            'yaml_load': {
                'keywords': ['yaml.load', 'yaml.unsafe_load'],
                'cve_search': 'python yaml load vulnerability',
                'severity_boost': 0.4
            },
            'subprocess_shell': {
                'keywords': ['subprocess', 'shell=True', 'os.system'],
                'cve_search': 'python subprocess shell injection',
                'severity_boost': 0.3
            },
            'xml_parsing': {
                'keywords': ['xml.etree', 'lxml', 'defusedxml'],
                'cve_search': 'python xml external entity',
                'severity_boost': 0.2
            }
        }
    
    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cve_cache (
                    cve_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pattern_cache (
                    pattern_hash TEXT PRIMARY KEY,
                    cve_ids TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
    
    def enhance_security_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        Enhance security issues with CVE database information.
        
        Args:
            issues: List of detected security issues
        
        Returns:
            Enhanced issues with CVE information
        """
        enhanced_issues = []
        
        for issue in issues:
            if issue.type == IssueType.SECURITY:
                enhanced_issue = self._enhance_single_issue(issue)
                enhanced_issues.append(enhanced_issue)
            else:
                enhanced_issues.append(issue)
        
        return enhanced_issues
    
    def _enhance_single_issue(self, issue: Issue) -> Issue:
        """Enhance a single security issue with CVE data."""
        try:
            # Determine vulnerability pattern
            pattern_info = self._identify_vulnerability_pattern(issue)
            
            if pattern_info:
                # Search for relevant CVEs
                cves = self._search_cves(pattern_info['cve_search'])
                
                if cves:
                    # Select most relevant CVE
                    relevant_cve = self._select_most_relevant_cve(cves, issue)
                    
                    if relevant_cve:
                        # Enhance issue with CVE information
                        enhanced_issue = self._apply_cve_enhancement(issue, relevant_cve, pattern_info)
                        return enhanced_issue
            
            return issue
            
        except Exception as e:
            print(f"Warning: CVE enhancement failed for issue {issue.id}: {e}")
            return issue
    
    def _identify_vulnerability_pattern(self, issue: Issue) -> Optional[Dict[str, Any]]:
        """Identify the vulnerability pattern from the issue."""
        issue_text = f"{issue.message} {issue.rule_id}".lower()
        
        for pattern_name, pattern_info in self.python_patterns.items():
            for keyword in pattern_info['keywords']:
                if keyword.lower() in issue_text:
                    return {
                        'pattern': pattern_name,
                        'cve_search': pattern_info['cve_search'],
                        'severity_boost': pattern_info['severity_boost']
                    }
        
        return None
    
    def _search_cves(self, search_query: str) -> List[CVEInfo]:
        """Search for CVEs matching the query."""
        try:
            # Check cache first
            pattern_hash = hashlib.md5(search_query.encode()).hexdigest()
            cached_cves = self._get_cached_pattern_results(pattern_hash)
            
            if cached_cves:
                return cached_cves
            
            # Rate limiting
            self._wait_for_rate_limit()
            
            # Search NVD database
            params = {
                'keywordSearch': search_query,
                'resultsPerPage': 5,  # Limit results
                'startIndex': 0
            }
            
            headers = {}
            if self.api_key:
                headers['apiKey'] = self.api_key
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            cves = self._parse_cve_response(data)
            
            # Cache results
            self._cache_pattern_results(pattern_hash, cves)
            
            return cves
            
        except Exception as e:
            print(f"Warning: CVE search failed for '{search_query}': {e}")
            return []
    
    def _parse_cve_response(self, data: Dict[str, Any]) -> List[CVEInfo]:
        """Parse CVE API response into CVEInfo objects."""
        cves = []
        
        for vuln in data.get('vulnerabilities', []):
            cve_data = vuln.get('cve', {})
            
            # Extract basic information
            cve_id = cve_data.get('id', '')
            descriptions = cve_data.get('descriptions', [])
            description = descriptions[0].get('value', '') if descriptions else ''
            
            # Extract severity information
            metrics = cve_data.get('metrics', {})
            severity = 'UNKNOWN'
            score = 0.0
            
            # Try CVSS v3.1 first, then v3.0, then v2.0
            for version in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                if version in metrics and metrics[version]:
                    metric = metrics[version][0]
                    if version.startswith('cvssMetricV3'):
                        cvss_data = metric.get('cvssData', {})
                        severity = cvss_data.get('baseSeverity', 'UNKNOWN')
                        score = cvss_data.get('baseScore', 0.0)
                    else:  # v2
                        cvss_data = metric.get('cvssData', {})
                        severity = metric.get('baseSeverity', 'UNKNOWN')
                        score = cvss_data.get('baseScore', 0.0)
                    break
            
            # Extract dates
            published = cve_data.get('published', '')
            modified = cve_data.get('lastModified', '')
            
            # Extract references
            references = []
            for ref in cve_data.get('references', []):
                references.append(ref.get('url', ''))
            
            # Extract affected products (simplified)
            affected_products = []
            configurations = cve_data.get('configurations', [])
            for config in configurations:
                for node in config.get('nodes', []):
                    for cpe_match in node.get('cpeMatch', []):
                        cpe = cpe_match.get('criteria', '')
                        if 'python' in cpe.lower():
                            affected_products.append(cpe)
            
            cve_info = CVEInfo(
                cve_id=cve_id,
                description=description,
                severity=severity,
                score=score,
                published_date=published,
                modified_date=modified,
                references=references[:3],  # Limit references
                affected_products=affected_products[:3]  # Limit products
            )
            
            cves.append(cve_info)
        
        return cves
    
    def _select_most_relevant_cve(self, cves: List[CVEInfo], issue: Issue) -> Optional[CVEInfo]:
        """Select the most relevant CVE for the issue."""
        if not cves:
            return None
        
        # Score CVEs by relevance
        scored_cves = []
        
        for cve in cves:
            score = 0.0
            
            # Higher score for higher CVSS score
            score += cve.score * 0.3
            
            # Higher score for more recent CVEs
            try:
                pub_date = datetime.fromisoformat(cve.published_date.replace('Z', '+00:00'))
                days_old = (datetime.now().replace(tzinfo=pub_date.tzinfo) - pub_date).days
                recency_score = max(0, 1 - (days_old / 365))  # Decay over a year
                score += recency_score * 0.2
            except:
                pass
            
            # Higher score for Python-specific CVEs
            if any('python' in product.lower() for product in cve.affected_products):
                score += 0.3
            
            # Higher score for description relevance
            issue_keywords = issue.message.lower().split()
            desc_keywords = cve.description.lower().split()
            common_keywords = set(issue_keywords) & set(desc_keywords)
            score += len(common_keywords) * 0.1
            
            scored_cves.append((score, cve))
        
        # Return highest scoring CVE
        scored_cves.sort(key=lambda x: x[0], reverse=True)
        return scored_cves[0][1] if scored_cves else None
    
    def _apply_cve_enhancement(self, issue: Issue, cve: CVEInfo, pattern_info: Dict[str, Any]) -> Issue:
        """Apply CVE enhancement to an issue."""
        # Create enhanced issue
        enhanced_issue = Issue(
            id=issue.id,
            type=issue.type,
            severity=self._calculate_enhanced_severity(issue.severity, cve, pattern_info),
            file_path=issue.file_path,
            line_number=issue.line_number,
            column=issue.column,
            message=f"{issue.message} (Related: {cve.cve_id})",
            rule_id=issue.rule_id,
            cve_id=cve.cve_id
        )
        
        # Add CVE information as metadata
        enhanced_issue.cve_info = {
            'cve_id': cve.cve_id,
            'description': cve.description[:200] + '...' if len(cve.description) > 200 else cve.description,
            'severity': cve.severity,
            'score': cve.score,
            'references': cve.references[:2]  # Limit references
        }
        
        return enhanced_issue
    
    def _calculate_enhanced_severity(self, original_severity: Severity, cve: CVEInfo, pattern_info: Dict[str, Any]) -> Severity:
        """Calculate enhanced severity based on CVE information."""
        # Convert original severity to numeric
        severity_values = {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4
        }
        
        current_value = severity_values[original_severity]
        
        # Apply CVE score boost
        if cve.score >= 9.0:  # Critical CVSS
            current_value = max(current_value, 4)
        elif cve.score >= 7.0:  # High CVSS
            current_value = max(current_value, 3)
        elif cve.score >= 4.0:  # Medium CVSS
            current_value = max(current_value, 2)
        
        # Apply pattern-specific boost
        boost = pattern_info.get('severity_boost', 0)
        if boost > 0.3:  # High risk patterns
            current_value = min(4, current_value + 1)
        
        # Convert back to Severity
        value_to_severity = {
            1: Severity.LOW,
            2: Severity.MEDIUM,
            3: Severity.HIGH,
            4: Severity.CRITICAL
        }
        
        return value_to_severity[current_value]
    
    def _wait_for_rate_limit(self):
        """Wait for rate limit if necessary."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cached_pattern_results(self, pattern_hash: str) -> Optional[List[CVEInfo]]:
        """Get cached CVE results for a pattern."""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.execute(
                    'SELECT cve_ids FROM pattern_cache WHERE pattern_hash = ? AND expires_at > ?',
                    (pattern_hash, datetime.now().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    cve_ids = json.loads(row[0])
                    cves = []
                    
                    for cve_id in cve_ids:
                        cve_data = self._get_cached_cve(cve_id)
                        if cve_data:
                            cves.append(cve_data)
                    
                    return cves
            
            return None
            
        except Exception:
            return None
    
    def _get_cached_cve(self, cve_id: str) -> Optional[CVEInfo]:
        """Get cached CVE information."""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.execute(
                    'SELECT data FROM cve_cache WHERE cve_id = ? AND expires_at > ?',
                    (cve_id, datetime.now().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    data = json.loads(row[0])
                    return CVEInfo(**data)
            
            return None
            
        except Exception:
            return None
    
    def _cache_pattern_results(self, pattern_hash: str, cves: List[CVEInfo]):
        """Cache CVE results for a pattern."""
        try:
            expires_at = datetime.now() + timedelta(days=7)  # Cache for a week
            cve_ids = []
            
            with sqlite3.connect(self.cache_db) as conn:
                for cve in cves:
                    # Cache individual CVE
                    cve_data = {
                        'cve_id': cve.cve_id,
                        'description': cve.description,
                        'severity': cve.severity,
                        'score': cve.score,
                        'published_date': cve.published_date,
                        'modified_date': cve.modified_date,
                        'references': cve.references,
                        'affected_products': cve.affected_products
                    }
                    
                    conn.execute(
                        'INSERT OR REPLACE INTO cve_cache (cve_id, data, expires_at) VALUES (?, ?, ?)',
                        (cve.cve_id, json.dumps(cve_data), expires_at.isoformat())
                    )
                    
                    cve_ids.append(cve.cve_id)
                
                # Cache pattern results
                conn.execute(
                    'INSERT OR REPLACE INTO pattern_cache (pattern_hash, cve_ids, expires_at) VALUES (?, ?, ?)',
                    (pattern_hash, json.dumps(cve_ids), expires_at.isoformat())
                )
        
        except Exception as e:
            print(f"Warning: Failed to cache CVE results: {e}")
    
    def get_vulnerability_stats(self) -> Dict[str, Any]:
        """Get statistics about cached vulnerabilities."""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                # Count cached CVEs
                cursor = conn.execute('SELECT COUNT(*) FROM cve_cache WHERE expires_at > ?', 
                                    (datetime.now().isoformat(),))
                cached_cves = cursor.fetchone()[0]
                
                # Count cached patterns
                cursor = conn.execute('SELECT COUNT(*) FROM pattern_cache WHERE expires_at > ?', 
                                    (datetime.now().isoformat(),))
                cached_patterns = cursor.fetchone()[0]
                
                return {
                    'cached_cves': cached_cves,
                    'cached_patterns': cached_patterns,
                    'cache_location': str(self.cache_db),
                    'supported_patterns': list(self.python_patterns.keys())
                }
        
        except Exception:
            return {
                'cached_cves': 0,
                'cached_patterns': 0,
                'cache_location': str(self.cache_db),
                'supported_patterns': list(self.python_patterns.keys())
            }
    
    def clear_cache(self):
        """Clear the CVE cache."""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute('DELETE FROM cve_cache')
                conn.execute('DELETE FROM pattern_cache')
            print("CVE cache cleared successfully")
        except Exception as e:
            print(f"Error clearing CVE cache: {e}")