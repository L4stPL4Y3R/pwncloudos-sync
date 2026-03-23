"""
Git repository updater for pwncloudos-sync.
"""

import subprocess
from typing import Optional
from .base import BaseUpdater, UpdateResult


class GitUpdater(BaseUpdater):
    """Updater for git repositories."""

    def get_current_version(self) -> Optional[str]:
        """Get current commit hash."""
        try:
            result = subprocess.run(
                ['git', '-C', str(self.tool.path), 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Failed to get current version: {e}")
        return None

    def get_latest_version(self) -> Optional[str]:
        """Get latest commit hash from remote."""
        try:
            # Fetch first
            subprocess.run(
                ['git', '-C', str(self.tool.path), 'fetch', 'origin'],
                capture_output=True, timeout=60
            )

            # Get remote HEAD
            result = subprocess.run(
                ['git', '-C', str(self.tool.path), 'rev-parse', '--short', 'origin/HEAD'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                # Try origin/main or origin/master
                for branch in ['origin/main', 'origin/master']:
                    result = subprocess.run(
                        ['git', '-C', str(self.tool.path), 'rev-parse', '--short', branch],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()

            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            self.logger.debug(f"Failed to get latest version: {e}")
        return None

    def needs_update(self) -> bool:
        """Check if there are new commits."""
        try:
            # Fetch first
            subprocess.run(
                ['git', '-C', str(self.tool.path), 'fetch', 'origin'],
                capture_output=True, timeout=60
            )

            # Count commits behind
            result = subprocess.run(
                ['git', '-C', str(self.tool.path), 'rev-list', 'HEAD...origin/HEAD', '--count'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                # Try with explicit branch
                result = subprocess.run(
                    ['git', '-C', str(self.tool.path), 'rev-list', 'HEAD...origin/main', '--count'],
                    capture_output=True, text=True
                )

            if result.returncode == 0:
                count = int(result.stdout.strip())
                return count > 0
        except Exception as e:
            self.logger.debug(f"Failed to check for updates: {e}")

        return False

    def perform_update(self) -> UpdateResult:
        """Execute git pull."""
        old_version = self.get_current_version()

        try:
            # Try git pull first
            result = subprocess.run(
                ['git', '-C', str(self.tool.path), 'pull', 'origin', 'HEAD'],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode != 0:
                # If pull fails, try reset --hard
                self.logger.warning("git pull failed, trying reset --hard")
                result = subprocess.run(
                    ['git', '-C', str(self.tool.path), 'reset', '--hard', 'origin/HEAD'],
                    capture_output=True, text=True, timeout=60
                )

                if result.returncode != 0:
                    # Try with explicit branch
                    result = subprocess.run(
                        ['git', '-C', str(self.tool.path), 'reset', '--hard', 'origin/main'],
                        capture_output=True, text=True, timeout=60
                    )

            if result.returncode == 0:
                new_version = self.get_current_version()
                return UpdateResult(
                    success=True,
                    tool_name=self.tool.name,
                    old_version=old_version,
                    new_version=new_version,
                )
            else:
                return UpdateResult(
                    success=False,
                    tool_name=self.tool.name,
                    old_version=old_version,
                    error_message=result.stderr,
                )

        except subprocess.TimeoutExpired:
            return UpdateResult(
                success=False,
                tool_name=self.tool.name,
                old_version=old_version,
                error_message="Git operation timed out",
            )
        except Exception as e:
            return UpdateResult(
                success=False,
                tool_name=self.tool.name,
                old_version=old_version,
                error_message=str(e),
            )

    def verify_update(self) -> bool:
        """Verify git repository is in good state."""
        try:
            result = subprocess.run(
                ['git', '-C', str(self.tool.path), 'status'],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
