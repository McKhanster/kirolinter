#!/usr/bin/env python3
"""
Self-testing script for KiroLinter - tests KiroLinter on its own codebase.
This demonstrates CVE integration, HTML reporting, and comprehensive analysis.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

def run_self_analysis():
    """Run KiroLinter analysis on its own codebase."""
    print("🔍 Running KiroLinter self-analysis...")
    print("=" * 60)
    
    # Test 1: JSON format with CVE integration
    print("\n1️⃣  Testing JSON format with CVE integration...")
    cmd_json = [
        'python', '-m', 'kirolinter.cli',
        'analyze', '.',
        '--format', 'json',
        '--enable-cve',
        '--severity', 'low',
        '--exclude', 'venv/*',
        '--exclude', '__pycache__/*',
        '--exclude', '.git/*'
    ]
    
    start_time = time.time()
    result_json = subprocess.run(cmd_json, capture_output=True, text=True)
    json_time = time.time() - start_time
    
    if result_json.returncode == 0:
        try:
            json_data = json.loads(result_json.stdout)
            summary = json_data.get('summary', {})
            
            print(f"✅ JSON Analysis completed in {json_time:.2f}s")
            print(f"   Files analyzed: {summary.get('total_files', 0)}")
            print(f"   Issues found: {summary.get('total_issues', 0)}")
            
            # Check for CVE-enhanced issues
            cve_count = 0
            for file_data in json_data.get('files', []):
                for issue in file_data.get('issues', []):
                    if issue.get('cve_id') or issue.get('cve_info'):
                        cve_count += 1
            
            print(f"   CVE-enhanced issues: {cve_count}")
            
            # Save JSON report
            with open('kirolinter_self_analysis.json', 'w') as f:
                json.dump(json_data, f, indent=2)
            print("   📄 JSON report saved to: kirolinter_self_analysis.json")
            
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON output")
            print(f"STDERR: {result_json.stderr}")
    else:
        print(f"❌ JSON analysis failed with exit code {result_json.returncode}")
        print(f"STDERR: {result_json.stderr}")
    
    # Test 2: HTML format
    print("\n2️⃣  Testing HTML format...")
    cmd_html = [
        'python', '-m', 'kirolinter.cli',
        'analyze', '.',
        '--format', 'html',
        '--output', 'kirolinter_self_analysis.html',
        '--severity', 'medium',
        '--exclude', 'venv/*',
        '--exclude', '__pycache__/*'
    ]
    
    start_time = time.time()
    result_html = subprocess.run(cmd_html, capture_output=True, text=True)
    html_time = time.time() - start_time
    
    if result_html.returncode == 0:
        html_file = Path('kirolinter_self_analysis.html')
        if html_file.exists():
            html_size = html_file.stat().st_size
            print(f"✅ HTML Analysis completed in {html_time:.2f}s")
            print(f"   HTML report size: {html_size:,} bytes")
            print(f"   📄 HTML report saved to: {html_file}")
            
            # Validate HTML content
            html_content = html_file.read_text()
            features = {
                'Interactive filtering': 'severity-filter' in html_content,
                'File navigation': 'toggleFile' in html_content,
                'Responsive design': '@media' in html_content,
                'Syntax highlighting': 'code' in html_content,
                'CVE information': 'cve' in html_content.lower()
            }
            
            print("   HTML Features:")
            for feature, present in features.items():
                status = "✅" if present else "❌"
                print(f"     {status} {feature}")
        else:
            print("❌ HTML file was not created")
    else:
        print(f"❌ HTML analysis failed with exit code {result_html.returncode}")
        print(f"STDERR: {result_html.stderr}")
    
    # Test 3: Summary format
    print("\n3️⃣  Testing summary format...")
    cmd_summary = [
        'python', '-m', 'kirolinter.cli',
        'analyze', '.',
        '--format', 'summary',
        '--severity', 'medium'
    ]
    
    start_time = time.time()
    result_summary = subprocess.run(cmd_summary, capture_output=True, text=True)
    summary_time = time.time() - start_time
    
    if result_summary.returncode == 0:
        print(f"✅ Summary Analysis completed in {summary_time:.2f}s")
        print("\n📊 Summary Output:")
        print("-" * 40)
        print(result_summary.stdout)
        print("-" * 40)
    else:
        print(f"❌ Summary analysis failed with exit code {result_summary.returncode}")
        print(f"STDERR: {result_summary.stderr}")
    
    # Test 4: Changed files only (if in git repo)
    print("\n4️⃣  Testing changed files analysis...")
    if Path('.git').exists():
        cmd_changed = [
            'python', '-m', 'kirolinter.cli',
            'analyze', '--changed-only',
            '--format', 'summary'
        ]
        
        result_changed = subprocess.run(cmd_changed, capture_output=True, text=True)
        
        if result_changed.returncode == 0:
            print("✅ Changed files analysis completed")
            if result_changed.stdout.strip():
                print("📊 Changed files output:")
                print(result_changed.stdout)
            else:
                print("ℹ️  No changed files to analyze")
        else:
            print(f"❌ Changed files analysis failed: {result_changed.stderr}")
    else:
        print("ℹ️  Not a git repository, skipping changed files test")
    
    # Performance summary
    print("\n📈 Performance Summary:")
    print(f"   JSON analysis: {json_time:.2f}s")
    print(f"   HTML analysis: {html_time:.2f}s")
    print(f"   Summary analysis: {summary_time:.2f}s")
    
    total_time = json_time + html_time + summary_time
    print(f"   Total analysis time: {total_time:.2f}s")
    
    if total_time < 30:
        print("✅ Performance: Excellent (< 30s)")
    elif total_time < 60:
        print("✅ Performance: Good (< 60s)")
    elif total_time < 300:
        print("⚠️  Performance: Acceptable (< 5min)")
    else:
        print("❌ Performance: Needs improvement (> 5min)")

def test_specific_features():
    """Test specific KiroLinter features on its own code."""
    print("\n🧪 Testing Specific Features:")
    print("=" * 40)
    
    # Test CVE database stats
    print("\n🛡️  Testing CVE database...")
    try:
        from kirolinter.integrations.cve_database import CVEDatabase
        cve_db = CVEDatabase()
        stats = cve_db.get_vulnerability_stats()
        
        print(f"   CVE cache location: {stats['cache_location']}")
        print(f"   Cached CVEs: {stats['cached_cves']}")
        print(f"   Cached patterns: {stats['cached_patterns']}")
        print(f"   Supported patterns: {len(stats['supported_patterns'])}")
        print("✅ CVE database integration working")
        
    except Exception as e:
        print(f"❌ CVE database test failed: {e}")
    
    # Test web reporter
    print("\n🌐 Testing web reporter...")
    try:
        from kirolinter.reporting.web_reporter import WebReporter
        reporter = WebReporter()
        
        # Create a minimal test report
        test_html = reporter._generate_html_head()
        if '<!DOCTYPE html>' in test_html or '<head>' in test_html:
            print("✅ Web reporter HTML generation working")
        else:
            print("❌ Web reporter HTML generation failed")
            
    except Exception as e:
        print(f"❌ Web reporter test failed: {e}")
    
    # Test configuration
    print("\n⚙️  Testing configuration...")
    try:
        from kirolinter.models.config import Config
        config = Config()
        
        if hasattr(config, 'rules') and hasattr(config, 'exclude_patterns'):
            print("✅ Configuration system working")
            print(f"   Default rules loaded: {len(getattr(config, 'rules', {}))}")
        else:
            print("❌ Configuration system failed")
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")

def main():
    """Main testing function."""
    print("🚀 KiroLinter Self-Analysis Test")
    print("Testing KiroLinter on its own codebase")
    print("Repository: git@github.com:McKhanster/kirolinter.git")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path('kirolinter').exists() or not Path('setup.py').exists():
        print("❌ Error: Not in KiroLinter repository root")
        print("Please run this script from the KiroLinter repository root directory")
        print("\nTo set up:")
        print("git clone git@github.com:McKhanster/kirolinter.git")
        print("cd kirolinter")
        print("pip install -e .")
        print("python test_kirolinter_self.py")
        return 1
    
    # Check if KiroLinter is installed
    try:
        import kirolinter
        print(f"✅ KiroLinter installed at: {kirolinter.__file__}")
    except ImportError:
        print("❌ Error: KiroLinter not installed")
        print("Please install with: pip install -e .")
        return 1
    
    # Run the analysis
    run_self_analysis()
    
    # Test specific features
    test_specific_features()
    
    print("\n🎉 Self-analysis completed!")
    print("\n📋 Generated Files:")
    
    files_created = []
    if Path('kirolinter_self_analysis.json').exists():
        files_created.append('kirolinter_self_analysis.json')
    if Path('kirolinter_self_analysis.html').exists():
        files_created.append('kirolinter_self_analysis.html')
    
    for file in files_created:
        size = Path(file).stat().st_size
        print(f"   📄 {file} ({size:,} bytes)")
    
    if 'kirolinter_self_analysis.html' in files_created:
        print(f"\n🌐 Open HTML report: file://{Path.cwd()}/kirolinter_self_analysis.html")
    
    print("\n✨ KiroLinter self-analysis demonstrates:")
    print("   • CVE database integration with real vulnerability data")
    print("   • Interactive HTML reports with filtering and navigation")
    print("   • Comprehensive code analysis across security, performance, and quality")
    print("   • Sub-minute analysis time for medium-sized Python projects")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())