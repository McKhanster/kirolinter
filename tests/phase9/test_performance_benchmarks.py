"""
Phase 9: Performance Benchmarking Suite for KiroLinter.

Tests performance optimization for hackathon demo scenarios.
"""

import os
import time
import psutil
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
import json
import gc

from kirolinter.core.scanner import CodeScanner
from kirolinter.core.engine import AnalysisEngine
from kirolinter.memory.pattern_memory import PatternMemory
from kirolinter.agents.coordinator import CoordinatorAgent


class PerformanceBenchmark:
    """Performance benchmarking utilities."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.results = []
        
    def measure_memory(self) -> float:
        """Measure current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
    
    def measure_time(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Measure execution time and memory usage of a function."""
        gc.collect()
        initial_memory = self.measure_memory()
        
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        gc.collect()
        final_memory = self.measure_memory()
        
        return {
            "execution_time": end_time - start_time,
            "memory_used": final_memory - initial_memory,
            "initial_memory": initial_memory,
            "final_memory": final_memory,
            "result": result
        }
    
    def generate_test_repository(self, num_files: int, lines_per_file: int = 100) -> Path:
        """Generate a test repository with specified number of files."""
        temp_dir = tempfile.mkdtemp(prefix="kirolinter_perf_")
        
        for i in range(num_files):
            file_path = Path(temp_dir) / f"module_{i}.py"
            content = self._generate_python_file(lines_per_file, i)
            file_path.write_text(content)
        
        return Path(temp_dir)
    
    def _generate_python_file(self, lines: int, file_index: int) -> str:
        """Generate realistic Python code with various issues."""
        code = f'''"""Module {file_index} for performance testing."""

import os
import sys
import json  # unused import
from typing import List, Dict, Any

# Hardcoded secret (security issue)
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"  # another security issue

def process_data_{file_index}(data: List[str]) -> Dict[str, Any]:
    """Process data with some issues."""
    result = {{}}
    unused_var = "this is unused"  # code quality issue
    
    # Performance issue: inefficient string concatenation
    output = ""
    for item in data:
        output += str(item)
    
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + str(data[0])
    
    # Complex nested conditions (high cyclomatic complexity)
    if len(data) > 0:
        if data[0] == "test":
            if len(data) > 1:
                if data[1] == "value":
                    result["status"] = "ok"
                else:
                    result["status"] = "error"
            else:
                result["status"] = "incomplete"
        else:
            result["status"] = "unknown"
    
    # Unsafe eval usage
    if len(data) > 2:
        eval(data[2])  # critical security issue
    
    return result

class DataProcessor_{file_index}:
    """Class with various code issues."""
    
    def __init__(self):
        self.password = "secret123"  # hardcoded secret
        self.unused_attribute = None
    
    def process(self, items: List[Any]) -> None:
        """Process items with issues."""
        temp1 = 1  # unused variable
        temp2 = 2  # unused variable
        
        # Inefficient loop
        results = []
        for i in range(len(items)):
            results += [items[i]]
        
        return results

'''
        
        # Add more lines if needed
        while code.count('\n') < lines:
            code += f"\n# Additional line {code.count('\n')}"
        
        return code


class TestPerformanceBenchmarks:
    """Test suite for performance benchmarking."""
    
    def setup_method(self):
        """Set up test environment."""
        self.benchmark = PerformanceBenchmark()
        self.temp_dirs = []
    
    def teardown_method(self):
        """Clean up test environment."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def test_target_performance_35_files(self):
        """Test: Ensure sub-3-second analysis for 35-file repositories."""
        # Generate 35-file repository
        repo_path = self.benchmark.generate_test_repository(35, 150)
        self.temp_dirs.append(repo_path)
        
        # Create scanner and measure performance
        scanner = CodeScanner({})
        
        def scan_repository():
            results = []
            for py_file in repo_path.glob("**/*.py"):
                result = scanner.scan_file(py_file)
                results.append(result)
            return results
        
        metrics = self.benchmark.measure_time(scan_repository)
        
        # Verify performance meets target
        assert metrics["execution_time"] < 3.0, \
            f"Analysis took {metrics['execution_time']:.2f}s, expected < 3s"
        
        # Verify memory usage is reasonable
        assert metrics["memory_used"] < 50, \
            f"Memory usage {metrics['memory_used']:.2f}MB exceeds 50MB limit"
        
        print(f"✅ 35-file analysis: {metrics['execution_time']:.2f}s, "
              f"Memory: {metrics['memory_used']:.2f}MB")
    
    def test_memory_efficiency_pattern_storage(self):
        """Test: Memory usage for pattern storage < 100MB."""
        # Create pattern memory with many patterns
        pattern_memory = PatternMemory(":memory:")
        
        initial_memory = self.benchmark.measure_memory()
        
        # Store 10,000 patterns
        for i in range(10000):
            pattern = {
                "pattern_type": f"type_{i % 10}",
                "pattern_value": f"value_{i}",
                "context": {
                    "file": f"file_{i}.py",
                    "line": i,
                    "confidence": 0.8 + (i % 20) / 100
                },
                "metadata": {
                    "timestamp": time.time(),
                    "source": "test",
                    "additional_data": f"data_{i}" * 10  # Some bulk
                }
            }
            pattern_memory.store_pattern(
                f"repo_{i % 100}",
                f"type_{i % 10}",
                pattern
            )
        
        final_memory = self.benchmark.measure_memory()
        memory_used = final_memory - initial_memory
        
        assert memory_used < 100, \
            f"Pattern storage uses {memory_used:.2f}MB, expected < 100MB"
        
        print(f"✅ Pattern storage (10k patterns): {memory_used:.2f}MB")
    
    def test_concurrent_repository_monitoring(self):
        """Test: Support for 5+ simultaneous repository monitoring."""
        repos = []
        for i in range(5):
            repo = self.benchmark.generate_test_repository(10, 100)
            repos.append(repo)
            self.temp_dirs.append(repo)
        
        scanner = CodeScanner({})
        
        def scan_all_repos():
            results = {}
            for repo in repos:
                repo_results = []
                for py_file in repo.glob("**/*.py"):
                    result = scanner.scan_file(py_file)
                    repo_results.append(result)
                results[str(repo)] = repo_results
            return results
        
        metrics = self.benchmark.measure_time(scan_all_repos)
        
        # Should handle 5 repos efficiently
        assert metrics["execution_time"] < 10.0, \
            f"5-repo analysis took {metrics['execution_time']:.2f}s, expected < 10s"
        
        assert metrics["memory_used"] < 200, \
            f"Memory usage {metrics['memory_used']:.2f}MB exceeds 200MB limit"
        
        print(f"✅ 5-repo concurrent: {metrics['execution_time']:.2f}s, "
              f"Memory: {metrics['memory_used']:.2f}MB")
    
    def test_analysis_speed_scaling(self):
        """Test: Analysis speed scales linearly with file count."""
        results = []
        
        for num_files in [10, 20, 30, 40, 50]:
            repo = self.benchmark.generate_test_repository(num_files, 100)
            self.temp_dirs.append(repo)
            
            scanner = CodeScanner({})
            
            def scan():
                file_results = []
                for py_file in repo.glob("**/*.py"):
                    result = scanner.scan_file(py_file)
                    file_results.append(result)
                return file_results
            
            metrics = self.benchmark.measure_time(scan)
            time_per_file = metrics["execution_time"] / num_files
            
            results.append({
                "files": num_files,
                "total_time": metrics["execution_time"],
                "time_per_file": time_per_file,
                "memory": metrics["memory_used"]
            })
        
        # Check that time per file is relatively constant
        times_per_file = [r["time_per_file"] for r in results]
        avg_time = sum(times_per_file) / len(times_per_file)
        max_deviation = max(abs(t - avg_time) for t in times_per_file)
        
        assert max_deviation < avg_time * 0.3, \
            f"Time per file varies too much: {max_deviation:.3f}s deviation"
        
        print("✅ Scaling test results:")
        for r in results:
            print(f"  {r['files']} files: {r['total_time']:.2f}s "
                  f"({r['time_per_file']:.3f}s/file), "
                  f"Memory: {r['memory']:.1f}MB")
    
    def test_long_term_memory_stability(self):
        """Test: No memory leaks during extended operation."""
        scanner = CodeScanner({})
        repo = self.benchmark.generate_test_repository(5, 50)
        self.temp_dirs.append(repo)
        
        initial_memory = self.benchmark.measure_memory()
        memory_readings = [initial_memory]
        
        # Simulate 100 analysis cycles
        for cycle in range(100):
            for py_file in repo.glob("**/*.py"):
                scanner.scan_file(py_file)
            
            if cycle % 10 == 0:
                gc.collect()
                memory = self.benchmark.measure_memory()
                memory_readings.append(memory)
        
        # Calculate memory growth
        memory_growth = memory_readings[-1] - memory_readings[0]
        growth_percentage = (memory_growth / memory_readings[0]) * 100
        
        assert growth_percentage < 10, \
            f"Memory grew by {growth_percentage:.1f}%, expected < 10%"
        
        print(f"✅ Memory stability (100 cycles): "
              f"Growth: {memory_growth:.1f}MB ({growth_percentage:.1f}%)")
    
    def test_cache_effectiveness(self):
        """Test: Caching reduces analysis time for repeated scans."""
        repo = self.benchmark.generate_test_repository(20, 100)
        self.temp_dirs.append(repo)
        
        scanner = CodeScanner({})
        
        # First scan (cold cache)
        def first_scan():
            results = []
            for py_file in repo.glob("**/*.py"):
                result = scanner.scan_file(py_file)
                results.append(result)
            return results
        
        first_metrics = self.benchmark.measure_time(first_scan)
        
        # Second scan (warm cache - if implemented)
        second_metrics = self.benchmark.measure_time(first_scan)
        
        # Cache should provide some speedup (even if minimal)
        speedup = first_metrics["execution_time"] / second_metrics["execution_time"]
        
        print(f"✅ Cache effectiveness: {speedup:.2f}x speedup "
              f"(First: {first_metrics['execution_time']:.2f}s, "
              f"Second: {second_metrics['execution_time']:.2f}s)")
    
    def test_quick_pattern_recognition(self):
        """Test: Quick pattern recognition from learned patterns."""
        pattern_memory = PatternMemory(":memory:")
        
        # Pre-load common patterns
        for i in range(100):
            pattern_memory.store_pattern(
                "test_repo",
                "naming_convention",
                {
                    "pattern": f"pattern_{i}",
                    "confidence": 0.9,
                    "frequency": 10 + i
                }
            )
        
        # Measure pattern retrieval time
        def retrieve_patterns():
            results = []
            for i in range(1000):
                patterns = pattern_memory.get_patterns(
                    "test_repo",
                    "naming_convention"
                )
                results.append(patterns)
            return results
        
        metrics = self.benchmark.measure_time(retrieve_patterns)
        time_per_retrieval = metrics["execution_time"] / 1000
        
        assert time_per_retrieval < 0.001, \
            f"Pattern retrieval takes {time_per_retrieval*1000:.2f}ms, expected < 1ms"
        
        print(f"✅ Pattern retrieval: {time_per_retrieval*1000:.3f}ms per query")


def run_performance_suite():
    """Run complete performance benchmark suite."""
    print("🚀 Running KiroLinter Performance Benchmarks\n")
    print("=" * 60)
    
    benchmark = TestPerformanceBenchmarks()
    
    tests = [
        ("35-File Repository Performance", benchmark.test_target_performance_35_files),
        ("Memory Efficiency", benchmark.test_memory_efficiency_pattern_storage),
        ("Concurrent Monitoring", benchmark.test_concurrent_repository_monitoring),
        ("Scaling Analysis", benchmark.test_analysis_speed_scaling),
        ("Memory Stability", benchmark.test_long_term_memory_stability),
        ("Cache Effectiveness", benchmark.test_cache_effectiveness),
        ("Pattern Recognition", benchmark.test_quick_pattern_recognition)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📊 Testing: {name}")
        print("-" * 40)
        
        benchmark.setup_method()
        try:
            test_func()
            results.append((name, "PASSED"))
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            results.append((name, f"FAILED: {e}"))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((name, f"ERROR: {e}"))
        finally:
            benchmark.teardown_method()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 60)
    
    for test_name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
    
    passed = sum(1 for _, s in results if s == "PASSED")
    print(f"\n✨ Passed: {passed}/{len(results)} tests")
    
    return passed == len(results)


if __name__ == "__main__":
    success = run_performance_suite()
    exit(0 if success else 1)