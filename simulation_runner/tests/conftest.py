"""
Pytest configuration and fixtures for simulation_runner tests.
"""

import tempfile
from pathlib import Path

import pytest

from simulation_runner.config import SimulationConfig


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_fred_file(tmp_path):
    """Create a sample FRED configuration file for testing."""
    fred_file = tmp_path / "main.fred"
    fred_file.write_text("""
# Sample FRED configuration file
condition TEST {
    states = S I R
    start_state = S
}
""")
    return fred_file


@pytest.fixture
def sample_run_config(tmp_path):
    """Create a sample run config JSON for testing."""
    import json

    run_config = tmp_path / "run_1_config.json"
    config_data = {
        "job_id": 1,
        "run_id": 1,
        "params": {
            "start_date": "2020-01-01",
            "end_date": "2020-03-31",
            "synth_pop": {
                "version": "US_2010.v5",
                "locations": ["Allegheny_County_PA"]
            },
            "seed": 12345
        },
        "fred_version": "latest"
    }
    run_config.write_text(json.dumps(config_data, indent=2))
    return run_config


@pytest.fixture
def test_config(temp_workspace):
    """Create test simulation configuration."""
    return SimulationConfig(
        job_id=1,
        run_id=1,
        fred_home=Path("/workspaces/fred_simulations/fred-framework"),
        workspace_dir=temp_workspace,
        api_url="http://localhost:5000",
        s3_bucket="test-bucket",
        aws_region="us-east-1",
        database_url="sqlite:///test.db"
    )
