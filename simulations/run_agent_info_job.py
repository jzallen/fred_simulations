#!/usr/bin/env python3
"""
Script to run the agent_info_job against the Epistemix API.
This validates that the dockerized API is working properly.
"""

import os
import sys
from pathlib import Path

def main():
    """Main function to execute the agent info job."""
    # Ensure relative FRED assets resolve regardless of invocation location
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    from agent_info_demo.agent_info_job import info_job

    print("Starting agent_info_job execution...")
    print(f"API URL: {os.environ.get('EPISTEMIX_API_URL', 'Using ~/.epx/config')}")
    print(f"Job tags: {info_job.tags}")
    print(f"FRED files: {info_job.fred_files}")

    try:
        # Execute the job with a timeout of 300 seconds
        info_job.execute(300)
        print(f"Job completed successfully! Status: {info_job.status}")
        return 0
    except Exception as e:
        print(f"Job execution failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())