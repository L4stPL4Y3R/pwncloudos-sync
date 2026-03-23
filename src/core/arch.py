"""
Architecture detection for pwncloudos-sync.
"""

import platform
import subprocess
from typing import Dict


class UnsupportedArchitectureError(Exception):
    """Raised when the system architecture is not supported."""
    pass


# Architecture mapping
ARCH_MAPPING: Dict[str, str] = {
    'x86_64': 'amd64',
    'amd64': 'amd64',
    'aarch64': 'arm64',
    'arm64': 'arm64',
}


def detect_architecture() -> str:
    """
    Detect the system architecture.

    Returns:
        str: 'amd64' or 'arm64'

    Raises:
        UnsupportedArchitectureError: If architecture is not supported
    """
    machine = platform.machine().lower()

    if machine in ARCH_MAPPING:
        return ARCH_MAPPING[machine]

    # Fallback to uname
    try:
        result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
        machine = result.stdout.strip().lower()
        if machine in ARCH_MAPPING:
            return ARCH_MAPPING[machine]
    except Exception:
        pass

    raise UnsupportedArchitectureError(
        f"Unsupported architecture: {machine}. "
        f"PwnCloudOS only supports AMD64 and ARM64."
    )


def get_binary_asset_pattern(tool_name: str, arch: str) -> Dict[str, str]:
    """
    Get the binary asset patterns for a tool.

    Args:
        tool_name: Name of the tool
        arch: Architecture ('amd64' or 'arm64')

    Returns:
        Dict with 'pattern' and 'binary_name' keys
    """
    PATTERNS = {
        'cloudfox': {
            'amd64': 'cloudfox_*_linux_amd64.tar.gz',
            'arm64': 'cloudfox_*_linux_arm64.tar.gz',
            'binary_name': 'cloudfox',
        },
        'azurehound': {
            'amd64': 'azurehound-linux-amd64.zip',
            'arm64': 'azurehound-linux-arm64.zip',
            'binary_name': 'azurehound',
        },
        'aws-enumerator': {
            'amd64': 'aws-enumerator_linux_amd64',
            'arm64': 'aws-enumerator_linux_arm64',
            'binary_name': 'aws-enumerator',
        },
        'steampipe': {
            'amd64': 'steampipe_linux_amd64.tar.gz',
            'arm64': 'steampipe_linux_arm64.tar.gz',
            'binary_name': 'steampipe',
        },
        'powerpipe': {
            'amd64': 'powerpipe_linux_amd64.tar.gz',
            'arm64': 'powerpipe_linux_arm64.tar.gz',
            'binary_name': 'powerpipe',
        },
    }

    if tool_name not in PATTERNS:
        raise ValueError(f"No binary pattern defined for: {tool_name}")

    pattern_info = PATTERNS[tool_name]
    return {
        'pattern': pattern_info[arch],
        'binary_name': pattern_info['binary_name'],
    }


def validate_binary_for_arch(binary_path: str) -> bool:
    """
    Validate that a binary matches the current system architecture.

    Args:
        binary_path: Path to the binary file

    Returns:
        bool: True if binary matches system architecture
    """
    try:
        result = subprocess.run(
            ['file', binary_path],
            capture_output=True,
            text=True
        )
        output = result.stdout.lower()

        arch = detect_architecture()

        if arch == 'amd64':
            return 'x86-64' in output or 'x86_64' in output
        elif arch == 'arm64':
            return 'aarch64' in output or 'arm64' in output

        return False
    except Exception:
        return False
