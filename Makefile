# Rogue Garmin Bridge - Test and Development Commands

.PHONY: help install test test-unit test-integration test-simulator test-fit test-all test-coverage test-slow clean lint format setup-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install         Install dependencies"
	@echo "  setup-dev       Set up development environment"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-simulator  Run simulator tests only"
	@echo "  test-fit        Run FIT validation tests only"
	@echo "  test-coverage   Run tests with coverage report"
	@echo "  test-slow       Run slow tests"
	@echo "  test-all        Run all tests including slow ones"
	@echo "  lint            Run code linting"
	@echo "  format          Format code with black and isort"
	@echo "  clean           Clean up test artifacts"

# Installation and setup
install:
	pip install -r requirements.txt

setup-dev: install
	pip install flake8 black isort mypy pre-commit
	pre-commit install

# Test commands
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

test-simulator:
	pytest tests/simulator/ -v --tb=short

test-fit:
	pytest tests/fit_validation/ -v --tb=short

test-coverage:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml

test-slow:
	pytest -m slow -v --timeout=600

test-all: test test-slow

# Code quality
lint:
	flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy src --ignore-missing-imports --no-strict-optional

format:
	black src tests
	isort src tests

# Cleanup
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -name "*.db" -delete
	find . -name "test_*.fit" -delete

# Development helpers
run-simulator:
	python -m src.ftms.ftms_simulator --device-type bike --duration 300

run-tests-watch:
	pytest-watch tests/ -- -v --tb=short

# Docker commands
docker-build:
	docker build -t rogue-garmin-bridge .

docker-test:
	docker run --rm -v $(PWD):/app -w /app rogue-garmin-bridge make test

# Database commands
reset-test-db:
	rm -f tests/fixtures/test_*.db
	python -c "from tests.utils.database_utils import TestDatabaseManager; db = TestDatabaseManager(); db.setup_test_database(); print('Test database created')"