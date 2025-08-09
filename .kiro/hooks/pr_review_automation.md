---
name: "PR Review Automation"
description: "Automatically analyze pull requests and post review comments"
trigger: "pull_request"
enabled: true
---

# PR Review Automation Hook

This hook automatically runs KiroLinter analysis on pull requests and posts detailed review comments directly to GitHub, providing immediate feedback on code quality issues before merge.

## Configuration

**Trigger Event**: `pull_request` (GitHub webhook for PR events)

**Command**: `kirolinter analyze --changed-only --format=json --github-pr={pr_number}`

**Working Directory**: Repository root

**Timeout**: 300 seconds (5 minutes)

## Environment Variables Required

```bash
export GITHUB_TOKEN="your_github_token_here"
export GITHUB_REPO="owner/repository_name"
export KIROLINTER_CONFIG_PATH=".kirolinter.yaml"
```

## Hook Script

```bash
#!/bin/bash
# .github/workflows/kirolinter-pr-review.yml (GitHub Actions version)

name: KiroLinter PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - '**.py'

jobs:
  kirolinter-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Fetch full history for changed file detection
        
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install KiroLinter
      run: |
        pip install -e .
        
    - name: Run KiroLinter Analysis
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        GITHUB_REPO: ${{ github.repository }}
      run: |
        echo "🔍 Running KiroLinter analysis on PR #${{ github.event.number }}..."
        
        # Run analysis and capture exit code
        kirolinter analyze \
          --changed-only \
          --format=json \
          --output=pr_analysis.json \
          --github-pr=${{ github.event.number }} \
          --severity=medium || true
          
        # Always upload results as artifact
        echo "📊 Analysis complete. Results saved to pr_analysis.json"
        
    - name: Upload Analysis Results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: kirolinter-analysis-pr-${{ github.event.number }}
        path: pr_analysis.json
        retention-days: 30
        
    - name: Comment Analysis Summary
      if: always()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          
          try {
            // Read analysis results
            const analysisData = JSON.parse(fs.readFileSync('pr_analysis.json', 'utf8'));
            
            // Format summary comment
            const summary = analysisData.summary;
            const criticalIssues = summary.issues_by_severity.critical || 0;
            const highIssues = summary.issues_by_severity.high || 0;
            const mediumIssues = summary.issues_by_severity.medium || 0;
            const lowIssues = summary.issues_by_severity.low || 0;
            
            let commentBody = `## 🔍 KiroLinter Analysis Results\n\n`;
            commentBody += `**Files Analyzed:** ${summary.total_files}\n`;
            commentBody += `**Issues Found:** ${summary.total_issues}\n`;
            commentBody += `**Analysis Time:** ${summary.analysis_time.toFixed(2)}s\n\n`;
            
            if (summary.total_issues > 0) {
              commentBody += `### Issue Breakdown\n`;
              if (criticalIssues > 0) commentBody += `🔴 **${criticalIssues} Critical**\n`;
              if (highIssues > 0) commentBody += `🟠 **${highIssues} High**\n`;
              if (mediumIssues > 0) commentBody += `🟡 **${mediumIssues} Medium**\n`;
              if (lowIssues > 0) commentBody += `🟢 **${lowIssues} Low**\n`;
              
              commentBody += `\n### 📋 Detailed Issues\n`;
              commentBody += `Check the individual file comments below for specific issues and suggested fixes.\n\n`;
              
              if (criticalIssues > 0 || highIssues > 0) {
                commentBody += `⚠️ **Action Required:** This PR contains ${criticalIssues + highIssues} high-priority security or quality issues that should be addressed before merging.\n\n`;
              }
            } else {
              commentBody += `✅ **No issues found!** Great job maintaining code quality.\n\n`;
            }
            
            commentBody += `---\n*Analysis powered by [KiroLinter](https://github.com/your-org/kirolinter)*`;
            
            // Post summary comment
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: commentBody
            });
            
            // Set status check
            const state = (criticalIssues > 0) ? 'failure' : 'success';
            const description = (criticalIssues > 0) 
              ? `Found ${criticalIssues} critical issues`
              : `Analysis complete - ${summary.total_issues} issues found`;
              
            await github.rest.repos.createCommitStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              sha: context.payload.pull_request.head.sha,
              state: state,
              target_url: `https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`,
              description: description,
              context: 'KiroLinter Analysis'
            });
            
          } catch (error) {
            console.error('Error processing analysis results:', error);
            
            // Post error comment
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## ❌ KiroLinter Analysis Failed\n\nThere was an error processing the analysis results. Please check the [workflow logs](https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}) for details.`
            });
          }
```

## Webhook Version (for self-hosted)

```python
# webhook_handler.py - Flask webhook handler for self-hosted GitHub integration

from flask import Flask, request, jsonify
import subprocess
import json
import os
import tempfile
import shutil
from pathlib import Path

app = Flask(__name__)

