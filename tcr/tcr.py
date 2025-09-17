#!/usr/bin/env python3
"""TCR (Test && Commit || Revert) implementation for AI-constrained development."""

import argparse
import logging
import logging.handlers
import re
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import setproctitle
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def _get_or_generate_session_id(session_id: Optional[str]) -> str:
    """Get session_id or generate a random one if not provided.

    Args:
        session_id: Optional session identifier.

    Returns:
        Valid filesystem-safe session_id.
    """
    if not session_id or session_id == "":
        return secrets.token_urlsafe(8)
    else:
        # Sanitize session_id to be filesystem-safe (alphanumeric, underscores, and hyphens only)
        return re.sub(r'[^a-zA-Z0-9_-]', '_', session_id)


def setup_logger(log_file: Optional[Path] = None, session_id: Optional[str] = None) -> logging.Logger:
    """Set up logger to write to both console and file.

    Args:
        log_file: Path to log file. If provided, session_id is ignored.
        session_id: Optional session identifier for namespacing logs.
                   If not provided, generates a random alphanumeric string.

    Returns:
        Configured logger instance
    """
    if log_file is None:
        session_id = _get_or_generate_session_id(session_id)

        # Use XDG Base Directory specification with session_id
        log_dir = Path.home() / '.local' / 'share' / 'tcr' / session_id
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
    watch_paths: List[str] = field(default_factory=lambda: ['.'])
    test_command: str = 'poetry run pytest -xvs'
    test_timeout: int = 30
    commit_prefix: str = 'TCR'
    revert_on_failure: bool = True
    debounce_seconds: float = 2.0
    log_file: Optional[str] = None

    def __post_init__(self):
        """Ensure watch_paths is never empty."""
        if not self.watch_paths:
            self.watch_paths = ['.']
    
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

                # Ensure watch_paths defaults to current directory if not specified or empty
                if 'watch_paths' not in config_dict or not config_dict.get('watch_paths'):
                    config_dict['watch_paths'] = ['.']

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
            
        current_time = time.time()
        if current_time - self.last_run < self.config.debounce_seconds:
            return
            
        # Check if there are any changes using git status (respects .gitignore)
        # Filter by watch_paths (always has at least one path)
        git_cmd = ['git', 'status', '--porcelain', '--'] + self.config.watch_paths

        result = subprocess.run(
            git_cmd,
            capture_output=True,
            text=True
        )
        
        # If no changes detected (all ignored by .gitignore), skip TCR cycle
        if not result.stdout.strip():
            return
            
        self.last_run = current_time
        path = Path(event.src_path)
        self._run_tcr_cycle(path)
        
    def _run_tcr_cycle(self, changed_file: Path):
        """Run the TCR cycle: test && commit || revert."""
        logger.info(f"\n🔄 TCR: Change detected in {changed_file}")
        logger.debug(f"Starting TCR cycle for file: {changed_file}")
        
        test_result = self._run_tests()
        
        if test_result:
            self._commit_changes(changed_file)
        else:
            self._revert_changes()
            
    def _run_tests(self) -> bool:
        """Run tests and return success status."""
        logger.info("🧪 Running tests...")
        logger.debug(f"Executing command: {self.config.test_command}")
        
        try:
            result = subprocess.run(
                self.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Tests passed!")
                logger.debug(f"Test output:\n{result.stdout}")
                return True
            else:
                logger.error(f"❌ Tests failed!")
                logger.error(f"stdout:\n{result.stdout}")
                logger.error(f"stderr:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Tests timed out after {self.config.test_timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"🚨 Error running tests: {e}")
            logger.debug(f"Exception details:", exc_info=True)
            return False
            
    def _commit_changes(self, changed_file: Path):
        """Commit changes to git."""
        try:
            # Stage only files in watch_paths
            git_add_cmd = ['git', 'add', '--'] + self.config.watch_paths
            logger.debug(f"Staging changes in watch_paths with: {' '.join(git_add_cmd)}")
            subprocess.run(git_add_cmd, check=True, capture_output=True)
            
            # Create commit message
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            message = f"{self.config.commit_prefix}: {timestamp} - Modified {changed_file.name}"
            
            # Commit
            logger.debug(f"Committing with message: {message}")
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
            git_checkout_cmd = ['git', 'checkout', 'HEAD', '--'] + self.config.watch_paths
            logger.debug(f"Reverting changes in watch_paths with: {' '.join(git_checkout_cmd)}")
            subprocess.run(git_checkout_cmd, check=True, capture_output=True)
            logger.info("🔙 Reverted changes")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Could not revert: {e}")
            logger.debug(f"Revert error details:", exc_info=True)


class TCRRunner:
    """Main TCR runner that manages the file watching."""

    def __init__(self, config_path: Optional[Path] = None, session_id: Optional[str] = None):
        self.config = TCRConfig.from_yaml(config_path)
        self.session_id = session_id

        # Re-initialize logger with config-specified log file or session_id
        global logger
        if self.config.log_file:
            # If log_file is explicitly specified in config, use it (ignores session_id)
            logger = setup_logger(log_file=Path(self.config.log_file))
            # Even with log_file, set process name if session_id provided
            if session_id:
                setproctitle.setproctitle(f'tcr:{session_id}')
        else:
            # Otherwise use session_id (or generate random if None)
            # If no session_id provided, generate one for both logger and process name
            effective_session_id = _get_or_generate_session_id(session_id)
            logger = setup_logger(session_id=effective_session_id)
            # Always set process name with the effective session_id
            setproctitle.setproctitle(f'tcr:{effective_session_id}')

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
        git_cmd = ['git', 'status', '--porcelain', '--'] + self.config.watch_paths

        result = subprocess.run(git_cmd, capture_output=True, text=True)
        if result.stdout.strip():
            logger.warning("⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first.")
            logger.debug(f"Uncommitted changes:\n{result.stdout}")
            
        # Set up watchers for each path
        for path in self.config.watch_paths:
            if Path(path).exists():
                logger.debug(f"Setting up watcher for path: {path}")
                self.observer.schedule(self.handler, path, recursive=True)
            else:
                logger.warning(f"⚠️ Watch path does not exist: {path}")
                
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
    parser.add_argument('--session-id', type=str, default=None,
                        help='Session identifier for namespacing logs (generates random if not provided)')

    args = parser.parse_args()

    if args.command == 'start':
        # Pass both config_path and session_id to TCRRunner
        runner = TCRRunner(config_path=args.config, session_id=args.session_id)
        runner.start()
    elif args.command == 'stop':
        # Stop is handled by KeyboardInterrupt in start()
        logger.info("Use Ctrl+C to stop TCR mode")
        

if __name__ == '__main__':
    main()