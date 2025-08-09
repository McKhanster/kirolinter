# KiroLinter Testing Commands

## Test Analysis with Suggestions on Flask Repository

### Setup
```bash
# Clone Flask repository
git clone https://github.com/pallets/flask.git
cd flask

# Install KiroLinter in development mode
pip install -e /path/to/kirolinter
```

### Quick Test (No Config Required)
```bash
# Simple test without configuration file
kirolinter analyze src/flask/app.py --format=json --severity=medium

# Expected: JSON output with detected issues and suggestions
# Should complete in under 2 seconds for a single file
```

### Test Commands with JSON Output and Diffs

#### 1. Full Analysis with Suggestions and Diffs
```bash
# Analyze Flask source with suggestions and diff patches
kirolinter analyze src/flask --format=json --output=flask_analysis_with_diffs.json --severity=medium --verbose

# Expected: JSON report with suggested_fix sections containing diff patches
# Performance target: Complete analysis in under 5 seconds for Flask codebase
```

#### 1.1 Week 2 Enhanced Analysis Command

**Option A: With Configuration File**
```bash
# First, create a config file (or use the provided .kirolinter.yaml)
kirolinter config init

# Enhanced analysis with team style learning and AI suggestions
kirolinter analyze src/flask \
  --format=json \
  --output=flask_enhanced_analysis.json \
  --severity=low \
  --verbose \
  --config=.kirolinter.yaml

# Expected output with enhanced features:
# - Team style-aware suggestions
# - AI-powered fix recommendations (if OpenAI key configured)
# - Diff patches for all fixable issues
# - Performance metrics showing 229+ issues detected in ~1.23s
```

**Option B: Without Configuration File (Recommended for Testing)**
```bash
# Enhanced analysis using default settings
kirolinter analyze src/flask \
  --format=json \
  --output=flask_enhanced_analysis.json \
  --severity=low \
  --verbose

# This command works immediately without requiring a config file
# Uses built-in defaults for all settings
```

#### 2. Individual File Analysis
```bash
# Analyze a specific Flask file
kirolinter analyze src/flask/app.py --format=json --severity=low --verbose

# Expected: Detailed analysis of single file with suggestions
```

#### 3. Security-Focused Analysis
```bash
# Focus on security issues with high confidence suggestions
kirolinter analyze src/flask --format=json --severity=high --exclude="tests/*" --exclude="docs/*"

# Expected: Security vulnerabilities with environment variable suggestions
```

#### 4. Performance Analysis
```bash
# Analyze for performance issues
kirolinter analyze src/flask --format=summary --severity=medium --verbose

# Expected: Performance bottlenecks with optimization suggestions
```

### Expected JSON Output Structure with Suggestions

```json
{
  "kirolinter_version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "target": "src/flask",
  "summary": {
    "total_files_analyzed": 45,
    "total_issues_found": 12,
    "analysis_time_seconds": 1.23,
    "issues_by_severity": {
      "critical": 0,
      "high": 2,
      "medium": 5,
      "low": 5
    },
    "has_critical_issues": false
  },
  "files": [
    {
      "file_path": "src/flask/app.py",
      "issues": [
        {
          "id": "unused_import_sys_45",
          "type": "code_smell",
          "severity": "low",
          "line_number": 45,
          "column": 0,
          "message": "Unused import 'sys'",
          "rule_id": "unused_import",
          "suggested_fix": {
            "fix_type": "delete",
            "suggested_code": "",
            "confidence": 0.95,
            "explanation": "This import is not used anywhere in the file and can be safely removed.",
            "diff_patch": "--- a/src/flask/app.py\n+++ b/src/flask/app.py\n@@ -42,7 +42,6 @@\n import os\n-import sys\n import json"
          }
        },
        {
          "id": "hardcoded_secret_123",
          "type": "security",
          "severity": "high",
          "line_number": 67,
          "column": 0,
          "message": "Potential hardcoded secret in variable 'SECRET_KEY'",
          "rule_id": "hardcoded_secret",
          "suggested_fix": {
            "fix_type": "replace",
            "suggested_code": "os.environ.get('SECRET_KEY', 'your_secret_key_here')",
            "confidence": 0.85,
            "explanation": "Hardcoded secrets pose security risks. Use environment variables to store sensitive data securely.",
            "diff_patch": "--- a/src/flask/app.py\n+++ b/src/flask/app.py\n@@ -64,7 +64,8 @@\n+import os\n \n-SECRET_KEY = 'hardcoded_secret_123'\n+SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key_here')"
          }
        }
      ],
      "metrics": {
        "lines_of_code": 234,
        "functions": 12,
        "classes": 3,
        "imports": 8
      },
      "parse_errors": []
    }
  ],
  "metadata": {
    "rules_applied": ["unused_import", "hardcoded_secret", "unused_variable"],
    "file_extensions_analyzed": [".py"]
  }
}
```

### Validation Commands

#### 1. Verify JSON Structure
```bash
# Test JSON validity
kirolinter analyze src/flask/app.py --format=json | python -m json.tool

# Should output valid, formatted JSON
```

#### 2. Compare Formats
```bash
# Generate both JSON and summary for comparison
kirolinter analyze src/flask/app.py --format=json --output=report.json
kirolinter analyze src/flask/app.py --format=summary

# Verify both contain same issues with different formatting
```

