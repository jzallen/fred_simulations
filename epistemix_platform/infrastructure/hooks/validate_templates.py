"""
Sceptre hook to validate CloudFormation templates using cfn-lint.

This hook runs before stack creation/update to ensure templates are valid.
"""

import subprocess
from pathlib import Path

from sceptre.hooks import Hook
from sceptre.exceptions import SceptreException


class ValidateTemplate(Hook):
    """
    Hook to validate CloudFormation templates using cfn-lint.
    
    This hook runs cfn-lint on the template before deployment to catch
    syntax errors and AWS CloudFormation best practice violations.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the hook."""
        super().__init__(*args, **kwargs)
    
    def run(self) -> None:
        """
        Execute template validation.
        
        Raises:
            HookFailed: If template validation fails.
        """
        # Get the template path from the stack config
        template_config = self.stack.template
        
        if isinstance(template_config, dict):
            template_path = template_config.get('path')
        else:
            # Legacy format support
            template_path = template_config
        
        if not template_path:
            raise SceptreException(f"No template path found for stack {self.stack.name}")
        
        # Construct full template path
        template_dir = Path(self.stack.project_path) / "templates"
        full_template_path = template_dir / template_path
        
        if not full_template_path.exists():
            raise SceptreException(f"Template file not found: {full_template_path}")
        
        # Run cfn-lint validation
        self.logger.info(f"Validating template: {full_template_path}")
        
        try:
            result = subprocess.run(
                ["poetry", "run", "cfn-lint", str(full_template_path)],
                capture_output=True,
                text=True,
                check=True,  # Automatically raise CalledProcessError on non-zero exit
                timeout=300,  # 5-minute timeout for validation
                cwd=Path(self.stack.project_path).parent.parent  # Go up to project root for Poetry
            )

            # Log output (cfn-lint may provide useful info even on success)
            if result.stdout:
                self.logger.info(f"cfn-lint output:\n{result.stdout}")

            # Log stderr if present (even on success, for warnings)
            if result.stderr:
                self.logger.warning(f"cfn-lint warnings/stderr:\n{result.stderr}")

            self.logger.info(f"Template validation successful: {template_path}")

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Template validation timed out after {e.timeout} seconds")
            if e.stdout:
                self.logger.error(f"Partial stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Partial stderr:\n{e.stderr}")
            raise SceptreException(f"cfn-lint validation timed out for {template_path}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Template validation failed with return code {e.returncode}")
            if e.stdout:
                self.logger.error(f"cfn-lint stdout:\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"cfn-lint stderr:\n{e.stderr}")
            raise SceptreException(f"cfn-lint validation failed for {template_path}")

        except Exception as e:
            self.logger.error(f"Unexpected error running cfn-lint: {str(e)}")
            raise SceptreException(f"Failed to run cfn-lint: {str(e)}")