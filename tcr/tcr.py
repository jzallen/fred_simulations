#!/usr/bin/env python3
"""TCR (Test && Commit || Revert) implementation for AI-constrained development."""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class TCRConfig:
    """Configuration for TCR behavior."""
    
    enabled: bool = True
    watch_paths: List[str] = field(default_factory=list)
    ignore_paths: List[str] = field(default_factory=lambda: ['*.pyc', '__pycache__', '.git', '*.egg-info', '*.pex'])
    test_command: str = 'poetry run pytest -xvs'
    test_timeout: int = 30
    commit_prefix: str = 'TCR'
    revert_on_failure: bool = True
    debounce_seconds: float = 2.0
    
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
            
        # Check if file should be ignored
        path = Path(event.src_path)
        for pattern in self.config.ignore_paths:
            if path.match(pattern):
                return
                
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_run < self.config.debounce_seconds:
            return
            
        self.last_run = current_time
        self._run_tcr_cycle(path)
        
    def _run_tcr_cycle(self, changed_file: Path):
        """Run the TCR cycle: test && commit || revert."""
        print(f"\n🔄 TCR: Change detected in {changed_file}")
        
        # Run tests
        test_result = self._run_tests()
        
        if test_result:
            self._commit_changes(changed_file)
        else:
            self._revert_changes()
            
    def _run_tests(self) -> bool:
        """Run tests and return success status."""
        print("🧪 Running tests...")
        
        try:
            result = subprocess.run(
                self.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout
            )
            
            if result.returncode == 0:
                print("✅ Tests passed!")
                return True
            else:
                print(f"❌ Tests failed!\n{result.stdout}\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ Tests timed out after {self.config.test_timeout} seconds")
            return False
        except Exception as e:
            print(f"🚨 Error running tests: {e}")
            return False
            
    def _commit_changes(self, changed_file: Path):
        """Commit changes to git."""
        try:
            # Stage all changes
            subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
            
            # Create commit message
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            message = f"{self.config.commit_prefix}: {timestamp} - Modified {changed_file.name}"
            
            # Commit
            subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
            print(f"✅ Committed: {message}")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Could not commit: {e}")
            
    def _revert_changes(self):
        """Revert uncommitted changes."""
        if not self.config.revert_on_failure:
            print("⚠️ Tests failed but revert is disabled")
            return
            
        try:
            # Reset to HEAD
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True, capture_output=True)
            print("🔙 Reverted changes")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Could not revert: {e}")


class TCRRunner:
    """Main TCR runner that manages the file watching."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = TCRConfig.from_yaml(config_path)
        self.observer = Observer()
        self.handler = TCRHandler(self.config)
        
    def start(self):
        """Start watching for file changes."""
        if not self.config.enabled:
            print("TCR is disabled in configuration")
            return
            
        print("🚀 Starting TCR mode...")
        print(f"Watching: {self.config.watch_paths}")
        print(f"Test command: {self.config.test_command}")
        
        # Check for uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first.")
            
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
        print("\n🛑 Stopping TCR mode...")
        self.observer.stop()
        self.observer.join()
        print("TCR mode stopped")


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
        print("Use Ctrl+C to stop TCR mode")
        

if __name__ == '__main__':
    main()