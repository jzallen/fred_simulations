#!/usr/bin/env python3
"""
Epistemix CLI for interacting with jobs and uploads.

Usage:
    epistemix jobs --job-id=<job-id>  # Get job and runs info
    epistemix jobs upload --location=<upload-location>  # Read upload contents
"""

import os
import sys
import json
import logging
from typing import Optional

import click
from returns.pipeline import is_successful
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from epistemix_api.repositories.job_repository import SQLAlchemyJobRepository
from epistemix_api.repositories.run_repository import SQLAlchemyRunRepository
from epistemix_api.repositories.database import get_database_manager
from epistemix_api.use_cases.get_job import get_job
from epistemix_api.use_cases.get_runs import get_runs_by_job_id
from epistemix_api.use_cases.list_jobs import list_jobs
from epistemix_api.use_cases.get_job_uploads import get_job_uploads, JobUpload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_session():
    """Get a database session."""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///epistemix_jobs.db')
    db_manager = get_database_manager(database_url)
    db_manager.create_tables()
    return db_manager.get_session()


def format_job_uploads(uploads: list) -> str:
    """Format job uploads for display."""
    if not uploads:
        return "No uploads found for this job."
    
    output = []
    output.append("=" * 80)
    
    # Group uploads by type
    job_uploads = [u for u in uploads if u['runId'] is None]
    run_uploads = [u for u in uploads if u['runId'] is not None]
    
    # Display job uploads
    if job_uploads:
        output.append(f"Job {uploads[0]['jobId']} Uploads:")
        output.append("-" * 80)
        
        for upload in job_uploads:
            output.append(f"\n[{upload['uploadType'].upper()}]")
            if upload.get('content'):
                # Truncate very long content
                content = upload['content']
                if len(content) > 1000:
                    content = content[:997] + "..."
                output.append(content)
            elif upload.get('error'):
                output.append(f"Error: {upload['error']}")
            else:
                output.append("(No content available)")
            output.append("-" * 40)
    
    # Display run uploads
    if run_uploads:
        output.append(f"\nRun Uploads:")
        output.append("-" * 80)
        
        # Group by run ID
        runs_by_id = {}
        for upload in run_uploads:
            run_id = upload['runId']
            if run_id not in runs_by_id:
                runs_by_id[run_id] = []
            runs_by_id[run_id].append(upload)
        
        for run_id, run_uploads_list in runs_by_id.items():
            output.append(f"\nRun ID: {run_id}")
            for upload in run_uploads_list:
                output.append(f"  [{upload['uploadType'].upper()}]")
                if upload.get('content'):
                    # Indent content for run uploads
                    content = upload['content']
                    if len(content) > 800:
                        content = content[:797] + "..."
                    content_lines = content.split('\n')
                    for line in content_lines[:20]:  # Limit lines shown
                        output.append(f"    {line}")
                    if len(content_lines) > 20:
                        output.append(f"    ... ({len(content_lines) - 20} more lines)")
                elif upload.get('error'):
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
        tags_str = ', '.join(job.get('tags', []))[:28]  # Truncate long tags
        if len(tags_str) == 28:
            tags_str += '..'
        
        created_str = job.get('createdAt', 'N/A')
        if created_str != 'N/A':
            # Simplify timestamp display
            created_str = created_str.replace('T', ' ').split('.')[0]
        
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
            request = run.get('request', {})
            if request:
                output.append(f"  Working Dir: {request.get('workingDir', 'N/A')}")
                output.append(f"  Size: {request.get('size', 'N/A')}")
                output.append(f"  FRED Version: {request.get('fredVersion', 'N/A')}")
                
                # Show population info
                population = request.get('population', {})
                if population:
                    output.append(f"  Population Version: {population.get('version', 'N/A')}")
                    locations = population.get('locations', [])
                    if locations:
                        output.append(f"  Locations: {', '.join(locations)}")
                
                # Show FRED args
                fred_args = request.get('fredArgs', [])
                if fred_args:
                    args_str = ' '.join([f"{arg.get('flag', '')} {arg.get('value', '')}" for arg in fred_args])
                    output.append(f"  FRED Args: {args_str}")
                
                # Show FRED files
                fred_files = request.get('fredFiles', [])
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


