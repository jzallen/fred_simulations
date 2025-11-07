"""
Run simulation use case.

Orchestrates simulation execution by submitting runs to AWS Batch
via the simulation runner gateway.
"""

import functools
import logging
from epistemix_platform.models import Run
from epistemix_platform.gateways.interfaces import ISimulationRunner


logger = logging.getLogger(__name__)


def run_simulation(
    run: Run,
    simulation_runner: ISimulationRunner,
) -> Run:
    """
    Submit a run for execution on AWS Batch.

    This use case orchestrates submitting a Run to AWS Batch via the simulation
    runner gateway. The Run object is passed directly from the caller (typically
    from submit_runs use case which already has the Run).

    AWS Batch is the source of truth for job state. The run object is not
    modified or saved after submission. Jobs are tracked by name (run.natural_key()).

    Args:
        run: The Run object to execute
        simulation_runner: Gateway for AWS Batch integration

    Returns:
        The Run (unmodified - AWS Batch is source of truth)
    """
    # Submit run to AWS Batch via gateway (does not modify run object)
    simulation_runner.submit_run(run)

    logger.info(
        f"Submitted run {run.id} to AWS Batch with job name: {run.natural_key()}"
    )

    return run


def create_run_simulation(
    simulation_runner: ISimulationRunner,
):
    """Factory to create run_simulation function with simulation_runner wired."""
    return functools.partial(
        run_simulation, simulation_runner=simulation_runner
    )
