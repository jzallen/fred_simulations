# FRED Simulation Makefile
# Uses CLI approach with bash scripts

.PHONY: all run-fred build-fred analyze clean help format lint lint-fix pre-commit test

# Default target
all: help

# Run FRED simulation via CLI (primary approach)
run-fred:
	./run_fred_simulation.sh

# Analyze simulation results with Python
analyze:
	python3 analyze_results.py

# Run simulation and analyze results
run-and-analyze: run-fred analyze

# Build FRED framework if needed
build-fred:
	cd fred-framework/src && make

# Clean generated files
clean:
	rm -rf output/
	rm -f simulation_config.fred
	rm -f fred_analysis.png

# Code Quality Commands
format:
	@echo "Formatting Python code with black and isort..."
	poetry run black epistemix_api/ simulations/ *.py --exclude "fred-framework"
	poetry run isort epistemix_api/ simulations/ *.py --skip fred-framework

lint:
	@echo "Running linters..."
	poetry run black epistemix_api/ simulations/ *.py --check --exclude "fred-framework"
	poetry run flake8 epistemix_api/ simulations/ *.py --max-line-length=100 --extend-ignore=E203,W503
	poetry run pylint epistemix_api/ simulations/ *.py

lint-fix:
	@echo "Running black to auto-fix formatting..."
	poetry run black epistemix_api/ simulations/ *.py --exclude "fred-framework"
	poetry run isort epistemix_api/ simulations/ *.py --skip fred-framework
	@echo "Running pylint to check for remaining issues..."
	poetry run pylint epistemix_api/ simulations/ *.py

pre-commit:
	@echo "Running pre-commit hooks on all files..."
	poetry run pre-commit run --all-files

test:
	@echo "Running epistemix_api tests in parallel..."
	poetry run pytest epistemix_api/ -n auto

# Show available targets
help:
	@echo "Available targets:"
	@echo "  run-fred         - Run FRED simulation using CLI"
	@echo "  analyze          - Analyze simulation results with Python"
	@echo "  run-and-analyze  - Run simulation and analyze results"
	@echo "  build-fred       - Build the FRED framework"
	@echo "  clean            - Remove generated output files"
	@echo ""
	@echo "Code Quality:"
	@echo "  format           - Format Python code with black and isort"
	@echo "  lint             - Run all linters (black, flake8, pylint)"
	@echo "  lint-fix         - Auto-fix formatting and show remaining issues"
	@echo "  pre-commit       - Run pre-commit hooks on all files"
	@echo "  test             - Run epistemix_api tests in parallel"
	@echo ""
	@echo "  help             - Show this help message"
