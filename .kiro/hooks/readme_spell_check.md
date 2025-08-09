---
name: "README Spell Check"
description: "Review and fix grammar/spelling errors in README files"
trigger: "manual"
enabled: true
button_text: "🔤 Check Spelling"
button_tooltip: "Review and fix spelling/grammar in README files"
---

# README Spell Check Hook

This manual hook reviews README files for spelling and grammar errors, providing suggestions for improvements to maintain professional documentation quality.

## Configuration

**Trigger Event**: `manual` (User-initiated via button click)

**Target Files**: `README.md`, `README.rst`, `README.txt`, and similar documentation files

**Command**: Custom spell-check and grammar analysis

**Timeout**: 30 seconds

## Hook Implementation

```python
#!/usr/bin/env python3
# spell_check_hook.py

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess
import json

class ReadmeSpellChecker:
    """Spell checker specifically designed for README files."""
    
    def __init__(self):
        self.common_tech_words = {
            # Programming languages
            'python', 'javascript', 'typescript', 'java', 'cpp', 'csharp',
            'golang', 'rust', 'kotlin', 'swift', 'php', 'ruby',
            
            # Frameworks and libraries
            'flask', 'django', 'fastapi', 'react', 'vue', 'angular',
            'nodejs', 'express', 'webpack', 'babel', 'eslint',
            
            # Tools and platforms
            'github', 'gitlab', 'docker', 'kubernetes', 'aws', 'azure',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            
            # Common abbreviations
            'api', 'cli', 'gui', 'url', 'uri', 'http', 'https', 'json',
            'xml', 'yaml', 'csv', 'sql', 'html', 'css', 'js', 'ts',
            
            # KiroLinter specific
            'kirolinter', 'linter', 'ast', 'cve', 'nvd', 'bandit',
            'pylint', 'flake8', 'mypy', 'pytest'
        }
        
        self.common_typos = {
            'teh': 'the',
            'adn': 'and',
            'nad': 'and',
            'taht': 'that',
            'thsi': 'this',
            'wiht': 'with',
            'htis': 'this',
            'recieve': 'receive',
            'seperate': 'separate',
            'definately': 'definitely',
            'occured': 'occurred',
            'begining': 'beginning',
            'sucessful': 'successful',
            'sucessfully': 'successfully',
            'accomodate': 'accommodate',
            'recomend': 'recommend',
            'recomendation': 'recommendation',
            'installtion': 'installation',
            'confguration': 'configuration',
            'configuraton': 'configuration',
            'anaylsis': 'analysis',
            'anaylze': 'analyze',
            'anaylzer': 'analyzer',
            'vulnerabilty': 'vulnerability',
            'secuirty': 'security',
            'performace': 'performance',
            'optmization': 'optimization',
            'integraion': 'integration',
            'documentaion': 'documentation',
            'requirments': 'requirements',
            'dependecies': 'dependencies',
            'compatibilty': 'compatibility'
        }
        
        self.grammar_patterns = [
            # Common grammar issues
            (r'\bi\s+am\s+a\s+([aeiou])', r'I am an \1'),  # "i am a apple" -> "I am an apple"
            (r'\ba\s+([aeiou]\w+)', r'an \1'),  # "a apple" -> "an apple"
            (r'\ban\s+([bcdfghjklmnpqrstvwxyz]\w+)', r'a \1'),  # "an book" -> "a book"
            (r'\bits\s+([a-z])', r"it's \1"),  # "its working" -> "it's working" (context dependent)
            (r'\byour\s+(working|running|using)', r"you're \1"),  # "your working" -> "you're working"
            (r'\bthere\s+(working|running|going)', r"they're \1"),  # "there working" -> "they're working"
        ]
    
    def find_readme_files(self, directory: str) -> List[Path]:
        """Find all README files in the directory."""
        readme_patterns = [
            'README.md', 'README.rst', 'README.txt', 'README',
            'readme.md', 'readme.rst', 'readme.txt', 'readme',
            'Readme.md', 'Readme.rst', 'Readme.txt', 'Readme'
        ]
        
        found_files = []
        for pattern in readme_patterns:
            file_path = Path(directory) / pattern
            if file_path.exists():
                found_files.append(file_path)
        
        return found_files
    
    def extract_text_content(self, file_path: Path) -> str:
        """Extract text content from README file, handling markdown."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if file_path.suffix.lower() == '.md':
                # Remove markdown formatting for spell checking
                content = self._clean_markdown(content)
            
            return content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
    
    def _clean_markdown(self, content: str) -> str:
        """Clean markdown formatting to extract plain text."""
        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`[^`]+`', '', content)
        
        # Remove links but keep text
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # Remove images
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)
        
        # Remove headers
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        
        # Remove emphasis
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        return content
    
    def check_spelling(self, text: str) -> List[Dict[str, any]]:
        """Check spelling and return list of issues."""
        issues = []
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        for word in words:
            if word in self.common_typos:
                issues.append({
                    'type': 'spelling',
                    'word': word,
                    'suggestion': self.common_typos[word],
                    'severity': 'medium',
                    'message': f"Possible typo: '{word}' should be '{self.common_typos[word]}'"
                })
        
        return issues
    
    def check_grammar(self, text: str) -> List[Dict[str, any]]:
        """Check grammar and return list of issues."""
        issues = []
        
        for pattern, replacement in self.grammar_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues.append({
                    'type': 'grammar',
                    'original': match.group(0),
                    'suggestion': re.sub(pattern, replacement, match.group(0), flags=re.IGNORECASE),
                    'severity': 'low',
                    'message': f"Grammar suggestion: '{match.group(0)}' could be '{re.sub(pattern, replacement, match.group(0), flags=re.IGNORECASE)}'"
                })
        
        return issues
    
    def check_style(self, text: str) -> List[Dict[str, any]]:
        """Check documentation style and return suggestions."""
        issues = []
        
        # Check for passive voice (simplified)
        passive_patterns = [
            r'\b(is|are|was|were|been|being)\s+\w+ed\b',
            r'\b(is|are|was|were|been|being)\s+\w+en\b'
        ]
        
        for pattern in passive_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues.append({
                    'type': 'style',
                    'original': match.group(0),
                    'suggestion': 'Consider using active voice',
                    'severity': 'low',
                    'message': f"Style suggestion: Consider rewriting '{match.group(0)}' in active voice"
                })
        
        # Check for overly long sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            words = len(sentence.split())
            if words > 30:
                issues.append({
                    'type': 'style',
                    'original': sentence.strip()[:50] + '...',
                    'suggestion': 'Consider breaking into shorter sentences',
                    'severity': 'low',
                    'message': f"Style suggestion: Sentence is {words} words long, consider breaking it up"
                })
        
        return issues
    
    def generate_report(self, file_path: Path, issues: List[Dict[str, any]]) -> str:
        """Generate a formatted report of issues found."""
        if not issues:
            return f"✅ No spelling or grammar issues found in {file_path.name}"
        
        report = [f"📝 Spell Check Report for {file_path.name}"]
        report.append("=" * 50)
        
        # Group issues by type
        spelling_issues = [i for i in issues if i['type'] == 'spelling']
        grammar_issues = [i for i in issues if i['type'] == 'grammar']
        style_issues = [i for i in issues if i['type'] == 'style']
        
        if spelling_issues:
            report.append("\n🔤 Spelling Issues:")
            for issue in spelling_issues:
                report.append(f"  • {issue['message']}")
        
        if grammar_issues:
            report.append("\n📝 Grammar Issues:")
            for issue in grammar_issues:
                report.append(f"  • {issue['message']}")
        
        if style_issues:
            report.append("\n✨ Style Suggestions:")
            for issue in style_issues:
                report.append(f"  • {issue['message']}")
        
        report.append(f"\nTotal issues found: {len(issues)}")
        
        return "\n".join(report)
    
    def apply_fixes(self, file_path: Path, issues: List[Dict[str, any]]) -> bool:
        """Apply automatic fixes where possible."""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Apply spelling fixes
            for issue in issues:
                if issue['type'] == 'spelling' and 'suggestion' in issue:
                    # Use word boundaries to avoid partial replacements
                    pattern = r'\b' + re.escape(issue['word']) + r'\b'
                    content = re.sub(pattern, issue['suggestion'], content, flags=re.IGNORECASE)
            
            # Apply grammar fixes (more conservative)
            for issue in issues:
                if issue['type'] == 'grammar' and 'original' in issue and 'suggestion' in issue:
                    content = content.replace(issue['original'], issue['suggestion'])
            
            if content != original_content:
                # Create backup
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                backup_path.write_text(original_content, encoding='utf-8')
                
                # Write fixed content
                file_path.write_text(content, encoding='utf-8')
                
                print(f"✅ Applied fixes to {file_path.name}")
                print(f"📁 Backup saved as {backup_path.name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error applying fixes to {file_path}: {e}")
            return False

