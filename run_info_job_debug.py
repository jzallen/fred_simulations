#!/usr/bin/env python
"""
Debug script to run the info_job with configurable settings.

This script is designed for debugging the agent info job with:
- Configurable mock server settings
- Verbose output for debugging
- Breakpoint-friendly structure
- Option to use real or mock servers

Usage:
    python run_info_job_debug.py [--use-mocks]
"""

import argparse
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for debugging
os.environ["PACT_VERIFIER_LOG_LEVEL"] = "DEBUG"


def setup_environment(use_mocks=False):
    """
    Set up the environment for running the job.

    Args:
        use_mocks: If True, configure for mock servers
    """
    if use_mocks:
        # Configure for mock servers (different ports to avoid conflicts)
        os.environ["EPISTEMIX_API_URL"] = "http://localhost:5002"
        os.environ["S3_ENDPOINT_URL"] = "http://localhost:5003"
        print("Configured for mock servers:")
        print(f"  EPISTEMIX_API_URL: {os.environ.get('EPISTEMIX_API_URL')}")
        print(f"  S3_ENDPOINT_URL: {os.environ.get('S3_ENDPOINT_URL')}")
    else:
        # Use default or real servers
        epistemix_url = os.environ.get("EPISTEMIX_API_URL", "http://localhost:5000")
        s3_url = os.environ.get("S3_ENDPOINT_URL", "https://s3.amazonaws.com")
        print("Using server configuration:")
        print(f"  EPISTEMIX_API_URL: {epistemix_url}")
        print(f"  S3_ENDPOINT_URL: {s3_url}")


def run_job_with_debugging():
    """Run the job with detailed debugging output."""
    from simulations.agent_info_demo.agent_info_job import info_job

    print("\n" + "=" * 60)
    print("DEBUG: Agent Info Job Execution")
    print("=" * 60)

    # Display job configuration
    print("\nJob Configuration:")
    print(f"  Class: {info_job.__class__.__name__}")
    print(f"  Initial Status: {info_job.status}")

    # Display job attributes
    print("\nJob Attributes:")
    for attr in dir(info_job):
        if not attr.startswith("_") and not callable(getattr(info_job, attr)):
            value = getattr(info_job, attr)
            print(f"  {attr}: {value}")

    # Set a breakpoint here if you want to inspect before execution
    # import pdb; pdb.set_trace()

    print("\n" + "-" * 60)
    print("Starting job execution...")
    print("-" * 60 + "\n")

    try:
        # Execute the job
        result = info_job.execute()

        print("\n" + "-" * 60)
        print("Job execution completed")
        print("-" * 60)

        # Display results
        print(f"\nFinal Status: {info_job.status}")

        if hasattr(info_job, "runs"):
            print(f"\nRuns Information:")
            if info_job.runs:
                for i, run in enumerate(info_job.runs, 1):
                    print(f"\n  Run {i}:")
                    for key, value in run.items():
                        print(f"    {key}: {value}")
            else:
                print("  No runs found")

        # Check success
        if str(info_job.status) == "DONE":
            print("\n✓ SUCCESS: Job completed successfully!")
            return 0
        else:
            print(f"\n⚠ WARNING: Job ended with status: {info_job.status}")
            return 1

    except Exception as e:
        print(f"\n✗ ERROR: Job execution failed!")
        print(f"  Exception: {type(e).__name__}")
        print(f"  Message: {e}")

        # Print full traceback for debugging
        import traceback

        print("\nFull Traceback:")
        traceback.print_exc()

        return 2


def main():
    """Main entry point for the debug script."""
    parser = argparse.ArgumentParser(description="Debug script for running the agent info job")
    parser.add_argument(
        "--use-mocks", action="store_true", help="Use mock servers instead of real ones"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # Set up environment
    setup_environment(use_mocks=args.use_mocks)

    # Run the job
    exit_code = run_job_with_debugging()

    print("\n" + "=" * 60)
    print(f"Script completed with exit code: {exit_code}")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
