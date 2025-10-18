"""
FRED Simulation Runner package.

This package provides tools for running FRED epidemiological simulations
with support for downloading configurations, FRED 10/11+ compatibility,
and simulation execution.
"""

from simulation_runner.config import SimulationConfig
from simulation_runner.fred_config_builder import FREDConfigBuilder
from simulation_runner.workflow import SimulationWorkflow


__all__ = [
    "SimulationConfig",
    "FREDConfigBuilder",
    "SimulationWorkflow",
]

__version__ = "1.0.0"