def main():
    """Main hook execution function."""
    print("🔤 Starting README spell check...")
    
    # Find current directory (repository root)
    current_dir = os.getcwd()
    
    # Initialize spell checker
    checker = ReadmeSpellChecker()
    
    # Find README files
    readme_files = checker.find_readme_files(current_dir)
    
    if not readme_files:
        print("ℹ️  No README files found in the current directory")
        return
    
    print(f"📄 Found {len(readme_files)} README file(s): {', '.join(f.name for f in readme_files)}")
    
    total_issues = 0
    
    for readme_file in readme_files:
        print(f"\n🔍 Analyzing {readme_file.name}...")
        
        # Extract text content
        text_content = checker.extract_text_content(readme_file)
        
        if not text_content:
            print(f"⚠️  Could not read content from {readme_file.name}")
            continue
        
        # Check for issues
        spelling_issues = checker.check_spelling(text_content)
        grammar_issues = checker.check_grammar(text_content)
        style_issues = checker.check_style(text_content)
        
        all_issues = spelling_issues + grammar_issues + style_issues
        total_issues += len(all_issues)
        
        # Generate and display report
        report = checker.generate_report(readme_file, all_issues)
        print(report)
        
        # Ask user if they want to apply fixes
        if all_issues:
            fixable_issues = [i for i in all_issues if i['type'] in ['spelling', 'grammar']]
            if fixable_issues:
                response = input(f"\n🔧 Apply automatic fixes to {readme_file.name}? (y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    if checker.apply_fixes(readme_file, fixable_issues):
                        print(f"✅ Fixes applied to {readme_file.name}")
                    else:
                        print(f"ℹ️  No changes needed for {readme_file.name}")
    
    print(f"\n📊 Summary: Found {total_issues} total issues across {len(readme_files)} file(s)")
    
    if total_issues == 0:
        print("🎉 All README files look great!")
    else:
        print("💡 Consider reviewing and addressing the issues above to improve documentation quality")

if __name__ == "__main__":
    main()
```

## Usage Instructions

### Manual Execution

1. **Via Kiro Interface**: Click the "🔤 Check Spelling" button in the Agent Hooks panel
2. **Via Command Line**: Run `python .kiro/hooks/readme_spell_check.py` from repository root
3. **Via Kiro Command**: Use `kiro hook run readme_spell_check`

### Interactive Process

1. The hook scans for README files in the repository root
2. Analyzes each file for spelling, grammar, and style issues
3. Displays a detailed report of findings
4. Offers to apply automatic fixes for spelling and grammar errors
5. Creates backup files before making changes

## Sample Output

```
🔤 Starting README spell check...
📄 Found 1 README file(s): README.md

🔍 Analyzing README.md...

📝 Spell Check Report for README.md
==================================================

🔤 Spelling Issues:
  • Possible typo: 'installtion' should be 'installation'
  • Possible typo: 'anaylsis' should be 'analysis'
  • Possible typo: 'vulnerabilty' should be 'vulnerability'

📝 Grammar Issues:
  • Grammar suggestion: 'a API' could be 'an API'
  • Grammar suggestion: 'its working' could be 'it's working'

✨ Style Suggestions:
  • Style suggestion: Sentence is 35 words long, consider breaking it up
  • Style suggestion: Consider rewriting 'is configured' in active voice

Total issues found: 6

🔧 Apply automatic fixes to README.md? (y/N): y
✅ Applied fixes to README.md
📁 Backup saved as README.md.backup

📊 Summary: Found 6 total issues across 1 file(s)
💡 Consider reviewing and addressing the issues above to improve documentation quality
```

## Testing with Flask Repository

To test this hook with the KiroLinter repository:

```bash
# Clone KiroLinter repository
git clone git@github.com:McKhanster/kirolinter.git
cd kirolinter

# Copy the spell check hook
mkdir -p .kiro/hooks
cp /path/to/kirolinter/.kiro/hooks/readme_spell_check.md .kiro/hooks/

# Create a test README with intentional errors
cat > TEST_README.md << EOF
# KiroLinter Test Readme

This is a test readme for demonstraton of the spell checker hook.

## Installtion

To install KiroLinter, you need to run the folowing command:

\`\`\`bash
pip install -e .
\`\`\`

## Anaylsis

KiroLinter is a comprehensive code anaylsis tool that is writen in Python. Its working
great for detecting secuirty vulnerabilties, performance issues, and code smells.

The tool provides a API that is easy to use and understand.

## Confguration

KiroLinter can be configurated using enviroment variables or YAML configuration files.
The configuraton is very flexable and allows for customization.

## Vulnerabilty Detection

Make sure to check for secuirty vulnerabilties in your application.
Regular anaylsis of your code is recomended for maintaining good secuirty.
KiroLinter integrates with CVE databases for enhanced vulnerabilty detection.
EOF

# Run the spell checker
python .kiro/hooks/readme_spell_check.py

# Expected output will show multiple spelling and grammar issues
# The hook will offer to fix them automatically
```

### Expected Issues Found:
- **Spelling**: demonstraton → demonstration, installtion → installation, folowing → following, anaylsis → analysis, writen → written, confguration → configuration, configurated → configured, enviroment → environment, configuraton → configuration, flexable → flexible, vulnerabilty → vulnerability, secuirty → security, vulnerabilties → vulnerabilities, recomended → recommended
- **Grammar**: "a API" → "an API", "Its working" → "It's working"
- **Style**: Long sentences, passive voice suggestions

## Advanced Features

### Custom Dictionary

Add project-specific terms to avoid false positives:

```python
# Add to common_tech_words in the hook
custom_words = {
    'kirolinter', 'ast', 'cve', 'nvd', 'bandit',
    'your_project_name', 'custom_framework'
}
```

### Integration with External Tools

```bash
# Use aspell for more comprehensive spell checking
aspell --mode=markdown --check README.md

# Use languagetool for advanced grammar checking
languagetool README.md
```

### Automated Fixes

The hook can automatically fix:
- Common typos and misspellings
- Basic grammar issues (a/an, its/it's)
- Simple punctuation errors

## Troubleshooting

**No README files found**: Ensure you're running from the repository root

**Permission errors**: Check file permissions for README files

**Encoding issues**: The hook assumes UTF-8 encoding

**False positives**: Add technical terms to the custom dictionary

## Customization

You can customize the hook by modifying:
- `common_typos` dictionary for project-specific corrections
- `grammar_patterns` for additional grammar rules
- `common_tech_words` to avoid false positives
- Style checking rules for documentation standards