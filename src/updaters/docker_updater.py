"""
Docker image updater for pwncloudos-sync.
"""

import subprocess
from typing import Optional
from .base import BaseUpdater, UpdateResult


class DockerUpdater(BaseUpdater):
    """Updater for Docker-based tools."""

    def get_current_version(self) -> Optional[str]:
        """Get current image version."""
        # Docker versioning is complex, return image ID
        return None

    def get_latest_version(self) -> Optional[str]:
        """Get latest version (not applicable for Docker)."""
        return None

    def needs_update(self) -> bool:
        """Docker images should always be checked for updates."""
        return True

    def perform_update(self) -> UpdateResult:
        """Execute docker-compose pull."""
        try:
            compose_file = getattr(self.tool, 'docker_compose', None)

            if compose_file:
                result = subprocess.run(
                    ['docker-compose', '-f', str(compose_file), 'pull'],
                    capture_output=True, text=True, timeout=600
                )
            else:
                # Try docker pull directly
                result = subprocess.run(
                    ['docker', 'pull', self.tool.name],
                    capture_output=True, text=True, timeout=600
                )

            if result.returncode == 0:
                return UpdateResult(
                    success=True,
                    tool_name=self.tool.name,
                    old_version="docker",
                    new_version="latest",
                )
            else:
                return UpdateResult(
                    success=False,
                    tool_name=self.tool.name,
                    error_message=result.stderr,
                )

        except subprocess.TimeoutExpired:
            return UpdateResult(
                success=False,
                tool_name=self.tool.name,
                error_message="Docker pull timed out",
            )
        except Exception as e:
            return UpdateResult(
                success=False,
                tool_name=self.tool.name,
                error_message=str(e),
            )
