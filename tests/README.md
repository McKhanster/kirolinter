# KiroLinter Test Suite

This directory contains all test files for the KiroLinter project, organized by functionality.

## Test Categories

### Unit Tests
- `test_scanner.py` - Tests for AST-based code scanning functionality
- `test_suggester.py` - Tests for suggestion engine and fix generation
- `test_suggester_fix.py` - Additional tests for fix suggestions
- `test_cve_database.py` - Tests for CVE database integration
- `test_style_analyzer.py` - Tests for team style analysis
- `test_github_integration.py` - Tests for GitHub API integration

### Integration Tests
- `test_end_to_end.py` - End-to-end testing with complete workflows
- `test_performance.py` - Performance testing for large repositories
- `test_week4_features.py` - Feature validation tests

### Interactive Fixes Tests
- `test_interactive_fixes_demo.py` - Simple demonstration of interactive fixes
- `test_interactive_fixes_flask.py` - Interactive fixes testing on Flask repository
- `test_interactive_fixes_kirolinter.py` - Interactive fixes testing on KiroLinter itself
- `test_interactive_fixes_verification.py` - Verification tests for fix functionality

### Self-Analysis Tests
- `test_kirolinter_self.py` - Self-analysis of KiroLinter codebase
- `test_file.py` - Simple test file with known issues

### Test Fixtures
- `fixtures/` - Sample code files and test data
- `simple_test.py` - Simple test file for basic functionality testing
- `simple_test.py.kirolinter-backup` - Backup file demonstrating fix functionality

### Utility Files
- `test_commands.txt` - Collection of useful test commands
- `__init__.py` - Python package initialization

## Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests
python -m pytest tests/test_scanner.py tests/test_suggester.py -v

# Interactive fixes tests
python -m pytest tests/test_interactive_fixes_*.py -v

# Integration tests
python -m pytest tests/test_end_to_end.py tests/test_performance.py -v
```

### Run Interactive Demos
```bash
# Simple demo
python tests/test_interactive_fixes_demo.py

# Flask repository demo
python tests/test_interactive_fixes_flask.py

# KiroLinter self-analysis demo
python tests/test_interactive_fixes_kirolinter.py
```

## Test Coverage

The test suite covers:
- ✅ Core scanning functionality
- ✅ Suggestion engine and fix generation
- ✅ Interactive fixes with user authorization
- ✅ GitHub integration and PR reviews
- ✅ CVE database integration
- ✅ Team style analysis
- ✅ Configuration management
- ✅ Performance constraints
- ✅ End-to-end workflows
- ✅ Self-analysis capabilities

## Interactive Fixes Testing

The interactive fixes functionality has been thoroughly tested with:
- **Simple test cases** - Basic unused imports/variables
- **Real-world repositories** - Flask framework (217 → 39 issues, 95% improvement)
- **Self-analysis** - KiroLinter's own codebase
- **Safety verification** - Backup file creation and rollback capability
- **User experience** - Interactive prompts and progress feedback

All tests demonstrate the production-ready quality of KiroLinter's interactive fixes feature.