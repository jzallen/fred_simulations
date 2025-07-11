# FRED Simulation Makefile
# Uses CLI approach with bash scripts

.PHONY: all run-fred build-fred clean help

# Default target
all: help

# Run FRED simulation via CLI (primary approach)
run-fred:
	./run_fred_simulation.sh

# Build FRED framework if needed
build-fred:
	cd fred-framework/src && make

# Clean generated files
clean:
	rm -rf output/
	rm -f simulation_config.fred

# Show available targets
help:
	@echo "Available targets:"
	@echo "  run-fred     - Run FRED simulation using CLI"
	@echo "  build-fred   - Build the FRED framework"
	@echo "  clean        - Remove generated output files"
	@echo "  help         - Show this help message"
