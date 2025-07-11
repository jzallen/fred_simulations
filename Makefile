# FRED Simulation Makefile
# Uses CLI approach with bash scripts

.PHONY: all run-fred build-fred analyze clean help

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

# Show available targets
help:
	@echo "Available targets:"
	@echo "  run-fred         - Run FRED simulation using CLI"
	@echo "  analyze          - Analyze simulation results with Python"
	@echo "  run-and-analyze  - Run simulation and analyze results"
	@echo "  build-fred       - Build the FRED framework"
	@echo "  clean            - Remove generated output files"
	@echo "  help             - Show this help message"
