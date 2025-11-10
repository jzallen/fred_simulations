#!/usr/bin/env python3
"""TCR (Test && Commit || Revert) implementation for AI-constrained development."""

import argparse
import logging
import re
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import setproctitle
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from tcr.logging_config import LoggerType, logger_factory


def get_or_generate_session_id(session_id: str | None) -> str:
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
        return re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)


def get_log_file_path(session_id: str) -> Path:
    """Generate log file path based on session ID.

    Args:
        session_id: Session identifier for namespacing logs.

    Returns:
        Path to log file.
    """
    # Use XDG Base Directory specification with session_id
    log_dir = Path.home() / ".local" / "share" / "tcr" / session_id
    return log_dir / "tcr.log"


@dataclass
class TCRConfig:
    """Configuration for TCR behavior."""

    enabled: bool = True
    watch_paths: list[str] = field(default_factory=lambda: ["."])
    test_command: str = "poetry run pytest -xvs"
    test_timeout: int = 30
    commit_prefix: str = "TCR"
    revert_on_failure: bool = True
    debounce_seconds: float = 2.0
    log_file: str | None = None

    def __post_init__(self):
        """Ensure watch_paths is never empty."""
        if not self.watch_paths:
            self.watch_paths = ["."]

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> "TCRConfig":
        """Load configuration from YAML file or use defaults.

        Args:
            config_path: Path to YAML config file. Defaults to ~/tcr.yaml

        Returns:
            TCRConfig instance with loaded or default values
        """
        if config_path is None:
            config_path = Path.home() / "tcr.yaml"

        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                if data and "tcr" in data:
                    config_dict = data["tcr"]
                elif data:
                    config_dict = data
                else:
                    config_dict = {}

                # Ensure watch_paths defaults to current directory if not specified or empty
                if "watch_paths" not in config_dict or not config_dict.get("watch_paths"):
                    config_dict["watch_paths"] = ["."]

                return cls(**config_dict)

        return cls()


class TCRHandler(FileSystemEventHandler):
    """Handle file system events and trigger TCR workflow."""

    def __init__(self, config: TCRConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
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
        git_cmd = ["git", "status", "--porcelain", "--"] + self.config.watch_paths

        result = subprocess.run(git_cmd, capture_output=True, text=True)

        # If no changes detected (all ignored by .gitignore), skip TCR cycle
        if not result.stdout.strip():
            return

        self.last_run = current_time
        path = Path(event.src_path)
        self._run_tcr_cycle(path)

    def _run_tcr_cycle(self, changed_file: Path):
        """Run the TCR cycle: test && commit || revert."""
        self.logger.info(f"\n🔄 TCR: Change detected in {changed_file}")
        self.logger.debug(f"Starting TCR cycle for file: {changed_file}")

        test_result = self._run_tests()

        if test_result:
            self._commit_changes(changed_file)
        else:
            self._revert_changes()

    def _run_tests(self) -> bool:
        """Run tests and return success status."""
        self.logger.info("🧪 Running tests...")
        self.logger.debug(f"Executing command: {self.config.test_command}")

        try:
            result = subprocess.run(
                self.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout,
            )

            if result.returncode == 0:
                self.logger.info("✅ Tests passed!")
                self.logger.debug(f"Test output:\n{result.stdout}")
                return True
            else:
                self.logger.error("❌ Tests failed!")
                self.logger.error(f"stdout:\n{result.stdout}")
                self.logger.error(f"stderr:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.exception(f"⏱️ Tests timed out after {self.config.test_timeout} seconds")
            return False
        except Exception:
            self.logger.exception("🚨 Error running tests")
            return False

    def _commit_changes(self, changed_file: Path):
        """Commit changes to git."""
        try:
            # Stage only files in watch_paths
            git_add_cmd = ["git", "add", "--"] + self.config.watch_paths
            self.logger.debug(f"Staging changes in watch_paths with: {' '.join(git_add_cmd)}")
            subprocess.run(git_add_cmd, check=True, capture_output=True)

            # Create commit message
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            message = f"{self.config.commit_prefix}: {timestamp} - Modified {changed_file.name}"

            # Commit
            self.logger.debug(f"Committing with message: {message}")
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            self.logger.info(f"✅ Committed: {message}")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"⚠️ Could not commit: {e}")
            self.logger.debug("Commit error details:", exc_info=True)

    def _revert_changes(self):
        """Revert uncommitted changes."""
        if not self.config.revert_on_failure:
            self.logger.warning("⚠️ Tests failed but revert is disabled")
            return

        try:
            git_checkout_cmd = ["git", "checkout", "HEAD", "--"] + self.config.watch_paths
            self.logger.debug(
                f"Reverting changes in watch_paths with: {' '.join(git_checkout_cmd)}"
            )
            subprocess.run(git_checkout_cmd, check=True, capture_output=True)
            self.logger.info("🔙 Reverted changes")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"⚠️ Could not revert: {e}")
            self.logger.debug("Revert error details:", exc_info=True)


