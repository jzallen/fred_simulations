#!/usr/bin/env python3
"""
Simple test script to verify Poetry setup and debugging configuration.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pact
from epx import FREDJob, FREDModelConfig, SynthPop


def main():
    """Main function to test imports and basic functionality."""
    print("Testing Poetry environment setup...")
    
    # Test basic imports
    print(f"Pandas version: {pd.__version__}")
    print(f"NumPy version: {np.__version__}")
    print("pact-python imported successfully")
    print("epx imported successfully")
    
    # Create a simple test similar to agent_info_job.py
    print("\nTesting FRED configuration creation...")
    try:
        info_config = FREDModelConfig(
            synth_pop=SynthPop("US_2010.v5", ["Loving_County_TX"]),
            start_date="2022-05-10",
            end_date="2022-05-10",
        )
        print("✓ FREDModelConfig created successfully")
        
        # Test FREDJob creation (without execution)
        root_dir = Path(__file__).parent
        agent_info_fred_file = root_dir / "simulations" / "agent_info.fred"
        
        if agent_info_fred_file.exists():
            info_job = FREDJob(
                config=[info_config],
                tags=["test_job"],
                fred_files=[agent_info_fred_file]
            )
            print("✓ FREDJob created successfully")
        else:
            print(f"⚠ FRED file not found: {agent_info_fred_file}")
            
    except Exception as e:
        print(f"✗ Error creating FRED objects: {e}")
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    main()
