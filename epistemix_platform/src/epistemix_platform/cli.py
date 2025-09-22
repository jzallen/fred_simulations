#!/usr/bin/env python3
"""
Epistemix CLI for interacting with jobs and uploads.

Usage:
    epistemix jobs --job-id=<job-id>  # Get job and runs info
    epistemix jobs upload --location=<upload-location>  # Read upload contents
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

import click
from dotenv import load_dotenv
from returns.pipeline import is_successful

from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.repositories.database import get_database_manager
from epistemix_platform.repositories.job_repository import SQLAlchemyJobRepository
from epistemix_platform.repositories.run_repository import SQLAlchemyRunRepository
from epistemix_platform.repositories.s3_upload_location_repository import (
    create_upload_location_repository,
)
from epistemix_platform.use_cases.get_job import get_job
from epistemix_platform.use_cases.get_runs import get_runs_by_job_id
from epistemix_platform.use_cases.list_jobs import list_jobs

# Load configuration from ~/.epistemix/cli.env if it exists
CONFIG_PATH = Path.home() / ".epistemix" / "cli.env"
if CONFIG_PATH.exists():
    load_dotenv(CONFIG_PATH)
else:
    # Try loading from current directory as fallback
    load_dotenv("cli.env")

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_default_config() -> Dict[str, str]:
    """Get default configuration from environment variables."""
    return {
        "env": os.getenv("EPISTEMIX_ENV", "PRODUCTION"),
        "bucket": os.getenv("EPISTEMIX_S3_BUCKET"),  # None if not set
        "region": os.getenv("AWS_REGION"),  # None if not set
        "database_url": os.getenv("DATABASE_URL", "sqlite:///epistemix_jobs.db"),
    }


def get_database_session():
    """Get a database session."""
    config = get_default_config()
    db_manager = get_database_manager(config["database_url"])
    db_manager.create_tables()
    return db_manager.get_session()


def format_job_uploads(uploads: list) -> str:
    """Format job uploads for display."""
    if not uploads:
        return "No uploads found for this job."

    output = []
    output.append("=" * 80)

    # Group uploads by type
    job_uploads = [u for u in uploads if u.get("runId") is None]
    run_uploads = [u for u in uploads if u.get("runId") is not None]

    # Display job uploads
    if job_uploads:
        output.append(f"Job {uploads[0]['jobId']} Uploads:")
        output.append("-" * 80)

        for upload in job_uploads:
            output.append(f"\n[{upload['uploadType'].upper()}]")
            output.append(f"Location: {upload.get('location', {}).get('url', 'N/A')}")

            # Handle content based on new structure
            if upload.get("content"):
                content_obj = upload["content"]
                content_type = content_obj.get("contentType", "unknown")
                raw_content = content_obj.get("content", "")

                output.append(f"Content Type: {content_type}")

                # Truncate very long content
                if len(raw_content) > 1000:
                    raw_content = raw_content[:997] + "..."
                output.append(f"Content:\n{raw_content}")
            elif upload.get("error"):
                output.append(f"Error: {upload['error']}")
            else:
                output.append("(No content available)")
            output.append("-" * 40)

    # Display run uploads
    if run_uploads:
        output.append("\nRun Uploads:")
        output.append("-" * 80)

        # Group by run ID
        runs_by_id = {}
        for upload in run_uploads:
            run_id = upload["runId"]
            if run_id not in runs_by_id:
                runs_by_id[run_id] = []
            runs_by_id[run_id].append(upload)

        for run_id, run_uploads_list in runs_by_id.items():
            output.append(f"\nRun ID: {run_id}")
            for upload in run_uploads_list:
                output.append(f"  [{upload['uploadType'].upper()}]")
                output.append(f"  Location: {upload.get('location', {}).get('url', 'N/A')}")

                if upload.get("content"):
                    content_obj = upload["content"]
                    content_type = content_obj.get("contentType", "unknown")
                    raw_content = content_obj.get("content", "")

                    output.append(f"  Content Type: {content_type}")

                    # Indent content for run uploads
                    if len(raw_content) > 800:
                        raw_content = raw_content[:797] + "..."
                    content_lines = raw_content.split("\n")
                    for line in content_lines[:20]:  # Limit lines shown
                        output.append(f"    {line}")
                    if len(content_lines) > 20:
                        output.append(f"    ... ({len(content_lines) - 20} more lines)")
                elif upload.get("error"):
                    output.append(f"    Error: {upload['error']}")
                else:
                    output.append("    (No content available)")
            output.append("  " + "-" * 38)

    output.append("=" * 80)
    output.append(f"Total uploads found: {len(uploads)}")

    return "\n".join(output)


def format_jobs_list(jobs: list) -> str:
    """Format a list of jobs for display."""
    if not jobs:
        return "No jobs found."

    output = []
    output.append("=" * 80)
    output.append(f"{'ID':<8} {'User ID':<10} {'Status':<12} {'Tags':<30} {'Created'}")
    output.append("-" * 80)

    for job in jobs:
        tags_str = ", ".join(job.get("tags", []))[:28]  # Truncate long tags
        if len(tags_str) == 28:
            tags_str += ".."

        created_str = job.get("createdAt", "N/A")
        if created_str != "N/A":
            # Simplify timestamp display
            created_str = created_str.replace("T", " ").split(".")[0]

        output.append(
            f"{job['id']:<8} {job['userId']:<10} {job.get('status', 'N/A'):<12} "
            f"{tags_str:<30} {created_str}"
        )

    output.append("-" * 80)
    output.append(f"Total jobs: {len(jobs)}")
    output.append("=" * 80)

    return "\n".join(output)


def format_job_output(job_data: dict, runs_data: list) -> str:
    """Format job and runs data for display."""
    output = []
    output.append("=" * 60)
    output.append(f"Job ID: {job_data['id']}")
    output.append(f"User ID: {job_data['userId']}")
    output.append(f"Tags: {', '.join(job_data.get('tags', []))}")
    output.append(f"Created: {job_data.get('createdAt', 'N/A')}")
    output.append("=" * 60)

    if runs_data:
        output.append(f"\nRuns ({len(runs_data)} total):")
        output.append("-" * 60)

        for run in runs_data:
            output.append(f"\nRun ID: {run['id']}")
            output.append(f"  Status: {run.get('status', 'N/A')}")
            output.append(f"  Pod Phase: {run.get('podPhase', 'N/A')}")
            output.append(f"  Created: {run.get('createdTs', 'N/A')}")

            # Show request details if available
            request = run.get("request", {})
            if request:
                output.append(f"  Working Dir: {request.get('workingDir', 'N/A')}")
                output.append(f"  Size: {request.get('size', 'N/A')}")
                output.append(f"  FRED Version: {request.get('fredVersion', 'N/A')}")

                # Show population info
                population = request.get("population", {})
                if population:
                    output.append(f"  Population Version: {population.get('version', 'N/A')}")
                    locations = population.get("locations", [])
                    if locations:
                        output.append(f"  Locations: {', '.join(locations)}")

                # Show FRED args
                fred_args = request.get("fredArgs", [])
                if fred_args:
                    args_str = " ".join(
                        [f"{arg.get('flag', '')} {arg.get('value', '')}" for arg in fred_args]
                    )
                    output.append(f"  FRED Args: {args_str}")

                # Show FRED files
                fred_files = request.get("fredFiles", [])
                if fred_files:
                    output.append(f"  FRED Files: {len(fred_files)} file(s)")
                    for file in fred_files[:3]:  # Show first 3 files
                        output.append(f"    - {file}")
                    if len(fred_files) > 3:
                        output.append(f"    ... and {len(fred_files) - 3} more")

            output.append("-" * 60)
    else:
        output.append("\nNo runs found for this job.")

    return "\n".join(output)


@click.group()
def cli():
    """Epistemix CLI for managing jobs and uploads."""
    pass


@cli.group()
def jobs():
    """Commands for managing jobs."""
    pass


@jobs.command("list")
@click.option("--limit", type=int, help="Maximum number of jobs to display")
@click.option("--offset", type=int, default=0, help="Number of jobs to skip (for pagination)")
@click.option("--user-id", type=int, help="Filter jobs by user ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def list_all_jobs(limit: Optional[int], offset: int, user_id: Optional[int], json_output: bool):
    """List all jobs in the database."""
    try:
        # Get database session
        session = get_database_session()

        def session_factory():
            return session

        # Create repository with mapper
        job_mapper = JobMapper()
        job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)

        # Get jobs using the use case
        jobs = list_jobs(job_repository=job_repository, limit=limit, offset=offset, user_id=user_id)

        # Convert jobs to dicts
        jobs_data = []
        for job in jobs:
            job_dict = {
                "id": job.id,
                "userId": job.user_id,
                "tags": job.tags,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "createdAt": job.created_at.isoformat() if job.created_at else None,
            }
            jobs_data.append(job_dict)

        # Output results
        if json_output:
            output = {"jobs": jobs_data, "count": len(jobs_data), "offset": offset}
            if limit:
                output["limit"] = limit
            if user_id:
                output["userId"] = user_id
            click.echo(json.dumps(output, indent=2))
        else:
            if user_id:
                click.echo(f"\nJobs for User ID: {user_id}")
            click.echo(format_jobs_list(jobs_data))

        session.close()

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command("info")
@click.option("--job-id", required=True, type=int, help="Job ID to retrieve")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def get_job_info(job_id: int, json_output: bool):
    """Get job and its runs information."""
    try:
        # Get database session
        session = get_database_session()

        def session_factory():
            return session

        # Create repositories with mappers
        job_mapper = JobMapper()
        run_mapper = RunMapper()
        job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
        run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)

        # Get job
        job = get_job(job_repository, job_id)
        if not job:
            click.echo(f"Error: Job {job_id} not found", err=True)
            sys.exit(1)

        # Convert job to dict
        job_data = {
            "id": job.id,
            "userId": job.user_id,
            "tags": job.tags,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
        }

        # Get runs - returns a list directly, not a Result
        try:
            runs = get_runs_by_job_id(run_repository, job_id)
            # Convert Run objects to dicts
            runs_data = []
            for run in runs:
                run_dict = {
                    "id": run.id,
                    "jobId": run.job_id,
                    "userId": run.user_id,
                    "createdTs": run.created_at.isoformat() if run.created_at else None,
                    "request": run.request,
                    "podPhase": run.pod_phase,
                    "containerStatus": run.container_status,
                    "status": run.status,
                    "userDeleted": run.user_deleted,
                    "epxClientVersion": run.epx_client_version,
                }
                runs_data.append(run_dict)
        except Exception as e:
            runs_data = []
            click.echo(f"Warning: Could not retrieve runs: {e}", err=True)

        # Output results
        if json_output:
            output = {"job": job_data, "runs": runs_data}
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(format_job_output(job_data, runs_data))

        session.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.group("uploads")
def job_uploads():
    """Commands for managing job uploads."""
    pass


@job_uploads.command("list")
@click.option("--job-id", required=True, type=int, help="Job ID to get uploads for")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def list_job_uploads(job_id: int, json_output: bool):
    """List sanitized S3 URLs for all uploads of a job and its runs."""
    try:
        # Get configuration from environment/config file
        config = get_default_config()
        env = config["env"]
        bucket_name = config["bucket"] or "epistemix-uploads-dev"
        region_name = config["region"]

        # Get database session
        session = get_database_session()

        def session_factory():
            return session

        # Create repositories with mappers
        job_mapper = JobMapper()
        run_mapper = RunMapper()
        job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
        run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)

        # Create upload location repository
        upload_location_repository = create_upload_location_repository(
            env=env, bucket_name=bucket_name, region_name=region_name
        )

        # Create JobController
        job_controller = JobController.create_with_repositories(
            job_repository=job_repository,
            run_repository=run_repository,
            upload_location_repository=upload_location_repository,
        )

        # Get uploads WITHOUT content (just metadata and sanitized URLs)
        result = job_controller.get_job_uploads(job_id=job_id, include_content=False)

        if not is_successful(result):
            click.echo(f"Error: {result.failure()}", err=True)
            sys.exit(1)

        uploads_data = result.unwrap()

        # Output results
        if json_output:
            output = {
                "jobId": job_id,
                "env": env,
                "bucket": bucket_name if env != "TESTING" else "N/A (TESTING mode)",
                "uploads": uploads_data,
                "count": len(uploads_data),
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Print sanitized URLs to terminal
            for upload in uploads_data:
                # Get sanitized URL from location object
                location = upload.get("location", {})
                sanitized_url = location.get("url", "")
                if sanitized_url:
                    # Include context info in the output
                    context = upload.get("context", "")
                    upload_type = upload.get("uploadType", "")
                    run_id = upload.get("runId", "")

                    if context == "job":
                        prefix = f"[job_{job_id}_{upload_type}]"
                    elif run_id:
                        prefix = f"[run_{run_id}_{upload_type}]"
                    else:
                        prefix = f"[{context}_{upload_type}]"

                    click.echo(f"{prefix} {sanitized_url}")

        session.close()

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@job_uploads.command("archive")
@click.option("--job-id", required=True, type=int, help="Job ID to archive uploads for")
@click.option("--days-since-create", type=int, help="Archive uploads older than specified days")
@click.option("--hours-since-create", type=int, help="Archive uploads older than specified hours")
@click.option("--dry-run", is_flag=True, help="Show what would be archived without making changes")
def archive_uploads(
    job_id: int, days_since_create: Optional[int], hours_since_create: Optional[int], dry_run: bool
):
    """Archive uploads for a job to reduce storage costs."""
    try:
        # Get configuration
        config = get_default_config()
        env = config["env"]
        bucket_name = config["bucket"] or "epistemix-uploads-dev"
        region_name = config["region"]

        if env == "TESTING":
            click.echo("Error: Cannot archive uploads in TESTING mode", err=True)
            sys.exit(1)

        # Get database session
        session = get_database_session()

        def session_factory():
            return session

        # Create repositories with mappers
        job_mapper = JobMapper()
        run_mapper = RunMapper()
        job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
        run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)

        # Create upload location repository
        upload_location_repository = create_upload_location_repository(
            env=env, bucket_name=bucket_name, region_name=region_name
        )

        # Create JobController
        job_controller = JobController.create_with_repositories(
            job_repository=job_repository,
            run_repository=run_repository,
            upload_location_repository=upload_location_repository,
        )

        # Archive uploads using the controller
        result = job_controller.archive_job_uploads(
            job_id=job_id,
            days_since_create=days_since_create,
            hours_since_create=hours_since_create,
            dry_run=dry_run,
        )

        if not is_successful(result):
            click.echo(f"Error: {result.failure()}", err=True)
            sys.exit(1)

        archived_locations = result.unwrap()

        if not archived_locations:
            click.echo(f"No uploads found for job {job_id} matching criteria")
        else:
            action = "Would archive" if dry_run else "Archived"
            click.echo(f"\n{action} {len(archived_locations)} uploads for job {job_id}:")
            for location in archived_locations:
                click.echo(f"  - {location.get('url', 'N/A')}")

        session.close()

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@job_uploads.command("download")
@click.option("--job-id", required=True, type=int, help="Job ID to download uploads for")
@click.option("--output-dir", help="Directory to download files to (defaults to temp directory)")
@click.option("-f", "--force", is_flag=True, help="Force overwrite existing files")
def download_job_uploads(job_id: int, output_dir: Optional[str], force: bool):
    """Download all uploads for a job to a local directory."""
    try:
        # Get configuration from environment/config file
        config = get_default_config()
        env = config["env"]
        bucket_name = config["bucket"] or "epistemix-uploads-dev"
        region_name = config["region"]

        # Get database session
        session = get_database_session()

        def session_factory():
            return session

        # Create repositories with mappers
        job_mapper = JobMapper()
        run_mapper = RunMapper()
        job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
        run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)

        # Create upload location repository
        upload_location_repository = create_upload_location_repository(
            env=env, bucket_name=bucket_name, region_name=region_name
        )

        # Create JobController
        job_controller = JobController.create_with_repositories(
            job_repository=job_repository,
            run_repository=run_repository,
            upload_location_repository=upload_location_repository,
        )

        # Determine download path
        if output_dir:
            base_path = Path(output_dir)
        else:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix=f"job_{job_id}_")
            base_path = Path(temp_dir)

        click.echo(f"Downloading uploads for job {job_id} to {base_path}")
        if not force:
            click.echo("(Use -f/--force to overwrite existing files)")

        # Download uploads using the controller
        result = job_controller.download_job_uploads(
            job_id=job_id, base_path=base_path, should_force=force
        )

        if not is_successful(result):
            click.echo(f"Error: {result.failure()}", err=True)
            sys.exit(1)

        download_path = result.unwrap()

        # List downloaded files
        downloaded_files = list(Path(download_path).iterdir())
        click.echo(f"\nSuccessfully downloaded {len(downloaded_files)} files to:")
        click.echo(f"  {download_path}")

        if downloaded_files:
            click.echo("\nDownloaded files:")
            for file_path in downloaded_files:
                file_size = file_path.stat().st_size
                click.echo(f"  - {file_path.name} ({file_size} bytes)")

        session.close()

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("version")
def version():
    """Show CLI version."""
    click.echo("Epistemix CLI v1.0.0")


if __name__ == "__main__":
    cli()
