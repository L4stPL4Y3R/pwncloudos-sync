"""
CLI argument parsing for pwncloudos-sync.
"""

import argparse
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog='pwncloudos-sync',
        description='Update all PwnCloudOS security tools to their latest versions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pwncloudos-sync --all              Update all tools
  pwncloudos-sync --category aws     Update only AWS tools
  pwncloudos-sync --tool cloudfox    Update specific tool
  pwncloudos-sync --dry-run          Show what would be updated
  pwncloudos-sync --check            Check for updates only
  pwncloudos-sync --list             List all tools
        """
    )

    # Update scope
    scope = parser.add_argument_group('Update Scope')
    scope.add_argument('--all', '-a', action='store_true',
                       help='Update all tools (default behavior)')
    scope.add_argument('--category', '-c',
                       choices=['aws', 'azure', 'gcp', 'multi_cloud',
                               'ps_tools', 'code_scanning', 'cracking', 'system'],
                       help='Update only tools in specific category')
    scope.add_argument('--tool', '-t', action='append', dest='tools',
                       help='Update specific tool(s) by name (can be repeated)')
    scope.add_argument('--exclude', '-e', action='append', dest='exclude_tools',
                       help='Exclude specific tool(s) from update (can be repeated)')

    # Behavior
    behavior = parser.add_argument_group('Behavior')
    behavior.add_argument('--dry-run', '-n', action='store_true',
                          help='Show what would be updated without making changes')
    behavior.add_argument('--force', '-f', action='store_true',
                          help='Force update even if already at latest version')
    behavior.add_argument('--no-rollback', action='store_true',
                          help='Disable automatic rollback on failure')
    behavior.add_argument('--parallel', '-p', action='store_true',
                          help='Update tools in parallel (faster, more resource intensive)')
    behavior.add_argument('--workers', type=int, default=4,
                          help='Number of parallel workers (default: 4)')

    # Output
    output = parser.add_argument_group('Output')
    output.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase verbosity (-v, -vv, -vvv)')
    output.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress all output except errors')
    output.add_argument('--log-file', type=Path,
                        default=Path('logs/pwncloudos-sync.log'),
                        help='Log file path (default: logs/pwncloudos-sync.log)')
    output.add_argument('--json', action='store_true',
                        help='Output results as JSON')

    # Information
    info = parser.add_argument_group('Information')
    info.add_argument('--list', '-l', action='store_true', dest='list_only',
                      help='List all tools and their current versions')
    info.add_argument('--check', action='store_true', dest='check_only',
                      help='Check for updates without installing')
    info.add_argument('--version', action='version',
                      version='%(prog)s 1.0.0')

    return parser


def parse_args(args=None):
    """Parse command line arguments."""
    parser = create_parser()
    return parser.parse_args(args)