@app.route('/webhook/kirolinter', methods=['POST'])
def handle_pr_webhook():
    """Handle GitHub PR webhook events."""
    
    # Verify webhook signature (recommended for production)
    # signature = request.headers.get('X-Hub-Signature-256')
    # if not verify_signature(request.data, signature):
    #     return jsonify({'error': 'Invalid signature'}), 403
    
    payload = request.json
    
    # Only process pull request events
    if payload.get('action') not in ['opened', 'synchronize', 'reopened']:
        return jsonify({'message': 'Event ignored'}), 200
    
    pr_number = payload['number']
    repo_full_name = payload['repository']['full_name']
    clone_url = payload['repository']['clone_url']
    pr_head_sha = payload['pull_request']['head']['sha']
    
    print(f"Processing PR #{pr_number} for {repo_full_name}")
    
    # Clone repository to temporary directory
    temp_dir = tempfile.mkdtemp(prefix='kirolinter_pr_')
    
    try:
        # Clone repository
        subprocess.run([
            'git', 'clone', '--depth', '50', clone_url, temp_dir
        ], check=True, capture_output=True)
        
        # Checkout PR head
        subprocess.run([
            'git', 'checkout', pr_head_sha
        ], cwd=temp_dir, check=True, capture_output=True)
        
        # Run KiroLinter analysis
        env = os.environ.copy()
        env['GITHUB_TOKEN'] = os.getenv('GITHUB_TOKEN')
        env['GITHUB_REPO'] = repo_full_name
        
        result = subprocess.run([
            'kirolinter', 'analyze',
            '--changed-only',
            '--format=json',
            '--github-pr', str(pr_number),
            '--severity=medium'
        ], cwd=temp_dir, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print(f"✅ Analysis completed successfully for PR #{pr_number}")
        else:
            print(f"⚠️  Analysis completed with issues for PR #{pr_number}")
            print(f"STDERR: {result.stderr}")
        
        return jsonify({
            'message': f'Analysis completed for PR #{pr_number}',
            'exit_code': result.returncode
        }), 200
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing PR #{pr_number}: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Installation

### GitHub Actions (Recommended)

1. Create `.github/workflows/kirolinter-pr-review.yml` with the workflow above
2. Ensure your repository has the necessary permissions
3. The workflow will automatically trigger on PR events

### Self-hosted Webhook

1. Deploy the webhook handler to your server
2. Configure GitHub webhook to point to your endpoint
3. Set required environment variables
4. Ensure KiroLinter is installed on the server

## Sample Configuration

Create `.kirolinter.yaml` in your repository root:

```yaml
rules:
  sql_injection:
    enabled: true
    severity: critical
  unsafe_eval:
    enabled: true
    severity: critical
  unused_variable:
    enabled: true
    severity: low

exclude_patterns:
  - "tests/*"
  - "*/migrations/*"
  - "build/*"

enable_cve_integration: true
github_integration: true
```

## Testing with KiroLinter Repository

To test this hook with the KiroLinter repository itself:

```bash
# Fork the KiroLinter repository on GitHub
# Clone your fork
git clone git@github.com:YOUR_USERNAME/kirolinter.git
cd kirolinter

# Create a test branch
git checkout -b test-kirolinter-hook

# Add the GitHub Actions workflow
mkdir -p .github/workflows
cp .kiro/hooks/pr_review_automation.md .github/workflows/kirolinter-pr-review.yml

# Create a test configuration (if not exists)
cat > .kirolinter.yaml << EOF
rules:
  sql_injection:
    enabled: true
    severity: critical
  unsafe_eval:
    enabled: true
    severity: critical
  unused_variable:
    enabled: true
    severity: medium

exclude_patterns:
  - "tests/*"
  - "venv/*"
  - "__pycache__/*"
EOF

# Make a test change that introduces issues
cat >> test_vulnerable_code.py << EOF
# Test code for KiroLinter analysis
def test_vulnerable_function(user_input):
    # This will trigger security warnings
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    result = eval(user_input)
    unused_var = "This will trigger unused variable warning"
    return query, result
EOF

# Commit and push
git add .
git commit -m "Add KiroLinter PR automation and test code"
git push origin test-kirolinter-hook

# Create a pull request on GitHub
# The workflow will automatically run and post review comments
```

### Expected PR Comments:

**Summary Comment:**
```
## 🔍 KiroLinter Analysis Results

**Files Analyzed:** 1
**Issues Found:** 3
**Analysis Time:** 1.23s

### Issue Breakdown
🔴 **2 Critical**
🟡 **1 Medium**

### 📋 Detailed Issues
Check the individual file comments below for specific issues and suggested fixes.

⚠️ **Action Required:** This PR contains 2 high-priority security or quality issues that should be addressed before merging.

---
*Analysis powered by KiroLinter*
```

**Line-specific Comments:**
- Line 2850: `🔴 **CRITICAL** - Potential SQL injection vulnerability in query construction`
- Line 2851: `🔴 **CRITICAL** - Unsafe use of eval() function with user input`
- Line 2852: `🟡 **MEDIUM** - Unused variable 'unused_var'`

## Advanced Configuration

### Custom Severity Thresholds

```yaml
# .kirolinter.yaml
pr_review:
  fail_on_critical: true
  fail_on_high: true
  fail_on_medium: false
  max_issues_per_pr: 50
  comment_threshold: "medium"  # Only comment on medium+ issues
```

### Integration with Code Review Tools

```yaml
# reviewdog integration
pr_review:
  use_reviewdog: true
  reviewdog_format: "rdjson"
  filter_mode: "added"  # Only comment on added lines
```

## Troubleshooting

**Workflow not triggering**: Check that the workflow file is in `.github/workflows/` and has correct YAML syntax

**Permission errors**: Ensure the workflow has `pull-requests: write` permission

**Analysis timeout**: Increase timeout or add exclusion patterns for large files

**Rate limiting**: Use GitHub token with appropriate permissions and consider caching

## Security Considerations

- Store GitHub tokens as repository secrets
- Validate webhook signatures in production
- Limit analysis scope to changed files only
- Use least-privilege permissions for GitHub tokens
- Consider running analysis in isolated containers