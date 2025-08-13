#!/usr/bin/env python3
"""
Test runner script for Rogue Garmin Bridge project.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description or ' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description or 'Command'} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or 'Command'} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for Rogue Garmin Bridge")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--simulator", action="store_true", help="Run simulator tests only")
    parser.add_argument("--fit", action="store_true", help="Run FIT validation tests only")
    parser.add_argument("--slow", action="store_true", help="Run slow tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--parallel", "-j", type=int, help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    success = True
    
    # Format code if requested
    if args.format or args.all:
        success &= run_command(["black", "src", "tests"], "Code formatting with black")
        success &= run_command(["isort", "src", "tests"], "Import sorting with isort")
    
    # Run linting if requested
    if args.lint or args.all:
        success &= run_command([
            "flake8", "src", "tests", 
            "--count", "--select=E9,F63,F7,F82", 
            "--show-source", "--statistics"
        ], "Linting with flake8 (errors only)")
        
        success &= run_command([
            "flake8", "src", "tests",
            "--count", "--exit-zero", "--max-complexity=10", 
            "--max-line-length=127", "--statistics"
        ], "Linting with flake8 (full check)")
        
        success &= run_command([
            "mypy", "src", "--ignore-missing-imports", "--no-strict-optional"
        ], "Type checking with mypy")
    
    # Build pytest command
    pytest_cmd = ["pytest"]
    
    if args.verbose:
        pytest_cmd.append("-v")
    
    if args.parallel:
        pytest_cmd.extend(["-n", str(args.parallel)])
    
    if args.coverage:
        pytest_cmd.extend([
            "--cov=src", 
            "--cov-report=html", 
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Determine which tests to run
    test_paths = []
    
    if args.unit:
        test_paths.append("tests/unit/")
    elif args.integration:
        test_paths.append("tests/integration/")
    elif args.simulator:
        test_paths.append("tests/simulator/")
    elif args.fit:
        test_paths.append("tests/fit_validation/")
    elif args.slow:
        pytest_cmd.extend(["-m", "slow"])
        test_paths.append("tests/")
    elif not any([args.unit, args.integration, args.simulator, args.fit, args.slow]):
        # Run all regular tests if no specific category selected
        test_paths.append("tests/")
        if not args.all:
            pytest_cmd.extend(["-m", "not slow"])  # Exclude slow tests by default
    
    # Run tests
    if test_paths or args.slow:
        pytest_cmd.extend(test_paths)
        success &= run_command(pytest_cmd, "Running tests")
    
    # Run slow tests if --all is specified
    if args.all and not args.slow:
        slow_cmd = ["pytest", "-m", "slow", "tests/"]
        if args.verbose:
            slow_cmd.append("-v")
        success &= run_command(slow_cmd, "Running slow tests")
    
    # Print summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All checks passed!")
        sys.exit(0)
    else:
        print("💥 Some checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()