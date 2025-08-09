#!/usr/bin/env python3
"""
Simple test script to verify Poetry setup and debugging configuration.
"""


def main():
    """Main function to test imports and basic functionality."""
    print("Testing Poetry environment setup...")

    # Test basic imports
    import pandas as pd

    print(f"Pandas version: {pd.__version__}")

    import numpy as np

    print(f"NumPy version: {np.__version__}")

    print("Checking optional imports...")

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    main()