class TCRRunner:
    """Main TCR runner that manages the file watching."""

    def __init__(self, config: TCRConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.observer = Observer()
        self.handler = TCRHandler(self.config, self.logger)

    def start(self):
        """Start watching for file changes."""
        if not self.config.enabled:
            self.logger.info("TCR is disabled in configuration")
            return

        self.logger.info("🚀 Starting TCR mode...")
        self.logger.info(f"Watching: {self.config.watch_paths}")
        self.logger.info(f"Test command: {self.config.test_command}")
        self.logger.debug(f"Full configuration: {self.config}")

        # Check for uncommitted changes
        git_cmd = ["git", "status", "--porcelain", "--"] + self.config.watch_paths

        result = subprocess.run(git_cmd, capture_output=True, text=True)
        if result.stdout.strip():
            self.logger.warning(
                "⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first."
            )
            self.logger.debug(f"Uncommitted changes:\n{result.stdout}")

        # Set up watchers for each path
        for path in self.config.watch_paths:
            if Path(path).exists():
                self.logger.debug(f"Setting up watcher for path: {path}")
                self.observer.schedule(self.handler, path, recursive=True)
            else:
                self.logger.warning(f"⚠️ Watch path does not exist: {path}")

        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop watching for file changes."""
        self.logger.info("\n🛑 Stopping TCR mode...")
        self.logger.debug("Stopping file observer")
        self.observer.stop()
        self.observer.join()
        self.logger.info("TCR mode stopped")


def list_sessions(logger: logging.Logger):
    """List all running TCR sessions by checking process names.

    Args:
        logger: Logger instance for output.
    """

    try:
        # Use pgrep to find all processes matching tcr:*
        # Using tcr:* instead of tcr:.* to avoid 15 char limit
        result = subprocess.run(["pgrep", "-a", "tcr:"], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            # Output raw pgrep results
            print(result.stdout.strip())
        else:
            logger.info("No TCR sessions currently running")

    except FileNotFoundError:
        logger.exception("pgrep command not found. Please ensure procps is installed.")
    except Exception:
        logger.exception("Error listing sessions")


def stop_session(session_id: str, logger: logging.Logger):
    """Stop a TCR session by sending SIGINT to the process with matching session_id.

    Args:
        session_id: The session identifier to stop.
        logger: Logger instance for output.
    """

    try:
        # Use pgrep with grep to avoid the 15 character limit
        # pgrep -a "tcr:*" gets all tcr processes, then grep filters for the specific session
        result = subprocess.run(
            f'pgrep -a "tcr:*" | grep "tcr:{session_id}"',
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            pids = []
            for line in lines:
                # Extract PID from pgrep output
                parts = line.split(None, 1)
                if parts:
                    pids.append(parts[0])

            if len(pids) > 1:
                logger.warning(
                    f"Multiple sessions found matching '{session_id}': PIDs {', '.join(pids)}"
                )
                logger.info("Stopping all matching sessions...")

            # Send SIGINT to each matching process
            for pid in pids:
                try:
                    subprocess.run(["kill", "-INT", pid], check=True)
                    logger.info(f"Sent SIGINT to process {pid} (session: {session_id})")
                except subprocess.CalledProcessError:
                    logger.exception(f"Failed to stop process {pid}")
        else:
            logger.error(f"No TCR session found with session_id: {session_id}")

    except FileNotFoundError:
        logger.exception("pgrep or kill command not found. Please ensure procps is installed.")
    except Exception:
        logger.exception("Error stopping session")


def main():
    """Main entry point for TCR command."""
    parser = argparse.ArgumentParser(description="TCR (Test && Commit || Revert) runner")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start TCR mode")
    start_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to configuration file (defaults to ~/tcr.yaml)",
    )
    start_parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Session identifier for namespacing logs (generates random if not provided)",
    )

    # Stop command - requires session-id
    stop_parser = subparsers.add_parser("stop", help="Stop a TCR session")
    stop_parser.add_argument(
        "--session-id",
        type=str,
        required=True,
        help="Session identifier of the TCR session to stop",
    )

    # List command
    subparsers.add_parser("ls", help="List running TCR sessions")

    args = parser.parse_args()

    if args.command == "start":
        # Load config
        config = TCRConfig.from_yaml(args.config)

        # Generate or use session_id
        effective_session_id = get_or_generate_session_id(args.session_id)

        # Set process name for visibility
        setproctitle.setproctitle(f"tcr:{effective_session_id}")

        # Setup logger using factory with ternary for log_file
        log_file = (
            Path(config.log_file) if config.log_file else get_log_file_path(effective_session_id)
        )
        logger = logger_factory(logger_type=LoggerType.DEFAULT, log_file=log_file)

        # Create and start runner with injected dependencies
        runner = TCRRunner(config=config, logger=logger)
        runner.start()
    elif args.command == "stop":
        # Stop the specified session with console logger
        console_logger = logger_factory(logger_type=LoggerType.CONSOLE)
        stop_session(args.session_id, console_logger)
    elif args.command == "ls":
        # List sessions with console logger
        console_logger = logger_factory(logger_type=LoggerType.CONSOLE)
        list_sessions(console_logger)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
