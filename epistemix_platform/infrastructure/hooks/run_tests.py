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
from sceptre.exceptions import SceptreException


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

        Security: This hook validates that all test file paths remain within
        the designated test directory to prevent path traversal attacks.

        Example configuration in stack config:
            hooks:
                after_create:
                    - !run_tests
                        test_files:
                            - test_ecr_deployment.py
                            - test_s3_deployment.py

        Raises:
            SceptreException: If any tests fail or if path traversal is attempted.
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
                # Resolve the path to prevent path traversal attacks
                test_path = (test_dir / test_file).resolve()

                # Validate that the resolved path is within the test directory
                try:
                    # Check if the path is within test_dir (Python 3.9+)
                    test_path.relative_to(test_dir.resolve())
                except ValueError:
                    # Path is outside test directory - potential security issue
                    self.logger.error(f"Invalid test file path (outside test directory): {test_file}")
                    raise SceptreException(f"Test file path traversal attempt detected: {test_file}")

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
                check=True,  # Automatically raise CalledProcessError on non-zero exit
                timeout=300,  # 5-minute timeout for test execution
                cwd=Path(self.stack.project_path).parent.parent  # Go up to project root for Poetry
            )

            # Log output
            if result.stdout:
                self.logger.info(f"Test output:\n{result.stdout}")

            # Log stderr if present (even on success, for warnings)
            if result.stderr:
                self.logger.warning(f"Test warnings/stderr:\n{result.stderr}")

            self.logger.info("All tests passed successfully")

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Tests timed out after {e.timeout} seconds")
            if e.stdout:
                self.logger.error(f"Partial stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Partial stderr:\n{e.stderr}")
            raise SceptreException(f"Tests timed out after {e.timeout} seconds")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Tests failed with return code {e.returncode}")
            if e.stdout:
                self.logger.error(f"Test stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Test stderr:\n{e.stderr}")
            raise SceptreException(f"Tests failed with return code {e.returncode}")

        except Exception as e:
            self.logger.error(f"Unexpected error running tests: {str(e)}")
            raise SceptreException(f"Failed to run tests: {str(e)}")