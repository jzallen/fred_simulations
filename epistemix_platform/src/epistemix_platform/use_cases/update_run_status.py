"""
Update run status use case for the Epistemix API.
This module implements the core business logic for synchronizing run status with AWS Batch.
"""

import functools
import logging

from epistemix_platform.models.run import Run
from epistemix_platform.repositories.interfaces import IRunRepository
from epistemix_platform.gateways.interfaces import ISimulationRunner


logger = logging.getLogger(__name__)


def update_run_status(
    simulation_runner: ISimulationRunner,
    run_repository: IRunRepository,
    run: Run,
) -> bool:
    """
    Synchronize run status with AWS Batch and persist if changed.

    Args:
        simulation_runner: Gateway for AWS Batch integration
        run_repository: Repository for run persistence
        run: Run entity to update

    Returns:
        True if status was updated, False otherwise
    """
    status_detail = simulation_runner.describe_run(run)

    status_changed = (
        run.status != status_detail.status or run.pod_phase != status_detail.pod_phase
    )

    if status_changed:
        logger.info(
            f"Status change for run {run.id}: "
            f"{run.status.name}/{run.pod_phase.name} → "
            f"{status_detail.status.name}/{status_detail.pod_phase.name}"
        )
        run.status = status_detail.status
        run.pod_phase = status_detail.pod_phase
        run_repository.save(run)
        return True

    return False


def create_update_run_status(
    simulation_runner: ISimulationRunner, run_repository: IRunRepository
):
    """Factory to create update_run_status function with dependencies wired."""
    return functools.partial(update_run_status, simulation_runner, run_repository)
