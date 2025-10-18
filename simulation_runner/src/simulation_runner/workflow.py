"""
Simulation workflow orchestration.

This module provides the main SimulationWorkflow class that coordinates
the entire simulation pipeline from download to execution.
"""

import json
import logging
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from simulation_runner.config import SimulationConfig
from simulation_runner.exceptions import (
    DownloadError,
    ExtractionError,
    FREDConfigError,
    SimulationError,
    ValidationError,
    WorkflowError,
)
from simulation_runner.fred_config_builder import FREDConfigBuilder

logger = logging.getLogger(__name__)


class SimulationWorkflow:
    """
    Orchestrates the FRED simulation workflow.

    This class manages the complete pipeline:
    1. Download job uploads from S3
    2. Extract archives
    3. Prepare FRED configurations
    4. Validate configurations
    5. Run simulations
    6. Collect outputs

    Examples
    --------
    >>> config = SimulationConfig.from_env(job_id=12, run_id=4)
    >>> workflow = SimulationWorkflow(config)
    >>> workflow.execute()
    PosixPath('/workspace/job_12')
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize simulation workflow.

        Parameters
        ----------
        config : SimulationConfig
            Configuration for the simulation
        """
        self.config = config
        self.workspace_dir = config.workspace_dir
        self.job_id = config.job_id
        self.run_id = config.run_id

    def download_uploads(self) -> Path:
        """
        Download job uploads using epistemix-cli.

        Returns
        -------
        Path
            Path to workspace directory with downloaded files

        Raises
        ------
        DownloadError
            If download fails
        """
        logger.info(
            "Starting download",
            extra={"job_id": self.job_id, "workspace": str(self.workspace_dir)},
        )

        # Create workspace directory
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Build epistemix-cli command
        cmd = [
            "epistemix-cli",
            "jobs",
            "uploads",
            "download",
            "--job-id",
            str(self.job_id),
            "--output-dir",
            str(self.workspace_dir),
            "-f",  # Force overwrite
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
            )

            logger.info(
                "Download completed",
                extra={
                    "job_id": self.job_id,
                    "stdout": result.stdout[:500],  # First 500 chars
                },
            )

            # Verify files were downloaded
            downloaded_files = list(self.workspace_dir.iterdir())
            if not downloaded_files:
                raise DownloadError(
                    f"No files downloaded for job {self.job_id}"
                )

            logger.info(
                "Files downloaded",
                extra={
                    "job_id": self.job_id,
                    "file_count": len(downloaded_files),
                },
            )

            return self.workspace_dir

        except subprocess.TimeoutExpired as e:
            raise DownloadError(
                f"Download timed out after 5 minutes for job {self.job_id}"
            ) from e
        except subprocess.CalledProcessError as e:
            raise DownloadError(
                f"Failed to download uploads for job {self.job_id}: "
                f"{e.stderr}"
            ) from e
        except Exception as e:
            raise DownloadError(
                f"Unexpected error downloading job {self.job_id}: {e}"
            ) from e

    def extract_archives(self) -> Path:
        """
        Extract job_input.zip if present.

        Returns
        -------
        Path
            Path to workspace directory

        Raises
        ------
        ExtractionError
            If extraction fails
        """
        job_input_zip = self.workspace_dir / "job_input.zip"

        if not job_input_zip.exists():
            logger.info(
                "No job_input.zip to extract",
                extra={"job_id": self.job_id},
            )
            return self.workspace_dir

        logger.info(
            "Extracting archive",
            extra={
                "job_id": self.job_id,
                "archive": str(job_input_zip),
            },
        )

        try:
            with zipfile.ZipFile(job_input_zip, "r") as zip_ref:
                zip_ref.extractall(self.workspace_dir)

            logger.info(
                "Archive extracted",
                extra={"job_id": self.job_id},
            )

            return self.workspace_dir

        except zipfile.BadZipFile as e:
            raise ExtractionError(
                f"Invalid zip file: {job_input_zip}"
            ) from e
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract {job_input_zip}: {e}"
            ) from e

    def prepare_configs(self) -> list[dict]:
        """
        Prepare FRED configurations for all runs.

        Returns
        -------
        list[dict]
            List of dicts with 'run_id', 'config_path', 'run_number' for each run

        Raises
        ------
        FREDConfigError
            If configuration preparation fails
        """
        # Find run config files
        if self.run_id is not None:
            # Specific run requested
            run_config_path = self.workspace_dir / f"run_{self.run_id}_config.json"
            if not run_config_path.exists():
                raise FREDConfigError(
                    f"Run config not found: {run_config_path}"
                )
            run_configs = [run_config_path]
        else:
            # Process all runs
            run_configs = sorted(
                self.workspace_dir.glob("run_*_config.json")
            )

        if not run_configs:
            raise FREDConfigError(
                f"No run config files found in {self.workspace_dir}"
            )

        logger.info(
            "Preparing FRED configs",
            extra={
                "job_id": self.job_id,
                "run_count": len(run_configs),
            },
        )

        # Check for main.fred
        main_fred = self.workspace_dir / "main.fred"
        if not main_fred.exists():
            raise FREDConfigError(
                f"main.fred not found in {self.workspace_dir}"
            )

        prepared_runs = []

        for run_config_path in run_configs:
            # Extract run ID from filename
            run_id = int(run_config_path.stem.split("_")[1])

            try:
                # Build prepared config using builder
                builder = FREDConfigBuilder.from_run_config(
                    run_config_path, main_fred
                )

                prepared_fred = self.workspace_dir / f"run_{run_id}_prepared.fred"
                builder.build(prepared_fred)

                run_number = builder.get_run_number()

                prepared_runs.append({
                    "run_id": run_id,
                    "config_path": prepared_fred,
                    "run_number": run_number,
                })

                logger.info(
                    "Prepared config",
                    extra={
                        "job_id": self.job_id,
                        "run_id": run_id,
                        "output": str(prepared_fred),
                    },
                )

            except Exception as e:
                raise FREDConfigError(
                    f"Failed to prepare config for run {run_id}: {e}"
                ) from e

        return prepared_runs

    def validate_configs(self, prepared_runs: list[dict]) -> list[dict]:
        """
        Validate FRED configurations.

        Parameters
        ----------
        prepared_runs : list[dict]
            List of prepared run configurations

        Returns
        -------
        list[dict]
            Input list with 'validation_log' added to each dict

        Raises
        ------
        ValidationError
            If any validation fails
        """
        fred_binary = self.config.get_fred_binary()

        logger.info(
            "Validating configs",
            extra={
                "job_id": self.job_id,
                "run_count": len(prepared_runs),
            },
        )

        for run_info in prepared_runs:
            run_id = run_info["run_id"]
            config_path = run_info["config_path"]

            validation_log = self.workspace_dir / f"run_{run_id}_validation.log"

            cmd = [
                str(fred_binary),
                "-p",
                str(config_path),
                "-c",  # Check/validate flag
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60,
                    env={"FRED_HOME": str(self.config.fred_home)},
                )

                # Write validation log
                with open(validation_log, "w") as f:
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\n\n=== STDERR ===\n")
                        f.write(result.stderr)

                run_info["validation_log"] = validation_log

                logger.info(
                    "Validation passed",
                    extra={
                        "job_id": self.job_id,
                        "run_id": run_id,
                        "log": str(validation_log),
                    },
                )

            except subprocess.CalledProcessError as e:
                # Write error log
                with open(validation_log, "w") as f:
                    f.write(f"VALIDATION FAILED\n\n")
                    f.write(e.stdout)
                    if e.stderr:
                        f.write("\n\n=== STDERR ===\n")
                        f.write(e.stderr)

                raise ValidationError(
                    f"FRED validation failed for run {run_id}. "
                    f"See {validation_log} for details."
                ) from e
            except subprocess.TimeoutExpired as e:
                raise ValidationError(
                    f"FRED validation timed out for run {run_id}"
                ) from e

        return prepared_runs

    def run_simulations(self, prepared_runs: list[dict]) -> list[dict]:
        """
        Execute FRED simulations.

        Parameters
        ----------
        prepared_runs : list[dict]
            List of validated run configurations

        Returns
        -------
        list[dict]
            Input list with 'output_dir' and 'simulation_log' added

        Raises
        ------
        SimulationError
            If any simulation fails
        """
        fred_binary = self.config.get_fred_binary()

        logger.info(
            "Running simulations",
            extra={
                "job_id": self.job_id,
                "run_count": len(prepared_runs),
            },
        )

        for run_info in prepared_runs:
            run_id = run_info["run_id"]
            config_path = run_info["config_path"]
            run_number = run_info["run_number"]

            output_dir = self.workspace_dir / "OUT" / f"run_{run_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            simulation_log = self.workspace_dir / f"run_{run_id}_simulation.log"

            cmd = [
                str(fred_binary),
                "-p",
                str(config_path),
                "-r",
                str(run_number),
                "-d",
                str(output_dir),
            ]

            logger.info(
                "Starting simulation",
                extra={
                    "job_id": self.job_id,
                    "run_id": run_id,
                    "run_number": run_number,
                },
            )

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=3600,  # 1 hour timeout
                    env={"FRED_HOME": str(self.config.fred_home)},
                )

                # Write simulation log
                with open(simulation_log, "w") as f:
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\n\n=== STDERR ===\n")
                        f.write(result.stderr)

                run_info["output_dir"] = output_dir
                run_info["simulation_log"] = simulation_log

                # Count output files
                output_files = list(output_dir.rglob("*"))
                output_count = len([f for f in output_files if f.is_file()])

                logger.info(
                    "Simulation completed",
                    extra={
                        "job_id": self.job_id,
                        "run_id": run_id,
                        "output_count": output_count,
                        "log": str(simulation_log),
                    },
                )

            except subprocess.CalledProcessError as e:
                # Write error log
                with open(simulation_log, "w") as f:
                    f.write(f"SIMULATION FAILED\n\n")
                    f.write(e.stdout)
                    if e.stderr:
                        f.write("\n\n=== STDERR ===\n")
                        f.write(e.stderr)

                raise SimulationError(
                    f"FRED simulation failed for run {run_id}. "
                    f"See {simulation_log} for details."
                ) from e
            except subprocess.TimeoutExpired as e:
                raise SimulationError(
                    f"FRED simulation timed out for run {run_id} "
                    f"(exceeded 1 hour)"
                ) from e

        return prepared_runs

    def execute(self) -> Path:
        """
        Execute complete simulation workflow.

        This method runs all stages in sequence:
        1. Download uploads
        2. Extract archives
        3. Prepare configs
        4. Validate configs
        5. Run simulations

        Returns
        -------
        Path
            Path to workspace directory with simulation outputs

        Raises
        ------
        WorkflowError
            If any stage fails

        Examples
        --------
        >>> config = SimulationConfig.from_env(job_id=12)
        >>> workflow = SimulationWorkflow(config)
        >>> workspace = workflow.execute()
        >>> print(f"Results in: {workspace}")
        """
        logger.info(
            "Starting workflow",
            extra={
                "job_id": self.job_id,
                "run_id": self.run_id,
            },
        )

        try:
            # Validate configuration
            errors = self.config.validate()
            if errors:
                raise WorkflowError(
                    f"Configuration validation failed: {'; '.join(errors)}"
                )

            # Execute pipeline stages
            self.download_uploads()
            self.extract_archives()
            prepared_runs = self.prepare_configs()
            validated_runs = self.validate_configs(prepared_runs)
            completed_runs = self.run_simulations(validated_runs)

            logger.info(
                "Workflow completed",
                extra={
                    "job_id": self.job_id,
                    "completed_runs": len(completed_runs),
                    "workspace": str(self.workspace_dir),
                },
            )

            return self.workspace_dir

        except (
            DownloadError,
            ExtractionError,
            FREDConfigError,
            ValidationError,
            SimulationError,
        ) as e:
            logger.error(
                "Workflow failed",
                extra={
                    "job_id": self.job_id,
                    "error": str(e),
                },
            )
            raise WorkflowError(f"Simulation workflow failed: {e}") from e
