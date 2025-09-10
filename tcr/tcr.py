#!/usr/bin/env python3
"""TCR (Test && Commit || Revert) implementation for AI-constrained development."""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import git
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class TCRConfig:
    """Configuration for TCR behavior."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: Optional[Path]) -> dict:
        """Load configuration from file or use defaults."""
        defaults = {
            'enabled': True,
            'watch_paths': ['epistemix_platform/', 'simulations/'],
            'ignore_paths': ['*.pyc', '__pycache__', '.git', '*.egg-info'],
            'test_command': 'poetry run pytest -xvs',
            'test_timeout': 30,
            'commit_prefix': 'TCR',
            'revert_on_failure': True,
            'debounce_seconds': 2,
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f).get('tcr', {})
                defaults.update(user_config)
                
        return defaults


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
        for pattern in self.config.config['ignore_paths']:
            if path.match(pattern):
                return
                
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_run < self.config.config['debounce_seconds']:
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
                self.config.config['test_command'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.config['test_timeout']
            )
            
            if result.returncode == 0:
                print("✅ Tests passed!")
                return True
            else:
                print(f"❌ Tests failed!\n{result.stdout}\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ Tests timed out after {self.config.config['test_timeout']} seconds")
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
            message = f"{self.config.config['commit_prefix']}: {timestamp} - Modified {changed_file.name}"
            
            # Commit
            subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
            print(f"✅ Committed: {message}")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Could not commit: {e}")
            
    def _revert_changes(self):
        """Revert uncommitted changes."""
        if not self.config.config['revert_on_failure']:
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
        self.config = TCRConfig(config_path)
        self.observer = Observer()
        self.handler = TCRHandler(self.config)
        
    def start(self):
        """Start watching for file changes."""
        if not self.config.config['enabled']:
            print("TCR is disabled in configuration")
            return
            
        print("🚀 Starting TCR mode...")
        print(f"Watching: {self.config.config['watch_paths']}")
        print(f"Test command: {self.config.config['test_command']}")
        
        # Check for uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first.")
            
        # Set up watchers for each path
        for path in self.config.config['watch_paths']:
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
    parser.add_argument('--config', type=Path, help='Path to configuration file')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        runner = TCRRunner(args.config)
        runner.start()
    elif args.command == 'stop':
        # Stop is handled by KeyboardInterrupt in start()
        print("Use Ctrl+C to stop TCR mode")
        

if __name__ == '__main__':
    main()