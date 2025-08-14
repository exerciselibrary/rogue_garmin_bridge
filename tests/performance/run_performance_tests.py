#!/usr/bin/env python3
"""
Performance test runner for the Rogue Garmin Bridge.

This script runs all performance and stress tests and generates a comprehensive
performance report.
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest


class PerformanceTestRunner:
    """Runs performance tests and generates reports."""
    
    def __init__(self, output_dir: str = "performance_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_load_tests(self, verbose: bool = False) -> dict:
        """Run load testing suite."""
        print("Running load tests...")
        
        test_file = os.path.join(os.path.dirname(__file__), "test_load_testing.py")
        args = [
            test_file,
            "-v" if verbose else "-q",
            "-m", "performance",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.output_dir}/load_test_results.json"
        ]
        
        result = pytest.main(args)
        
        # Load results
        results_file = self.output_dir / "load_test_results.json"
        if results_file.exists():
            with open(results_file) as f:
                self.test_results['load_tests'] = json.load(f)
        
        return {'exit_code': result, 'category': 'load_tests'}
    
    def run_stress_tests(self, verbose: bool = False) -> dict:
        """Run stress testing suite."""
        print("Running stress tests...")
        
        test_file = os.path.join(os.path.dirname(__file__), "test_stress_testing.py")
        args = [
            test_file,
            "-v" if verbose else "-q",
            "-m", "stress",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.output_dir}/stress_test_results.json"
        ]
        
        result = pytest.main(args)
        
        # Load results
        results_file = self.output_dir / "stress_test_results.json"
        if results_file.exists():
            with open(results_file) as f:
                self.test_results['stress_tests'] = json.load(f)
        
        return {'exit_code': result, 'category': 'stress_tests'}
    
    def run_performance_monitoring_tests(self, verbose: bool = False) -> dict:
        """Run performance monitoring tests."""
        print("Running performance monitoring tests...")
        
        test_file = os.path.join(os.path.dirname(__file__), "test_performance_monitoring.py")
        args = [
            test_file,
            "-v" if verbose else "-q",
            "-m", "performance",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.output_dir}/monitoring_test_results.json"
        ]
        
        result = pytest.main(args)
        
        # Load results
        results_file = self.output_dir / "monitoring_test_results.json"
        if results_file.exists():
            with open(results_file) as f:
                self.test_results['monitoring_tests'] = json.load(f)
        
        return {'exit_code': result, 'category': 'monitoring_tests'}
    
    def run_all_tests(self, verbose: bool = False) -> dict:
        """Run all performance tests."""
        print("Starting comprehensive performance test suite...")
        self.start_time = datetime.now()
        
        results = {
            'start_time': self.start_time.isoformat(),
            'test_categories': []
        }
        
        # Run each test category
        test_categories = [
            self.run_load_tests,
            self.run_stress_tests,
            self.run_performance_monitoring_tests
        ]
        
        for test_func in test_categories:
            try:
                category_result = test_func(verbose)
                results['test_categories'].append(category_result)
            except Exception as e:
                print(f"Error running {test_func.__name__}: {e}")
                results['test_categories'].append({
                    'category': test_func.__name__,
                    'error': str(e),
                    'exit_code': -1
                })
        
        self.end_time = datetime.now()
        results['end_time'] = self.end_time.isoformat()
        results['total_duration_seconds'] = (self.end_time - self.start_time).total_seconds()
        
        return results
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""
        report_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Rogue Garmin Bridge Performance Test Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            if self.start_time and self.end_time:
                duration = (self.end_time - self.start_time).total_seconds()
                f.write(f"Test Duration: {duration:.2f} seconds\n\n")
            
            # Summary section
            f.write("## Test Summary\n\n")
            
            total_tests = 0
            passed_tests = 0
            failed_tests = 0
            
            for category, results in self.test_results.items():
                if 'summary' in results:
                    summary = results['summary']
                    total_tests += summary.get('total', 0)
                    passed_tests += summary.get('passed', 0)
                    failed_tests += summary.get('failed', 0)
                    
                    f.write(f"### {category.replace('_', ' ').title()}\n")
                    f.write(f"- Total: {summary.get('total', 0)}\n")
                    f.write(f"- Passed: {summary.get('passed', 0)}\n")
                    f.write(f"- Failed: {summary.get('failed', 0)}\n")
                    f.write(f"- Duration: {summary.get('duration', 0):.2f}s\n\n")
            
            f.write(f"**Overall Results:**\n")
            f.write(f"- Total Tests: {total_tests}\n")
            f.write(f"- Passed: {passed_tests}\n")
            f.write(f"- Failed: {failed_tests}\n")
            f.write(f"- Success Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%\n\n")
            
            # Detailed results
            f.write("## Detailed Results\n\n")
            
            for category, results in self.test_results.items():
                f.write(f"### {category.replace('_', ' ').title()}\n\n")
                
                if 'tests' in results:
                    for test in results['tests']:
                        test_name = test.get('nodeid', 'Unknown Test')
                        outcome = test.get('outcome', 'unknown')
                        duration = test.get('duration', 0)
                        
                        status_emoji = "✅" if outcome == "passed" else "❌" if outcome == "failed" else "⚠️"
                        f.write(f"{status_emoji} **{test_name}** ({duration:.3f}s)\n")
                        
                        if outcome == "failed" and 'call' in test:
                            longrepr = test['call'].get('longrepr', '')
                            if longrepr:
                                f.write(f"```\n{longrepr}\n```\n")
                        
                        f.write("\n")
                
                f.write("\n")
            
            # Performance metrics section
            f.write("## Performance Metrics\n\n")
            f.write("### Key Performance Indicators\n\n")
            f.write("| Metric | Target | Actual | Status |\n")
            f.write("|--------|--------|--------|--------|\n")
            
            # Add performance metrics if available
            performance_metrics = [
                ("Memory Usage (2hr workout)", "< 100MB growth", "TBD", "⚠️"),
                ("Database Insert Rate", "> 50 points/sec", "TBD", "⚠️"),
                ("Web Response Time", "< 500ms median", "TBD", "⚠️"),
                ("Connection Recovery", "< 30s average", "TBD", "⚠️"),
                ("CPU Usage (extended)", "< 50% average", "TBD", "⚠️")
            ]
            
            for metric, target, actual, status in performance_metrics:
                f.write(f"| {metric} | {target} | {actual} | {status} |\n")
            
            f.write("\n")
            
            # Recommendations section
            f.write("## Recommendations\n\n")
            f.write("### Performance Optimizations\n")
            f.write("- Monitor memory usage during extended workouts\n")
            f.write("- Optimize database queries with proper indexing\n")
            f.write("- Implement connection pooling for better resource management\n")
            f.write("- Add client-side caching for web interface\n\n")
            
            f.write("### Monitoring\n")
            f.write("- Set up continuous performance monitoring\n")
            f.write("- Implement alerting for performance regressions\n")
            f.write("- Regular performance benchmarking\n")
            f.write("- Resource usage tracking in production\n\n")
            
            # Test configuration
            f.write("## Test Configuration\n\n")
            f.write("```json\n")
            f.write(json.dumps({
                'test_environment': 'local',
                'python_version': sys.version,
                'test_categories': list(self.test_results.keys()),
                'output_directory': str(self.output_dir)
            }, indent=2))
            f.write("\n```\n")
        
        return str(report_file)
    
    def cleanup_test_artifacts(self):
        """Clean up test artifacts and temporary files."""
        # Remove temporary test files
        temp_patterns = [
            "*.tmp",
            "test_*.db",
            "performance_*.json"
        ]
        
        for pattern in temp_patterns:
            for file_path in self.output_dir.glob(pattern):
                try:
                    file_path.unlink()
                    print(f"Cleaned up: {file_path}")
                except Exception as e:
                    print(f"Error cleaning up {file_path}: {e}")


def main():
    """Main entry point for performance test runner."""
    parser = argparse.ArgumentParser(description="Run Rogue Garmin Bridge performance tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output-dir", "-o", default="performance_reports", 
                       help="Output directory for reports")
    parser.add_argument("--category", "-c", choices=["load", "stress", "monitoring", "all"],
                       default="all", help="Test category to run")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test artifacts after run")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")
    
    args = parser.parse_args()
    
    runner = PerformanceTestRunner(args.output_dir)
    
    if not args.report_only:
        print("🚀 Starting Rogue Garmin Bridge Performance Tests")
        print("=" * 60)
        
        if args.category == "all":
            results = runner.run_all_tests(args.verbose)
        elif args.category == "load":
            results = runner.run_load_tests(args.verbose)
        elif args.category == "stress":
            results = runner.run_stress_tests(args.verbose)
        elif args.category == "monitoring":
            results = runner.run_performance_monitoring_tests(args.verbose)
        
        print("\n" + "=" * 60)
        print("✅ Performance tests completed!")
        
        # Save overall results
        results_file = runner.output_dir / "overall_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 Results saved to: {results_file}")
    
    # Generate report
    print("📝 Generating performance report...")
    report_file = runner.generate_performance_report()
    print(f"📋 Report generated: {report_file}")
    
    # Cleanup if requested
    if args.cleanup:
        print("🧹 Cleaning up test artifacts...")
        runner.cleanup_test_artifacts()
    
    print("\n🎉 Performance testing complete!")
    print(f"📁 All outputs in: {runner.output_dir}")


if __name__ == "__main__":
    main()