#!/usr/bin/env python3
"""
Sceptre hook to validate CloudFormation templates using cfn-lint.

This hook runs before stack creation/update to ensure templates are valid.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from sceptre.hooks import Hook
from sceptre.exceptions import HookFailed


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
            raise HookFailed(f"No template path found for stack {self.stack.name}")
        
        # Construct full template path
        template_dir = Path(self.stack.project_path) / "templates"
        full_template_path = template_dir / template_path
        
        if not full_template_path.exists():
            raise HookFailed(f"Template file not found: {full_template_path}")
        
        # Run cfn-lint validation
        self.logger.info(f"Validating template: {full_template_path}")
        
        try:
            result = subprocess.run(
                ["poetry", "run", "cfn-lint", str(full_template_path)],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path(self.stack.project_path).parent.parent  # Go up to project root for Poetry
            )
            
            if result.returncode != 0:
                self.logger.error(f"Template validation failed:\n{result.stdout}\n{result.stderr}")
                raise HookFailed(f"cfn-lint validation failed for {template_path}")
            
            self.logger.info(f"Template validation successful: {template_path}")
            
        except Exception as e:
            self.logger.error(f"Error running cfn-lint: {str(e)}")
            raise HookFailed(f"Failed to run cfn-lint: {str(e)}")