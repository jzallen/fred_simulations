"""
FRED Simulation Runner CLI.

Command-line interface for orchestrating FRED epidemiological simulations
with support for downloading configurations, FRED 10/11+ compatibility,
and simulation execution.

Usage:
    simulation-runner run --job-id 12 --run-id 4
    simulation-runner validate --job-id 12
    simulation-runner prepare --job-id 12 --run-id 4
"""

import logging
from pathlib import Path

import click

from simulation_runner import __version__
from simulation_runner.config import SimulationConfig
from simulation_runner.exceptions import (
    ConfigurationError,
    FREDConfigError,
    SimulationRunnerError,
    ValidationError,
    WorkflowError,
)
from simulation_runner.fred_config_builder import FREDConfigBuilder
from simulation_runner.workflow import SimulationWorkflow


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set logging level",
)
def cli(log_level: str):
    """FRED Simulation Runner CLI.

    Orchestrates FRED epidemiological simulations from EPX job configurations.
    """
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))


@cli.command()
@click.option("--job-id", required=True, type=int, help="Job ID to process")
@click.option("--run-id", type=int, help="Specific run ID to process (optional)")
def run(job_id: int, run_id: int | None):
    """
    Run complete simulation workflow.

    Downloads job uploads, prepares FRED configurations, validates them,
    and executes simulations.

    Examples:
        simulation-runner run --job-id 12
        simulation-runner run --job-id 12 --run-id 4
    """
    try:
        click.echo(f"Starting simulation workflow for job {job_id}")
        if run_id:
            click.echo(f"Processing run {run_id}")

        # Load configuration
        config = SimulationConfig.from_env(job_id, run_id)

        # Validate configuration
        errors = config.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise click.ClickException(error_msg)

        # Execute workflow
        workflow = SimulationWorkflow(config)
        workspace = workflow.execute()

        # Summary
        click.echo()
        click.echo("=" * 60)
        click.echo("✓ Simulation workflow completed successfully")
        click.echo(f"Workspace: {workspace}")
        click.echo()

        # Count outputs
        output_dir = workspace / "OUT"
        if output_dir.exists():
            output_files = list(output_dir.rglob("*"))
            file_count = len([f for f in output_files if f.is_file()])
            click.echo(f"Generated {file_count} output files in {output_dir}")

        # List log files
        log_files = list(workspace.glob("*.log"))
        if log_files:
            click.echo()
            click.echo("Log files:")
            for log_file in log_files:
                size_kb = log_file.stat().st_size / 1024
                click.echo(f"  - {log_file.name} ({size_kb:.1f} KB)")

        click.echo("=" * 60)

    except ConfigurationError as e:
        raise click.ClickException(f"Configuration error: {e}")
    except WorkflowError as e:
        raise click.ClickException(f"Workflow error: {e}")
    except SimulationRunnerError as e:
        raise click.ClickException(f"Error: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
@click.option("--job-id", required=True, type=int, help="Job ID to validate")
@click.option("--run-id", type=int, help="Specific run ID to validate (optional)")
def validate(job_id: int, run_id: int | None):
    """
    Validate FRED configurations without running simulations.

    Downloads job uploads, prepares FRED configurations, and validates
    them using FRED -c flag, but does not execute simulations.

    Examples:
        simulation-runner validate --job-id 12
        simulation-runner validate --job-id 12 --run-id 4
    """
    try:
        click.echo(f"Validating configurations for job {job_id}")
        if run_id:
            click.echo(f"Processing run {run_id}")

        # Load configuration
        config = SimulationConfig.from_env(job_id, run_id)

        # Execute download, extract, prepare, and validate (but not simulate)
        workflow = SimulationWorkflow(config)
        workflow.download_uploads()
        workflow.extract_archives()
        prepared_runs = workflow.prepare_configs()
        validated_runs = workflow.validate_configs(prepared_runs)

        # Summary
        click.echo()
        click.echo("=" * 60)
        click.echo(f"✓ All {len(validated_runs)} configuration(s) validated successfully")
        click.echo()

        for run_info in validated_runs:
            click.echo(f"Run {run_info['run_id']}:")
            click.echo(f"  Config: {run_info['config_path']}")
            click.echo(f"  Validation log: {run_info['validation_log']}")
            click.echo()

        click.echo("=" * 60)

    except ConfigurationError as e:
        raise click.ClickException(f"Configuration error: {e}")
    except ValidationError as e:
        raise click.ClickException(f"Validation failed: {e}")
    except SimulationRunnerError as e:
        raise click.ClickException(f"Error: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
@click.argument("run_config", type=click.Path(exists=True, path_type=Path))
@click.argument("input_fred", type=click.Path(exists=True, path_type=Path))
@click.argument("output_fred", type=click.Path(path_type=Path))
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def prepare(run_config: Path, input_fred: Path, output_fred: Path, verbose: bool):
    """
    Prepare FRED 10 configuration from EPX run config.

    Converts EPX run config JSON to FRED 10 .fred file format by injecting
    start_date, end_date, and locations into the .fred file.

    Examples:
        simulation-runner prepare run_4_config.json main.fred prepared.fred
        simulation-runner prepare run_config.json main.fred out.fred --verbose
    """
    try:
        if verbose:
            click.echo(f"Loading run configuration: {run_config}")
            click.echo(f"Input FRED file: {input_fred}")
            click.echo(f"Output FRED file: {output_fred}")

        # Build configuration
        builder = FREDConfigBuilder.from_run_config(run_config, input_fred)
        result = builder.build(output_fred)
        run_number = builder.get_run_number()

        click.echo(f"✓ Successfully prepared FRED configuration: {result}")
        click.echo()
        click.echo("To run FRED with this configuration:")
        click.echo("  export FRED_HOME=/workspaces/fred_simulations/fred-framework")
        click.echo(f"  FRED -p {result} -r {run_number} -d OUT")

    except FREDConfigError as e:
        raise click.ClickException(f"Failed to prepare configuration: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
@click.option("--job-id", required=True, type=int, help="Job ID to download")
@click.option("--output-dir", type=click.Path(path_type=Path), help="Output directory")
def download(job_id: int, output_dir: Path | None):
    """
    Download job uploads without processing.

    Downloads all uploads for a job to the specified directory.

    Examples:
        simulation-runner download --job-id 12
        simulation-runner download --job-id 12 --output-dir /tmp/job_12
    """
    try:
        if output_dir is None:
            output_dir = Path(f"/workspace/job_{job_id}")

        click.echo(f"Downloading uploads for job {job_id} to {output_dir}")

        # Use minimal config just for download
        config = SimulationConfig.from_env(job_id)
        if output_dir:
            config.workspace_dir = output_dir

        workflow = SimulationWorkflow(config)
        workspace = workflow.download_uploads()

        # List downloaded files
        files = list(workspace.iterdir())
        click.echo()
        click.echo(f"✓ Downloaded {len(files)} files:")
        for file in files:
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                click.echo(f"  - {file.name} ({size_kb:.1f} KB)")

    except SimulationRunnerError as e:
        raise click.ClickException(f"Download failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
def version():
    """Show simulation runner version."""
    click.echo(f"FRED Simulation Runner v{__version__}")
    click.echo()
    click.echo("Part of the fred_simulations project")
    click.echo("https://github.com/jzallen/fred_simulations")


@cli.command()
def config():
    """Show current configuration from environment."""
    try:
        # Try to load config for a dummy job ID just to show settings
        test_config = SimulationConfig.from_env(job_id=1)

        click.echo("Current Configuration:")
        click.echo("=" * 60)
        click.echo(f"FRED_HOME:          {test_config.fred_home}")
        click.echo(f"EPISTEMIX_API_URL:  {test_config.api_url or '(not set)'}")
        click.echo(f"EPISTEMIX_S3_BUCKET: {test_config.s3_bucket or '(not set)'}")
        click.echo(f"AWS_REGION:         {test_config.aws_region}")
        click.echo(f"DATABASE_URL:       {test_config.database_url}")
        click.echo("=" * 60)

        # Validate
        errors = test_config.validate()
        if errors:
            click.echo()
            click.echo("Configuration Issues:")
            for error in errors:
                click.echo(f"  ⚠ {error}")
        else:
            click.echo()
            click.echo("✓ Configuration is valid")

    except ConfigurationError as e:
        raise click.ClickException(f"Configuration error: {e}")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
