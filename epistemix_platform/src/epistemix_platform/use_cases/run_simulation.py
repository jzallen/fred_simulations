"""
Run simulation use case.

Orchestrates simulation execution by submitting runs to AWS Batch
via the simulation runner gateway.
"""

import logging
from epistemix_platform.models import Run
from epistemix_platform.repositories.interfaces import IRunRepository
from epistemix_platform.gateways.interfaces import ISimulationRunner


logger = logging.getLogger(__name__)


def run_simulation(
    run_id: int,
    run_repository: IRunRepository,
    simulation_runner: ISimulationRunner,
) -> Run:
    """
    Submit a run for execution on AWS Batch.

    This use case orchestrates the process of:
    1. Retrieving the run from the repository
    2. Submitting it to AWS Batch via the simulation runner gateway
    3. Saving the updated run (with aws_batch_job_id) back to the repository

    Args:
        run_id: ID of the run to execute
        run_repository: Repository for run persistence
        simulation_runner: Gateway for AWS Batch integration

    Returns:
        The updated Run with aws_batch_job_id set

    Raises:
        ValueError: If run not found in repository
    """
    # Retrieve run from repository
    run = run_repository.find_by_id(run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")

    # Submit run to AWS Batch via gateway
    simulation_runner.submit_run(run)

    # Save updated run (now has aws_batch_job_id)
    run_repository.save(run)

    logger.info(
        f"Submitted run {run_id} to AWS Batch with job ID: {run.aws_batch_job_id}"
    )

    return run
