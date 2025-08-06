#!/usr/bin/env python
"""
Script to run the info_job for debugging purposes.

This script executes the agent info job directly, allowing you to:
- Step through the code with a debugger
- Test the job execution without running the full test suite
- Verify the job completes successfully

Usage:
    python run_info_job.py
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the info_job
from simulations.agent_info_demo.agent_info_job import info_job


def main():
    """Run the info_job and display its status."""
    print("=" * 60)
    print("Running Agent Info Job")
    print("=" * 60)
    
    try:
        # Execute the job
        print("\nExecuting job...")
        info_job.execute()
        
        # Display final status
        print(f"\nFinal job status: {info_job.status}")
        
        # Check if job completed successfully
        if str(info_job.status) == 'DONE':
            print("✓ Job completed successfully!")
        else:
            print(f"⚠ Job ended with status: {info_job.status}")
            
        # Display any additional job information
        if hasattr(info_job, 'runs') and info_job.runs:
            print(f"\nNumber of runs: {len(info_job.runs)}")
            for i, run in enumerate(info_job.runs, 1):
                print(f"  Run {i}: {run.get('status', 'Unknown status')}")
                
    except Exception as e:
        print(f"\n✗ Error executing job: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)