@jobs.command('list')
@click.option('--limit', type=int, help='Maximum number of jobs to display')
@click.option('--offset', type=int, default=0, help='Number of jobs to skip (for pagination)')
@click.option('--user-id', type=int, help='Filter jobs by user ID')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def list_all_jobs(limit: Optional[int], offset: int, user_id: Optional[int], json_output: bool):
    """List all jobs in the database."""
    try:
        # Get database session
        session = get_database_session()
        session_factory = lambda: session
        
        # Create repository
        job_repository = SQLAlchemyJobRepository(session_factory)
        
        # Get jobs using the use case
        jobs = list_jobs(
            job_repository=job_repository,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        
        # Convert jobs to dicts
        jobs_data = []
        for job in jobs:
            job_dict = {
                'id': job.id,
                'userId': job.user_id,
                'tags': job.tags,
                'status': job.status.value if hasattr(job.status, 'value') else str(job.status),
                'createdAt': job.created_at.isoformat() if job.created_at else None
            }
            jobs_data.append(job_dict)
        
        # Output results
        if json_output:
            output = {
                'jobs': jobs_data,
                'count': len(jobs_data),
                'offset': offset
            }
            if limit:
                output['limit'] = limit
            if user_id:
                output['userId'] = user_id
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


@jobs.command('info')
@click.option('--job-id', required=True, type=int, help='Job ID to retrieve')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def get_job_info(job_id: int, json_output: bool):
    """Get job and its runs information."""
    try:
        # Get database session
        session = get_database_session()
        session_factory = lambda: session
        
        # Create repositories
        job_repository = SQLAlchemyJobRepository(session_factory)
        run_repository = SQLAlchemyRunRepository(session_factory)
        
        # Get job
        job = get_job(job_repository, job_id)
        if not job:
            click.echo(f"Error: Job {job_id} not found", err=True)
            sys.exit(1)
        
        # Convert job to dict
        job_data = {
            'id': job.id,
            'userId': job.user_id,
            'tags': job.tags,
            'createdAt': job.created_at.isoformat() if job.created_at else None
        }
        
        # Get runs - returns a list directly, not a Result
        try:
            runs = get_runs_by_job_id(run_repository, job_id)
            # Convert Run objects to dicts
            runs_data = []
            for run in runs:
                run_dict = {
                    'id': run.id,
                    'jobId': run.job_id,
                    'userId': run.user_id,
                    'createdTs': run.created_at.isoformat() if run.created_at else None,
                    'request': run.request,
                    'podPhase': run.pod_phase,
                    'containerStatus': run.container_status,
                    'status': run.status,
                    'userDeleted': run.user_deleted,
                    'epxClientVersion': run.epx_client_version
                }
                runs_data.append(run_dict)
        except Exception as e:
            runs_data = []
            click.echo(f"Warning: Could not retrieve runs: {e}", err=True)
        
        # Output results
        if json_output:
            output = {
                'job': job_data,
                'runs': runs_data
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(format_job_output(job_data, runs_data))
        
        session.close()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.group('uploads')
def job_uploads():
    """Commands for managing job uploads."""
    pass


@job_uploads.command('list')
@click.option('--job-id', required=True, type=int, help='Job ID to get uploads for')
@click.option('--bucket', help='S3 bucket name (defaults to epistemix-uploads-dev)')
@click.option('--region', help='AWS region (defaults to AWS config)')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def list_job_uploads(job_id: int, bucket: Optional[str], region: Optional[str], json_output: bool):
    """List and display all upload contents for a job and its runs."""
    try:
        # Use default bucket if not provided
        bucket_name = bucket or os.getenv('S3_UPLOAD_BUCKET', 'epistemix-uploads-dev')
        
        # Get database session
        session = get_database_session()
        session_factory = lambda: session
        
        # Create repositories
        job_repository = SQLAlchemyJobRepository(session_factory)
        run_repository = SQLAlchemyRunRepository(session_factory)
        
        # Get uploads using the use case
        uploads = get_job_uploads(
            job_repository=job_repository,
            run_repository=run_repository,
            job_id=job_id,
            bucket_name=bucket_name,
            region_name=region
        )
        
        # Convert uploads to dicts
        uploads_data = []
        for upload in uploads:
            upload_dict = {
                'uploadType': upload.upload_type,
                'jobId': upload.job_id,
                'runId': upload.run_id,
                's3Key': upload.s3_key,
                'content': upload.content,
                'error': upload.error
            }
            uploads_data.append(upload_dict)
        
        # Output results
        if json_output:
            # For JSON, we might want to limit content size
            for upload in uploads_data:
                if upload.get('content') and len(upload['content']) > 5000:
                    upload['content'] = upload['content'][:4997] + '...'
            
            output = {
                'jobId': job_id,
                'bucket': bucket_name,
                'uploads': uploads_data,
                'count': len(uploads_data)
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\nUploads for Job ID: {job_id}")
            click.echo(f"Bucket: {bucket_name}")
            click.echo(format_job_uploads(uploads_data))
        
        session.close()
        
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('version')
def version():
    """Show CLI version."""
    click.echo("Epistemix CLI v1.0.0")


if __name__ == '__main__':
    cli()