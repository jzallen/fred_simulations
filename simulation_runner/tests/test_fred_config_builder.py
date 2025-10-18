"""
Tests for FREDConfigBuilder class.
"""

import pytest

from simulation_runner.exceptions import FREDConfigError
from simulation_runner.fred_config_builder import FREDConfigBuilder


class TestFREDConfigBuilder:
    """Tests for FRED configuration builder."""

    def test_builder_requires_existing_file(self, tmp_path):
        """Test that builder requires input file to exist."""
        nonexistent = tmp_path / "nonexistent.fred"

        with pytest.raises(FREDConfigError, match="Input FRED file not found"):
            FREDConfigBuilder(nonexistent)

    def test_builder_with_dates(self, sample_fred_file):
        """Test builder with date parameters."""
        builder = FREDConfigBuilder(sample_fred_file)
        result = builder.with_dates("2020-01-01", "2020-03-31")

        assert result is builder  # Fluent API
        assert builder._start_date == "2020-Jan-01"
        assert builder._end_date == "2020-Mar-31"

    def test_builder_with_locations(self, sample_fred_file):
        """Test builder with location parameters."""
        builder = FREDConfigBuilder(sample_fred_file)
        result = builder.with_locations(["Allegheny_County_PA", "Philadelphia_County_PA"])

        assert result is builder  # Fluent API
        assert builder._locations == ["Allegheny_County_PA", "Philadelphia_County_PA"]

    def test_builder_with_seed(self, sample_fred_file):
        """Test builder with seed parameter."""
        builder = FREDConfigBuilder(sample_fred_file)
        result = builder.with_seed(12345)

        assert result is builder  # Fluent API
        assert builder._seed == 12345

    def test_builder_build_creates_file(self, sample_fred_file, tmp_path):
        """Test that build creates output file."""
        output = tmp_path / "output.fred"

        builder = FREDConfigBuilder(sample_fred_file)
        builder.with_dates("2020-01-01", "2020-03-31")
        builder.with_locations(["Allegheny_County_PA"])
        result = builder.build(output)

        assert result == output
        assert output.exists()

    def test_builder_build_includes_dates(self, sample_fred_file, tmp_path):
        """Test that build includes date parameters in output."""
        output = tmp_path / "output.fred"

        builder = FREDConfigBuilder(sample_fred_file)
        builder.with_dates("2020-01-01", "2020-03-31")
        builder.build(output)

        content = output.read_text()
        assert "start_date = 2020-Jan-01" in content
        assert "end_date = 2020-Mar-31" in content

    def test_builder_build_includes_locations(self, sample_fred_file, tmp_path):
        """Test that build includes location parameters in output."""
        output = tmp_path / "output.fred"

        builder = FREDConfigBuilder(sample_fred_file)
        builder.with_locations(["Allegheny_County_PA"])
        builder.build(output)

        content = output.read_text()
        assert "locations = Allegheny_County_PA" in content

    def test_builder_build_preserves_original_content(self, sample_fred_file, tmp_path):
        """Test that build preserves original file content."""
        output = tmp_path / "output.fred"

        builder = FREDConfigBuilder(sample_fred_file)
        builder.with_dates("2020-01-01")
        builder.build(output)

        output_content = output.read_text()
        assert "condition TEST" in output_content  # From original
        assert "states = S I R" in output_content  # From original

    def test_builder_from_run_config(self, sample_run_config, sample_fred_file):
        """Test creating builder from run config JSON."""
        builder = FREDConfigBuilder.from_run_config(sample_run_config, sample_fred_file)

        assert builder._start_date == "2020-Jan-01"
        assert builder._end_date == "2020-Mar-31"
        assert builder._locations == ["Allegheny_County_PA"]
        assert builder._seed == 12345

    def test_builder_from_run_config_missing_file(self, tmp_path, sample_fred_file):
        """Test error when run config file is missing."""
        nonexistent = tmp_path / "missing.json"

        with pytest.raises(FREDConfigError, match="Failed to load run config"):
            FREDConfigBuilder.from_run_config(nonexistent, sample_fred_file)

    def test_builder_get_run_number_from_seed(self, sample_fred_file):
        """Test calculating run number from seed."""
        builder = FREDConfigBuilder(sample_fred_file)
        builder.with_seed(6401899875233727325)

        run_number = builder.get_run_number()

        # Should be seed % 2^16 + 1
        expected = (6401899875233727325 % (2**16)) + 1
        assert run_number == expected

    def test_builder_get_run_number_default(self, sample_fred_file):
        """Test default run number when no seed is set."""
        builder = FREDConfigBuilder(sample_fred_file)

        run_number = builder.get_run_number()
        assert run_number == 1

    def test_builder_fluent_api_chain(self, sample_fred_file, tmp_path):
        """Test that builder methods can be chained."""
        output = tmp_path / "output.fred"

        result = (
            FREDConfigBuilder(sample_fred_file)
            .with_dates("2020-01-01", "2020-03-31")
            .with_locations(["Allegheny_County_PA"])
            .with_seed(12345)
            .build(output)
        )

        assert result == output
        assert output.exists()
