"""
Builder for FRED 10 configuration files.

This module provides a fluent builder pattern for constructing FRED 10
configuration files from EPX run configs. It handles the conversion from
FRED 11+ format (CLI arguments) to FRED 10 format (in-file parameters).
"""

import json
import logging
from pathlib import Path
from typing import Optional

from simulation_runner.exceptions import FREDConfigError
from simulation_runner.utils.date_converter import convert_date_to_fred10_format

logger = logging.getLogger(__name__)


class FREDConfigBuilder:
    """
    Builder for FRED 10 configuration files.

    This class provides a fluent API for constructing FRED 10 .fred files
    by injecting parameters (dates, locations, etc.) at the beginning of
    an existing .fred file.

    Examples
    --------
    >>> builder = FREDConfigBuilder(Path("main.fred"))
    >>> builder.with_dates("2020-01-01", "2020-03-31") \\
    ...        .with_locations(["Allegheny_County_PA"]) \\
    ...        .build(Path("prepared.fred"))
    PosixPath('prepared.fred')
    """

    def __init__(self, input_fred_path: Path):
        """
        Initialize builder with input FRED file.

        Parameters
        ----------
        input_fred_path : Path
            Path to the base .fred file (e.g., main.fred)

        Raises
        ------
        FREDConfigError
            If input_fred_path does not exist
        """
        if not input_fred_path.exists():
            raise FREDConfigError(
                f"Input FRED file not found: {input_fred_path}"
            )

        self.input_fred_path = input_fred_path
        self._start_date: Optional[str] = None
        self._end_date: Optional[str] = None
        self._locations: list[str] = []
        self._seed: Optional[int] = None

    def with_dates(
        self, start_date: str, end_date: Optional[str] = None
    ) -> "FREDConfigBuilder":
        """
        Add simulation dates to the configuration.

        Dates should be in ISO format (YYYY-MM-DD) and will be converted
        to FRED 10 format (YYYY-Mon-DD) automatically.

        Parameters
        ----------
        start_date : str
            Simulation start date in ISO format (YYYY-MM-DD)
        end_date : Optional[str]
            Simulation end date in ISO format (YYYY-MM-DD)

        Returns
        -------
        FREDConfigBuilder
            Self for method chaining

        Raises
        ------
        FREDConfigError
            If date format is invalid
        """
        try:
            self._start_date = convert_date_to_fred10_format(start_date)
            if end_date:
                self._end_date = convert_date_to_fred10_format(end_date)
        except ValueError as e:
            raise FREDConfigError(f"Invalid date format: {e}") from e

        return self

    def with_locations(self, locations: list[str]) -> "FREDConfigBuilder":
        """
        Add simulation locations.

        Parameters
        ----------
        locations : list[str]
            List of location names (e.g., ["Allegheny_County_PA"])

        Returns
        -------
        FREDConfigBuilder
            Self for method chaining
        """
        self._locations = locations
        return self

    def with_seed(self, seed: int) -> "FREDConfigBuilder":
        """
        Add random seed for simulation.

        Parameters
        ----------
        seed : int
            Random seed value

        Returns
        -------
        FREDConfigBuilder
            Self for method chaining
        """
        self._seed = seed
        return self

    @classmethod
    def from_run_config(
        cls, run_config_path: Path, input_fred_path: Path
    ) -> "FREDConfigBuilder":
        """
        Create builder from EPX run config JSON file.

        This is a convenience method that extracts parameters from an
        EPX run_config.json file and initializes the builder.

        Parameters
        ----------
        run_config_path : Path
            Path to run_config.json file
        input_fred_path : Path
            Path to the base .fred file

        Returns
        -------
        FREDConfigBuilder
            Builder initialized with parameters from run config

        Raises
        ------
        FREDConfigError
            If run_config cannot be loaded or parsed

        Examples
        --------
        >>> builder = FREDConfigBuilder.from_run_config(
        ...     Path("run_4_config.json"),
        ...     Path("main.fred")
        ... )
        >>> builder.build(Path("prepared.fred"))
        """
        try:
            with open(run_config_path, encoding="utf-8") as f:
                run_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise FREDConfigError(
                f"Failed to load run config from {run_config_path}: {e}"
            ) from e

        # Extract parameters
        params = run_config.get("params", {})
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        synth_pop = params.get("synth_pop", {})
        locations = synth_pop.get("locations", [])
        seed = params.get("seed")

        # Initialize builder
        builder = cls(input_fred_path)

        # Add parameters
        if start_date:
            builder.with_dates(start_date, end_date)

        if locations:
            builder.with_locations(locations)

        if seed is not None:
            builder.with_seed(seed)

        logger.info(
            "Loaded run config",
            extra={
                "run_config": str(run_config_path),
                "start_date": start_date,
                "end_date": end_date,
                "locations": locations,
                "seed": seed,
            },
        )

        return builder

    def build(self, output_fred_path: Path) -> Path:
        """
        Build the FRED configuration file.

        This method reads the input .fred file, injects the configured
        parameters at the beginning, and writes to the output path.

        Parameters
        ----------
        output_fred_path : Path
            Path where the prepared .fred file should be written

        Returns
        -------
        Path
            Path to the generated .fred file (same as output_fred_path)

        Raises
        ------
        FREDConfigError
            If file operations fail

        Examples
        --------
        >>> builder = FREDConfigBuilder(Path("main.fred"))
        >>> builder.with_dates("2020-01-01").build(Path("out.fred"))
        PosixPath('out.fred')
        """
        try:
            # Read original fred file
            with open(self.input_fred_path, encoding="utf-8") as f:
                original_content = f.read()
        except IOError as e:
            raise FREDConfigError(
                f"Failed to read input FRED file {self.input_fred_path}: {e}"
            ) from e

        # Build parameter header
        header_lines = [
            "##################################################",
            "# FRED 10 Configuration",
            "# Auto-generated from EPX run config",
            "##################################################",
            "",
        ]

        # Add simulation timeframe
        if self._start_date:
            header_lines.append("##### SIMULATED TIMEFRAME")
            header_lines.append(f"start_date = {self._start_date}")
            if self._end_date:
                header_lines.append(f"end_date = {self._end_date}")
            header_lines.append("")

        # Add locations
        if self._locations:
            header_lines.append("##### SIMULATED LOCATION")
            for location in self._locations:
                header_lines.append(f"locations = {location}")
            header_lines.append("")

        # Add seed if specified (for reproducibility)
        if self._seed is not None:
            header_lines.append("##### RANDOM SEED")
            header_lines.append(f"# Original seed: {self._seed}")
            header_lines.append("# (Use -r flag with FRED to specify run number)")
            header_lines.append("")

        header_lines.append("##################################################")
        header_lines.append("")

        # Combine header with original content
        header = "\n".join(header_lines)
        final_content = header + original_content

        # Write to output file
        try:
            # Ensure output directory exists
            output_fred_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_fred_path, "w", encoding="utf-8") as f:
                f.write(final_content)

            logger.info(
                "Generated FRED config",
                extra={
                    "input": str(self.input_fred_path),
                    "output": str(output_fred_path),
                    "start_date": self._start_date,
                    "end_date": self._end_date,
                    "locations": self._locations,
                },
            )

            return output_fred_path

        except IOError as e:
            raise FREDConfigError(
                f"Failed to write output FRED file {output_fred_path}: {e}"
            ) from e

    def get_run_number(self) -> int:
        """
        Calculate FRED run number from seed.

        FRED 10 uses 16-bit run numbers (1-65536), so we convert
        the 64-bit seed using modulo operation.

        Returns
        -------
        int
            Run number for use with FRED -r flag (1-65536)

        Examples
        --------
        >>> builder = FREDConfigBuilder(Path("main.fred"))
        >>> builder.with_seed(6401899875233727325)
        >>> builder.get_run_number()
        11998
        """
        if self._seed is None:
            return 1

        # FRED 10 uses 16-bit run numbers
        max_run_number = 2**16
        return (self._seed % max_run_number) + 1
