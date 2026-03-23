"""
State management for pwncloudos-sync.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger('pwncloudos-sync')


@dataclass
class ToolState:
    """State of a tool."""
    name: str
    installed_version: str
    last_update: str  # ISO format datetime
    last_check: str   # ISO format datetime
    update_count: int = 0
    last_error: Optional[str] = None


class StateManager:
    """Manages state persistence for tools."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "tool_versions.json"
        self._state: Dict[str, ToolState] = {}

    def load(self) -> None:
        """Load state from disk."""
        if not self.state_file.exists():
            logger.debug("No state file found, starting fresh")
            return

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            for name, state_dict in data.items():
                self._state[name] = ToolState(**state_dict)

            logger.debug(f"Loaded state for {len(self._state)} tools")
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")
            self._state = {}

    def save(self) -> None:
        """Persist state to disk."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Use atomic write pattern
        temp_file = self.state_file.with_suffix('.tmp')

        try:
            data = {name: asdict(state) for name, state in self._state.items()}

            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.state_file)
            logger.debug(f"Saved state for {len(self._state)} tools")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            if temp_file.exists():
                temp_file.unlink()

    def get_tool_state(self, tool_name: str) -> Optional[ToolState]:
        """Get state for a specific tool."""
        return self._state.get(tool_name)

    def update_tool_state(self, tool_name: str, version: str, timestamp: datetime) -> None:
        """Update tool state after successful update."""
        existing = self._state.get(tool_name)

        self._state[tool_name] = ToolState(
            name=tool_name,
            installed_version=version,
            last_update=timestamp.isoformat(),
            last_check=timestamp.isoformat(),
            update_count=(existing.update_count + 1) if existing else 1,
            last_error=None
        )

    def record_check(self, tool_name: str) -> None:
        """Record that a tool was checked (even if not updated)."""
        if tool_name in self._state:
            state = self._state[tool_name]
            self._state[tool_name] = ToolState(
                name=state.name,
                installed_version=state.installed_version,
                last_update=state.last_update,
                last_check=datetime.now().isoformat(),
                update_count=state.update_count,
                last_error=state.last_error
            )

    def record_error(self, tool_name: str, error: str) -> None:
        """Record an error for a tool."""
        if tool_name in self._state:
            state = self._state[tool_name]
            self._state[tool_name] = ToolState(
                name=state.name,
                installed_version=state.installed_version,
                last_update=state.last_update,
                last_check=datetime.now().isoformat(),
                update_count=state.update_count,
                last_error=error
            )
        else:
            self._state[tool_name] = ToolState(
                name=tool_name,
                installed_version="unknown",
                last_update="",
                last_check=datetime.now().isoformat(),
                update_count=0,
                last_error=error
            )

    def get_last_update_time(self, tool_name: str) -> Optional[datetime]:
        """Get last update timestamp for a tool."""
        state = self._state.get(tool_name)
        if state and state.last_update:
            try:
                return datetime.fromisoformat(state.last_update)
            except ValueError:
                return None
        return None
