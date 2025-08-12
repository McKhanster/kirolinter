---
name: "On Commit Analysis"
description: "Automatically analyze changed files after each git commit"
trigger: "post-commit"
enabled: true
---

# On Commit Analysis Hook

This hook automatically runs KiroLinter analysis on files that were changed in the most recent commit, providing immediate feedback on code quality issues.

## Configuration

**Trigger Event**: `post-commit` (Git hook that runs after `git commit`)

**Command**: `kirolinter analyze --changed-only --format=summary`

**Working Directory**: Repository root

**Timeout**: 60 seconds

## Hook Script

```bash
#!/bin/bash
# .git/hooks/post-commit

# Get the repository root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Change to repository root
cd "$REPO_ROOT"

# Check if kirolinter is available
if ! command -v kirolinter &> /dev/null; then
    echo "⚠️  KiroLinter not found in PATH. Skipping analysis."
    echo "   Install with: pip install -e ."
    exit 0
fi

# Check if there are any Python files in the last commit
CHANGED_PY_FILES=$(git diff --name-only HEAD~1 HEAD | grep '\.py$' | wc -l)
if [ "$CHANGED_PY_FILES" -eq 0 ]; then
    echo "ℹ️  No Python files changed in this commit. Skipping analysis."
    exit 0
fi

echo "🔍 Running KiroLinter analysis on $CHANGED_PY_FILES changed Python file(s)..."

# Run analysis on changed files with timeout
timeout 60s kirolinter analyze --changed-only --format=summary --severity=medium

# Exit code handling
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ No issues found in changed files"
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠️  Issues found - review the analysis above"
elif [ $EXIT_CODE -eq 124 ]; then
    echo "⏰ Analysis timed out after 60 seconds"
else
    echo "❌ Analysis failed with exit code $EXIT_CODE"
fi

# Don't fail the commit even if issues are found
exit 0
```

## Installation

To install this hook in your repository:

1. Copy the hook script to `.git/hooks/post-commit`
2. Make it executable: `chmod +x .git/hooks/post-commit`
3. Ensure KiroLinter is installed and available in PATH

## Sample Output

```
🔍 Running KiroLinter analysis on changed files...

📊 KiroLinter Analysis Summary
Files analyzed: 3
Issues found: 2

🔴 HIGH SEVERITY (1):
  src/main.py:45 - Potential SQL injection vulnerability

🟡 MEDIUM SEVERITY (1):
  src/utils.py:23 - Unused variable 'temp_data'

⚠️  Issues found - review the analysis above
```

## Customization Options

You can customize the hook behavior by modifying the command:

- `--severity=low` - Include low severity issues
- `--format=json` - Output detailed JSON report
- `--output=analysis.json` - Save report to file
- `--exclude="tests/*"` - Exclude test files from analysis

## Testing with KiroLinter Repository

To test this hook with the KiroLinter repository itself:

```bash
# Clone KiroLinter repository
git clone git@github.com:McKhanster/kirolinter.git
cd kirolinter

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install KiroLinter in development mode
pip install -e .

# Install the hook
cp .kiro/hooks/on_commit_analysis.md .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Make a test commit to a Python file
echo "# Test variable for analysis" >> kirolinter/core/scanner.py
echo "unused_test_var = 'this will trigger unused variable detection'" >> kirolinter/core/scanner.py
git add kirolinter/core/scanner.py
git commit -m "Test commit for KiroLinter hook"

# The hook will automatically run and show analysis results
```

### Expected Output:
```
🔍 Running KiroLinter analysis on 1 changed Python file(s)...

📊 KiroLinter Analysis Summary
Files analyzed: 1
Issues found: 1

🟢 LOW SEVERITY (1):
  kirolinter/core/scanner.py:567 - Unused variable 'unused_test_var'

⚠️  Issues found - review the analysis above
```

### Manual Testing Commands:

```bash
# Test CLI directly on KiroLinter repository
kirolinter analyze . --format=summary --severity=low

# Test with changed files only
kirolinter analyze --changed-only --format=json

# Test with specific exclusions
kirolinter analyze . --exclude="tests/*" --exclude="venv/*" --format=summary
```

## Troubleshooting

**Hook not running**: Ensure the script is executable and located at `.git/hooks/post-commit`

**KiroLinter not found**: Make sure KiroLinter is installed and available in your PATH

**Performance issues**: For large repositories, consider adding `--exclude` patterns for generated files or dependencies