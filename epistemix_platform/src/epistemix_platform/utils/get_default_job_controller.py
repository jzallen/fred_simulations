"""
Factory function for creating a JobController with default dependencies.

This module provides a shared implementation of get_job_controller that can be
used by both app.py (Flask) and cli.py to avoid code duplication.
"""

from collections.abc import Callable

from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.gateways.simulation_runner import AWSBatchSimulationRunner
from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.repositories import SQLAlchemyJobRepository, SQLAlchemyRunRepository
from epistemix_platform.repositories.s3_results_repository import S3ResultsRepository
from epistemix_platform.repositories.s3_upload_location_repository import (
    create_upload_location_repository,
)


def create_job_controller(
    session_factory: Callable,
    environment: str,
    bucket_name: str,
    region_name: str,
) -> JobController:
    """
    Create a JobController instance with default dependencies.

    This function encapsulates the common logic for creating a JobController
    with all required repositories and gateways. It can be used by both the
    Flask app (app.py) and CLI (cli.py).

    Args:
        session_factory: Callable that returns a database session
        environment: Environment name (e.g., "dev", "staging", "prod")
        bucket_name: S3 bucket name for uploads
        region_name: AWS region name

    Returns:
        Configured JobController instance

    Example:
        # In app.py (Flask)
        def get_job_controller():
            return create_job_controller(
                session_factory=lambda: g.db_session,
                environment=app.config["ENVIRONMENT"],
                bucket_name=app.config["S3_UPLOAD_BUCKET"],
                region_name=app.config["AWS_REGION"],
            )

        # In cli.py
        def get_job_controller():
            config = get_config()
            session = get_database_session()
            return create_job_controller(
                session_factory=lambda: session,
                environment=config.ENVIRONMENT,
                bucket_name=config.S3_UPLOAD_BUCKET,
                region_name=config.AWS_REGION,
            )
    """
    # Create mappers
    job_mapper = JobMapper()
    run_mapper = RunMapper()

    # Create repository instances with injected mappers
    job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
    run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)

    # Create upload location repository
    upload_location_repository = create_upload_location_repository(
        env=environment, bucket_name=bucket_name, region_name=region_name
    )

    # Create S3 results repository
    results_repository = S3ResultsRepository(bucket_name=bucket_name, region_name=region_name)

    # Create simulation runner gateway
    simulation_runner = AWSBatchSimulationRunner.create(environment=environment, region=region_name)

    # Create and return JobController
    return JobController.create_with_repositories(
        job_repository=job_repository,
        run_repository=run_repository,
        upload_location_repository=upload_location_repository,
        results_repository=results_repository,
        simulation_runner=simulation_runner,
    )
