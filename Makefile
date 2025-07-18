# Makefile for Bot-answers project

.PHONY: install test lint format check clean run help

# Virtual environment setup
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
ACTIVATE = . $(VENV)/bin/activate &&

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

# Default target
help:
	@echo "Available commands:"
	@echo "  $(GREEN)install$(NC)     - Install dependencies and setup environment"
	@echo "  $(GREEN)test$(NC)        - Run tests"
	@echo "  $(GREEN)lint$(NC)        - Run linters"
	@echo "  $(GREEN)format$(NC)      - Format code"
	@echo "  $(GREEN)check$(NC)       - Run all checks (lint + test)"
	@echo "  $(GREEN)clean$(NC)       - Clean up temporary files"
	@echo "  $(GREEN)run$(NC)         - Run the bot"
	@echo "  $(GREEN)dev$(NC)         - Install development dependencies"
	@echo "  $(GREEN)pre-commit$(NC)  - Install pre-commit hooks"
	@echo "  $(GREEN)security$(NC)    - Run security checks"
	@echo "  $(GREEN)debug$(NC)       - Check PyCharm configuration"
	@echo "  $(GREEN)test-cov$(NC)    - Run tests with coverage"

# Create virtual environment if it doesn't exist
$(VENV):
	@echo "$(YELLOW)Creating virtual environment...$(NC)"
	python -m venv $(VENV)
	@echo "$(GREEN)Virtual environment created!$(NC)"

# Install dependencies
install: $(VENV)
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(ACTIVATE) $(PIP) install --upgrade pip
	$(ACTIVATE) $(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

# Install development dependencies
dev: install
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(ACTIVATE) $(PIP) install -r requirements_dev.txt
	@echo "$(GREEN)Development dependencies installed!$(NC)"

# Setup pre-commit hooks
pre-commit: dev
	@echo "$(YELLOW)Installing pre-commit hooks...$(NC)"
	$(ACTIVATE) pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"

# Format code
format: dev
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(ACTIVATE) black .
	$(ACTIVATE) isort .
	@echo "$(GREEN)Code formatted successfully!$(NC)"

# Run linters
lint: dev
	@echo "$(YELLOW)Running linters...$(NC)"
	$(ACTIVATE) flake8 .
	$(ACTIVATE) black --check --diff .
	$(ACTIVATE) isort --check-only --diff .
	@echo "$(GREEN)Linting completed!$(NC)"

# Run type checking (disabled by default)
typecheck:
	@echo "$(YELLOW)Type checking is disabled in current configuration$(NC)"
	@echo "$(GREEN)Type checking skipped!$(NC)"

# Run tests
test: dev
	@echo "$(YELLOW)Running tests...$(NC)"
	$(ACTIVATE) pytest tests/ -v --tb=short
	@echo "$(GREEN)Tests completed!$(NC)"

# Run tests with coverage
test-cov: dev
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(ACTIVATE) pytest tests/ -v --tb=short --cov=. --cov-report=term-missing
	@echo "$(GREEN)Tests with coverage completed!$(NC)"

# Run security checks
security: dev
	@echo "$(YELLOW)Running security checks...$(NC)"
	$(ACTIVATE) bandit -r . -c pyproject.toml || true
	$(ACTIVATE) safety check --file requirements.txt || true
	@echo "$(GREEN)Security checks completed!$(NC)"

# Run all checks
check: lint test security
	@echo "$(GREEN)All checks completed!$(NC)"

# Clean up temporary files
clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ build/
	rm -f bandit-report.json safety-report.json
	@echo "$(GREEN)Cleanup completed!$(NC)"

# Run the bot
run: install
	@echo "$(YELLOW)Starting bot...$(NC)"
	$(ACTIVATE) python main.py

# Run the bot in development mode
dev-run: dev
	@echo "$(YELLOW)Starting bot in development mode...$(NC)"
	$(ACTIVATE) python debug_runner.py

# Check PyCharm configuration
debug: install
	@echo "$(YELLOW)Checking PyCharm configuration...$(NC)"
	$(ACTIVATE) python pycharm_config.py
	@echo "$(GREEN)Configuration check completed!$(NC)"

# Build package
build:
	@echo "$(YELLOW)Building package...$(NC)"
	python -m build
	@echo "$(GREEN)Package built successfully!$(NC)"

# Update dependencies
update:
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements.txt --upgrade
	@echo "$(GREEN)Dependencies updated!$(NC)"

# Show project stats
stats:
	@echo "$(YELLOW)Project Statistics:$(NC)"
	@echo "Lines of code:"
	@find . -name "*.py" -not -path "./venv/*" -not -path "./converted-data/*" | xargs wc -l
	@echo "\nTest coverage:"
	@pytest tests/ --cov=. --cov-report=term-missing -q || true
