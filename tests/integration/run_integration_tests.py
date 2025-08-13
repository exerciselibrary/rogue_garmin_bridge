#!/usr/bin/env python3
"""
Integration test runner for Rogue Garmin Bridge.

This script runs the integration tests and provides a summary of results.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_integration_tests(test_pattern=None, verbose=False):
    """Run integration tests with optional pattern filtering."""
    
    # Set up test environment
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG" if verbose else "INFO"
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    cmd.append(str(test_dir))
    
    # Add pattern if specified
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add markers for integration tests
    cmd.extend(["-m", "integration or not integration"])
    
    # Add output formatting
    cmd.extend(["--tb=short"])
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Rogue Garmin Bridge integration tests")
    parser.add_argument("-k", "--pattern", help="Run tests matching pattern")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--end-to-end", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--web-api", action="store_true", help="Run web API tests only")
    parser.add_argument("--cross-component", action="store_true", help="Run cross-component tests only")
    
    args = parser.parse_args()
    
    # Determine test pattern
    test_pattern = args.pattern
    
    if args.end_to_end:
        test_pattern = "test_end_to_end"
    elif args.web_api:
        test_pattern = "test_web_api"
    elif args.cross_component:
        test_pattern = "test_cross_component"
    
    # Run tests
    exit_code = run_integration_tests(test_pattern, args.verbose)
    
    # Print summary
    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ All integration tests passed!")
    else:
        print("\n" + "=" * 60)
        print("❌ Some integration tests failed!")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()