#!/usr/bin/env python3
"""TCR (Test && Commit || Revert) implementation for AI-constrained development."""

import argparse
import fnmatch
import logging
import logging.handlers
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def setup_logger(log_file: Optional[Path] = None) -> logging.Logger:
    """Set up logger to write to both console and file.
    
    Args:
        log_file: Path to log file. Defaults to ~/.local/share/tcr/tcr.log
        
    Returns:
        Configured logger instance
    """
    if log_file is None:
        # Use XDG Base Directory specification
        log_dir = Path.home() / '.local' / 'share' / 'tcr'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'tcr.log'
    
    logger = logging.getLogger('tcr')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler with DEBUG level and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Initialize logger
logger = setup_logger()

@dataclass
class TCRConfig:
    """Configuration for TCR behavior."""
    
    enabled: bool = True
    watch_paths: List[str] = field(default_factory=list)
    test_command: str = 'poetry run pytest -xvs'
    test_timeout: int = 30
    commit_prefix: str = 'TCR'
    revert_on_failure: bool = True
    debounce_seconds: float = 2.0
    log_file: Optional[str] = None  # Path to log file, defaults to XDG location
    ignore_patterns: List[str] = field(default_factory=lambda: [
        'test_*.py', '**/test_*.py',  # Test files with test_ prefix
        '*_test.py', '**/*_test.py',  # Test files with _test suffix
        'tests/**', '**/tests/**',    # All files in tests directories
    ])
    
    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> 'TCRConfig':
        """Load configuration from YAML file or use defaults.
        
        Args:
            config_path: Path to YAML config file. Defaults to ~/tcr.yaml
            
        Returns:
            TCRConfig instance with loaded or default values
        """
        if config_path is None:
            config_path = Path.home() / 'tcr.yaml'
            
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'tcr' in data:
                    config_dict = data['tcr']
                elif data:
                    config_dict = data
                else:
                    config_dict = {}
                return cls(**config_dict)
        
        return cls()


class TCRHandler(FileSystemEventHandler):
    """Handle file system events and trigger TCR workflow."""
    
    def __init__(self, config: TCRConfig):
        self.config = config
        self.last_run = 0
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        if self._should_ignore_file(path):
            logger.debug(f"Ignoring change to {path} (matches ignore pattern)")
            return
            
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_run < self.config.debounce_seconds:
            return
            
        # Check if there are any non-ignored changes using git status
        result = subprocess.run(
            ['git', 'status', '--porcelain'], 
            capture_output=True, 
            text=True
        )
        
        if not result.stdout.strip():
            logger.debug("No changes detected in git status")
            return
            
        self.last_run = current_time
        self._run_tcr_cycle(path)
        
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on configured patterns.

        Args:
            file_path: Path to check

        Returns:
            True if file should be ignored, False otherwise
        """
        # Normalize to POSIX separators for cross-platform pattern matching
        path_str = file_path.as_posix()

        for pattern in self.config.ignore_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True

        return False
        
    def _run_tcr_cycle(self, changed_file: Path):
        """Run the TCR cycle: test && commit || revert."""
        logger.info(f"\n🔄 TCR: Change detected in {changed_file}")
        logger.debug(f"Starting TCR cycle for file: {changed_file}")
        
        # Run tests
        test_result = self._run_tests()
        
        if test_result:
            self._commit_changes(changed_file)
        else:
            self._revert_changes()
            
    def _run_tests(self) -> bool:
        """Run tests and return success status."""
        logger.info("🧪 Running tests...")
        logger.debug("Executing command: %s", self.config.test_command)

        try:
            cmd = shlex.split(self.config.test_command)
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout,
            )

            if result.returncode == 0:
                logger.info("✅ Tests passed!")
                logger.debug("Test output:\n%s", result.stdout)
                return True
            logger.error("❌ Tests failed!")
            logger.error("stdout:\n%s", result.stdout)
            logger.error("stderr:\n%s", result.stderr)
            return False

        except subprocess.TimeoutExpired:
            logger.error("⏱️ Tests timed out after %s seconds", self.config.test_timeout)
            return False
        except Exception:
            logger.exception("🚨 Error running tests")
            return False
            
    def _commit_changes(self, changed_file: Path):
        """Commit changes to git."""
        try:
            logger.debug("Staging all changes with git add -A")
            # Stage all changes
            subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
            
            # Create commit message
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            message = f"{self.config.commit_prefix}: {timestamp} - Modified {changed_file.name}"
            
            logger.debug(f"Committing with message: {message}")
            # Commit
            subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
            logger.info(f"✅ Committed: {message}")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Could not commit: {e}")
            logger.debug(f"Commit error details:", exc_info=True)
            
    def _revert_changes(self):
        """Revert uncommitted changes."""
        if not self.config.revert_on_failure:
            logger.warning("⚠️ Tests failed but revert is disabled")
            return
            
        try:
            logger.debug("Reverting changes with git reset --hard HEAD")
            # Reset to HEAD
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True, capture_output=True)
            logger.info("🔙 Reverted changes")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Could not revert: {e}")
            logger.debug(f"Revert error details:", exc_info=True)


class TCRRunner:
    """Main TCR runner that manages the file watching."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = TCRConfig.from_yaml(config_path)
        # Re-initialize logger with config-specified log file if provided
        if self.config.log_file:
            global logger
            logger = setup_logger(Path(self.config.log_file))
        self.observer = Observer()
        self.handler = TCRHandler(self.config)
        
    def start(self):
        """Start watching for file changes."""
        if not self.config.enabled:
            logger.info("TCR is disabled in configuration")
            return
            
        logger.info("🚀 Starting TCR mode...")
        logger.info(f"Watching: {self.config.watch_paths}")
        logger.info(f"Test command: {self.config.test_command}")
        logger.debug(f"Full configuration: {self.config}")
        
        # Check for uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            logger.warning("⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first.")
            logger.debug(f"Uncommitted changes:\n{result.stdout}")
            
        # Set up watchers for each path
        for path in self.config.watch_paths:
            if Path(path).exists():
                self.observer.schedule(self.handler, path, recursive=True)
                
        self.observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop watching for file changes."""
        logger.info("\n🛑 Stopping TCR mode...")
        logger.debug("Stopping file observer")
        self.observer.stop()
        self.observer.join()
        logger.info("TCR mode stopped")


def main():
    """Main entry point for TCR command."""
    parser = argparse.ArgumentParser(description='TCR (Test && Commit || Revert) runner')
    parser.add_argument('command', choices=['start', 'stop'], help='Command to execute')
    parser.add_argument('--config', type=Path, default=None,
                        help='Path to configuration file (defaults to ~/tcr.yaml)')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        # If no config specified, TCRRunner will use ~/tcr.yaml by default
        runner = TCRRunner(args.config)
        runner.start()
    elif args.command == 'stop':
        # Stop is handled by KeyboardInterrupt in start()
        logger.info("Use Ctrl+C to stop TCR mode")
        

if __name__ == '__main__':
    main()