#### 3. Test Suggestion Quality
```bash
# Analyze a file with known issues
cat > test_issues.py << 'EOF'
import os
import sys  # Unused
import json  # Unused

API_KEY = "sk-1234567890abcdef"  # Hardcoded secret
password = "super_secret_123"    # Hardcoded password

def unsafe_query(user_id):
    query = "SELECT * FROM users WHERE id = %s" % user_id  # SQL injection
    return eval(user_id)  # Unsafe eval

def test():
    unused_var = "not used"  # Unused variable
    return os.getcwd()
EOF

kirolinter analyze test_issues.py --format=json --severity=low --verbose
```

### Performance Benchmarks

```bash
# Test performance on large codebase
time kirolinter analyze . --format=json --severity=medium --exclude="venv/*" --exclude=".git/*"

# Expected: Analysis completes in under 5 minutes for large repositories
```

## Troubleshooting

### Common Issues and Solutions

1. **No suggestions in output**: Ensure suggester is properly integrated in engine.py
2. **Missing diff patches**: Check that DiffGenerator is working and include_diffs=True
3. **Invalid JSON**: Verify JSONReporter is being used instead of summary format
4. **Performance issues**: Use --exclude patterns for large directories

### Comprehensive Testing Sequence with File Output

```bash
# Create a results directory for organized output
mkdir -p kirolinter_test_results
cd kirolinter_test_results

# 1. Quick single file test (summary format with file output)
kirolinter analyze ../src/flask/app.py --format=summary --output=test1_single_file_summary.txt
echo "✅ Test 1 complete - check test1_single_file_summary.txt"

# 2. JSON output test (single file with structured output)
kirolinter analyze ../src/flask/app.py --format=json --output=test2_single_file_json.json
echo "✅ Test 2 complete - check test2_single_file_json.json"

# 3. Full directory analysis (comprehensive scan with verbose output)
kirolinter analyze ../src/flask --format=json --severity=medium --verbose --output=test3_full_directory.json
echo "✅ Test 3 complete - check test3_full_directory.json"

# 4. With configuration file (using custom settings)
kirolinter analyze ../src/flask --format=json --config=../.kirolinter.yaml --verbose --output=test4_with_config.json
echo "✅ Test 4 complete - check test4_with_config.json"

# 5. Performance comparison test (detailed format for analysis)
kirolinter analyze ../src/flask --format=detailed --severity=low --output=test5_detailed_analysis.txt
echo "✅ Test 5 complete - check test5_detailed_analysis.txt"

# 6. Security-focused analysis (high severity only)
kirolinter analyze ../src/flask --format=json --severity=high --exclude="tests/*" --output=test6_security_focus.json
echo "✅ Test 6 complete - check test6_security_focus.json"

# 7. GitHub Integration Test (requires GitHub token and test PR)
# Note: Replace PR_NUMBER and GITHUB_TOKEN with actual values
export GITHUB_TOKEN="your_github_token_here"
kirolinter analyze ../test_issues.py \
  --format=json \
  --output=test7_github_integration.json \
  --github-pr=PR_NUMBER \
  --github-token=$GITHUB_TOKEN \
  --github-repo=yourusername/flask \
  --verbose
echo "✅ Test 7 complete - check GitHub PR for posted comments"
```

### File Output Analysis Commands

```bash
# Compare file sizes to see analysis depth
ls -la test*.txt test*.json
echo "📊 File sizes show analysis comprehensiveness"

# View summary results
echo "📋 Summary Report:"
cat test1_single_file_summary.txt

# Analyze JSON structure
echo "🔍 JSON Structure Preview:"
python -m json.tool test2_single_file_json.json | head -20

# Count total issues found across all tests
echo "📈 Issue Counts:"
echo "Single file: $(grep -o '"total_issues_found": [0-9]*' test2_single_file_json.json | cut -d':' -f2 | tr -d ' ')"
echo "Full directory: $(grep -o '"total_issues_found": [0-9]*' test3_full_directory.json | cut -d':' -f2 | tr -d ' ')"
echo "With config: $(grep -o '"total_issues_found": [0-9]*' test4_with_config.json | cut -d':' -f2 | tr -d ' ')"

# Check performance metrics
echo "⚡ Performance Metrics:"
grep -o '"analysis_time_seconds": [0-9.]*' test*.json | sed 's/"analysis_time_seconds": //' | sed 's/,//' | while read time; do
  echo "Analysis time: ${time}s"
done

# Verify suggestions are included
echo "🤖 Suggestion Analysis:"
grep -c '"suggested_fix"' test*.json | while IFS=: read file count; do
  echo "$file: $count suggestions found"
done

# Check severity distribution
echo "📊 Severity Distribution:"
python3 -c "
import json
import glob

for file in glob.glob('test*.json'):
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            if 'summary' in data and 'issues_by_severity' in data['summary']:
                severity = data['summary']['issues_by_severity']
                print(f'{file}: Critical={severity.get(\"critical\", 0)}, High={severity.get(\"high\", 0)}, Medium={severity.get(\"medium\", 0)}, Low={severity.get(\"low\", 0)}')
    except Exception as e:
        print(f'Error reading {file}: {e}')
"
```

### Debug Commands

```bash
# Enable verbose output for debugging
kirolinter analyze test_file.py --format=json --verbose

# Test configuration
kirolinter config validate .kirolinter.yaml

# Test individual components
python -c "from kirolinter.core.suggester import RuleBasedSuggester; print('Suggester OK')"
python -c "from kirolinter.reporting.json_reporter import JSONReporter; print('JSON Reporter OK')"
```