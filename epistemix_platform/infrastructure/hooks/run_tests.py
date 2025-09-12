#!/usr/bin/env python3
"""
Sceptre hook to run infrastructure tests.

This hook can be configured to run tests before or after stack operations.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from sceptre.hooks import Hook
from sceptre.exceptions import HookFailed


class RunTests(Hook):
    """
    Hook to run infrastructure tests using pytest.
    
    This hook can be configured to run specific test files or all tests
    in the infrastructure test directory.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the hook."""
        super().__init__(*args, **kwargs)
    
    def run(self) -> None:
        """
        Execute infrastructure tests.
        
        The hook accepts an optional 'test_files' argument to specify
        which test files to run. If not provided, runs all tests.
        
        Example configuration in stack config:
            hooks:
                after_create:
                    - !run_tests
                        test_files:
                            - test_ecr_deployment.py
                            - test_s3_deployment.py
        
        Raises:
            HookFailed: If any tests fail.
        """
        # Get test files from hook arguments
        test_files = self.argument.get('test_files', []) if self.argument else []
        
        # Build pytest command
        test_dir = Path(self.stack.project_path) / "tests"
        
        if not test_dir.exists():
            self.logger.warning(f"Test directory not found: {test_dir}")
            return
        
        # Construct pytest command
        cmd = ["poetry", "run", "pytest"]
        
        if test_files:
            # Run specific test files
            for test_file in test_files:
                test_path = test_dir / test_file
                if test_path.exists():
                    cmd.append(str(test_path))
                else:
                    self.logger.warning(f"Test file not found: {test_path}")
        else:
            # Run all tests in the test directory
            cmd.append(str(test_dir))
        
        # Add pytest options
        cmd.extend(["-v", "--tb=short"])
        
        # Run tests
        self.logger.info(f"Running tests: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=Path(self.stack.project_path).parent.parent  # Go up to project root for Poetry
            )
            
            # Log output
            if result.stdout:
                self.logger.info(f"Test output:\n{result.stdout}")
            
            if result.returncode != 0:
                if result.stderr:
                    self.logger.error(f"Test errors:\n{result.stderr}")
                raise HookFailed(f"Tests failed with return code {result.returncode}")
            
            self.logger.info("All tests passed successfully")
            
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            raise HookFailed(f"Failed to run tests: {str(e)}")