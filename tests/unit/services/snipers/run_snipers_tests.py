#!/usr/bin/env python
"""
Snipers Service Test Runner - Comprehensive test execution with reporting.

Usage:
    python run_snipers_tests.py                    # Run all tests
    python run_snipers_tests.py --quick            # Run fast tests only
    python run_snipers_tests.py --coverage         # With coverage
    python run_snipers_tests.py --verbose          # Detailed output
    python run_snipers_tests.py --models           # Models tests only
    python run_snipers_tests.py --parsers          # Parsers tests only
    python run_snipers_tests.py --pyrit            # PyRIT tests only
    python run_snipers_tests.py --routing          # Routing tests only
"""

import subprocess
import sys
import argparse
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Base test directory
TESTS_DIR = Path("tests/unit/services/snipers")


class SnipersTestRunner:
    """Test runner for Snipers service."""

    def __init__(self, args):
        self.args = args
        self.test_dir = TESTS_DIR

    def build_pytest_args(self) -> List[str]:
        """Build pytest command arguments."""
        args = [
            "pytest",
            str(self.test_dir),
        ]

        # Add verbosity
        if self.args.verbose:
            args.append("-vv")
        else:
            args.append("-v")

        # Add logging
        if self.args.verbose:
            args.extend(["--log-cli=DEBUG", "--log-cli-level=DEBUG"])
        elif not self.args.quiet:
            args.extend(["--log-cli=INFO", "--log-cli-level=INFO"])

        # Add coverage
        if self.args.coverage:
            args.extend([
                "--cov=services/snipers",
                "--cov-report=term-missing",
                "--cov-report=html:tests/coverage_html",
                "--cov-report=xml",
                "--cov-branch"
            ])

        # Add reporting
        if not self.args.no_reports:
            args.extend([
                "--html=tests/report.html",
                "--self-contained-html",
                "--junit-xml=tests/junit.xml",
            ])

        # Add output options
        if self.args.show_output:
            args.append("-s")  # Don't capture stdout

        # Add durations
        if not self.args.quick:
            args.extend(["--durations=10"])

        # Add specific test file
        if self.args.models:
            args = args[:-1]  # Remove last arg
            args.append(str(self.test_dir / "test_models.py"))
        elif self.args.parsers:
            args = args[:-1]
            args.append(str(self.test_dir / "test_parsers.py"))
        elif self.args.pyrit:
            args = args[:-1]
            args.append(str(self.test_dir / "test_pyrit_integration.py"))
        elif self.args.routing:
            args = args[:-1]
            args.append(str(self.test_dir / "test_routing.py"))

        # Add marker filtering
        if self.args.quick:
            args.extend(["-m", "not slow"])

        if self.args.edge_cases_only:
            args.extend(["-m", "edge_case"])

        if self.args.config_errors_only:
            args.extend(["-m", "config_error"])

        return args

    def run(self) -> int:
        """Execute tests."""
        args = self.build_pytest_args()

        logger.info("=" * 80)
        logger.info("SNIPERS SERVICE TEST RUNNER")
        logger.info("=" * 80)
        logger.info(f"Running: {' '.join(args)}")
        logger.info("=" * 80)

        try:
            result = subprocess.run(args, cwd=Path.cwd())
            return result.returncode
        except FileNotFoundError:
            logger.error("pytest not found. Install with: pip install pytest pytest-cov pytest-html")
            return 1

    def print_summary(self, return_code: int) -> None:
        """Print test summary."""
        logger.info("=" * 80)

        if return_code == 0:
            logger.info("✓ ALL TESTS PASSED")
        else:
            logger.error("✗ TESTS FAILED")

        logger.info("=" * 80)

        # Print report locations
        if not self.args.no_reports:
            logger.info("\nReports generated:")
            logger.info(f"  - HTML Report: tests/report.html")
            logger.info(f"  - JUnit XML: tests/junit.xml")
            logger.info(f"  - Log File: tests/test_results.log")

        if self.args.coverage:
            logger.info(f"  - Coverage Report: tests/coverage_html/index.html")

        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Snipers service unit tests with comprehensive reporting"
    )

    # Test selection
    parser.add_argument(
        "--models",
        action="store_true",
        help="Run only model validation tests"
    )
    parser.add_argument(
        "--parsers",
        action="store_true",
        help="Run only parser tests"
    )
    parser.add_argument(
        "--pyrit",
        action="store_true",
        help="Run only PyRIT integration tests"
    )
    parser.add_argument(
        "--routing",
        action="store_true",
        help="Run only routing logic tests"
    )

    # Test filtering
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests (exclude slow)"
    )
    parser.add_argument(
        "--edge-cases-only",
        action="store_true",
        help="Run only edge case tests"
    )
    parser.add_argument(
        "--config-errors-only",
        action="store_true",
        help="Run only configuration error tests"
    )

    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output with detailed logging"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "-s", "--show-output",
        action="store_true",
        help="Show stdout/stderr from tests (don't capture)"
    )

    # Reporting
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports (HTML, XML)"
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Skip HTML and JUnit report generation"
    )

    args = parser.parse_args()

    runner = SnipersTestRunner(args)
    return_code = runner.run()
    runner.print_summary(return_code)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
