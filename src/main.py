#!/usr/bin/env python3
"""
pwncloudos-sync - Main entry point

This module is the main entry point for the PwnCloudOS tool updater.
It orchestrates the update process for all security tools.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

from .cli import (
    create_parser, parse_args, print_banner, print_tools_table,
    print_update_summary, confirm_update, Colors
)
from .config import Config, load_config
from .logger import setup_logging, SyncLogger
from .core.connectivity import check_internet_connectivity, check_github_api_rate_limit
from .core.privileges import check_sudo_available, request_sudo_upfront
from .core.arch import detect_architecture
from .core.state import StateManager
from .core.rollback import RollbackEngine
from .tools.registry import load_tools_manifest, get_tools_for_update


def main() -> int:
    """Main entry point."""
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()

    # Load configuration
    config = load_config(args)

    # Print banner (unless quiet mode)
    if not config.quiet:
        print_banner()

    # Setup logging
    logger = setup_logging(config)
    sync_logger = SyncLogger(config.log_file, config.verbose)

    logger.info(f"pwncloudos-sync v1.0.0 starting at {datetime.now().isoformat()}")

    # Load tools manifest (do this before connectivity checks for --list)
    if not config.quiet:
        print(f"{Colors.CYAN}Loading tools manifest...{Colors.END}")
    tools = load_tools_manifest()

    # Filter tools based on arguments
    tools_to_update = get_tools_for_update(tools, config)

    # Handle --list: Show tools and exit (no network required)
    if config.list_only:
        print_tools_table(tools_to_update)
        return 0

    # Pre-flight checks
    if not config.quiet:
        print(f"\n{Colors.CYAN}Running pre-flight checks...{Colors.END}")

    # Check architecture
    try:
        arch = detect_architecture()
        if not config.quiet:
            print(f"  {Colors.GREEN}✓{Colors.END} Architecture: {Colors.WHITE}{arch}{Colors.END}")
        logger.info(f"Detected architecture: {arch}")
    except Exception as e:
        print(f"  {Colors.RED}✗{Colors.END} Architecture detection failed: {e}")
        return 3

    # Check internet connectivity
    if not check_internet_connectivity():
        print(f"  {Colors.RED}✗{Colors.END} No internet connectivity")
        return 4
    if not config.quiet:
        print(f"  {Colors.GREEN}✓{Colors.END} Internet connectivity: OK")

    # Check GitHub API rate limit
    rate_info = check_github_api_rate_limit()
    if rate_info:
        remaining = rate_info['remaining']
        if remaining < 100:
            print(f"  {Colors.YELLOW}⚠{Colors.END} GitHub API rate limit low: {remaining} remaining")
        else:
            if not config.quiet:
                print(f"  {Colors.GREEN}✓{Colors.END} GitHub API rate limit: {remaining} remaining")

    # Check sudo privileges for /opt/ writes
    if not check_sudo_available():
        print(f"  {Colors.RED}✗{Colors.END} sudo access required for updating tools in /opt/")
        return 5
    if not config.quiet:
        print(f"  {Colors.GREEN}✓{Colors.END} sudo privileges: OK")

    if not config.quiet:
        print(f"\n{Colors.GREEN}All pre-flight checks passed!{Colors.END}")

    logger.info(f"Found {len(tools_to_update)} tools to check for updates")

    # Handle --check: Check for updates without installing
    if config.check_only:
        check_updates_only(tools_to_update, config, logger)
        return 0

    # VALIDATION STEP: Show tools table first
    print(f"\n{Colors.BOLD}{Colors.WHITE}The following tools will be checked for updates:{Colors.END}")
    print_tools_table(tools_to_update)

    # Show update summary
    print_update_summary(tools_to_update)

    # Confirmation prompt (unless --yes/-y flag is used)
    if not config.no_confirm and not config.dry_run:
        if not confirm_update():
            print(f"\n{Colors.YELLOW}Update cancelled by user.{Colors.END}\n")
            return 0

    # Request sudo upfront to cache credentials
    if not config.dry_run:
        print(f"\n{Colors.CYAN}Requesting sudo credentials...{Colors.END}")
        request_sudo_upfront()

    # Initialize rollback engine
    backup_dir = Path.home() / '.cache' / 'pwncloudos-sync' / 'backups'
    rollback_engine = RollbackEngine(backup_dir)

    # Initialize state manager
    state_dir = Path.home() / '.cache' / 'pwncloudos-sync' / 'state'
    state_manager = StateManager(state_dir)
    state_manager.load()

    # Perform updates
    print(f"\n{Colors.BOLD}{Colors.CYAN}Starting updates...{Colors.END}\n")

    results = []
    for i, tool in enumerate(tools_to_update, 1):
        print(f"[{i}/{len(tools_to_update)}] ", end='')
        result = update_tool(tool, config, rollback_engine, state_manager, sync_logger)
        results.append(result)

    # Print summary
    sync_logger.summary(results)

    # Save state
    state_manager.save()

    # Determine exit code
    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success and not r.skipped)

    if failed_count == 0:
        return 0
    elif success_count > 0:
        return 1
    else:
        return 2


def update_tool(tool, config, rollback_engine, state_manager, logger):
    """Update a single tool."""
    from .tools.registry import get_updater_for_tool
    from .core.safeguards import validate_update_target
    from .core.arch import detect_architecture
    from .updaters.base import UpdateResult

    logger.tool_start(tool.name)

    try:
        # Skip tools not supported on current architecture.
        current_arch = detect_architecture()
        if tool.arch_support and current_arch not in tool.arch_support:
            supported_arches = ', '.join(tool.arch_support)
            reason = f"Unsupported on {current_arch} (supports: {supported_arches})"
            logger.tool_skip(tool.name, reason)
            return UpdateResult(
                success=True,
                tool_name=tool.name,
                skipped=True,
                skip_reason=reason,
            )

        # Validate target path is safe to update
        validate_update_target(tool.path)

        # Get the appropriate updater
        updater = get_updater_for_tool(tool, config)

        # Check if update is needed
        if not config.force and not updater.needs_update():
            logger.tool_skip(tool.name, "Already up to date")
            return UpdateResult(
                success=True,
                tool_name=tool.name,
                skipped=True,
                skip_reason="Already up to date"
            )

        if config.dry_run:
            logger.tool_skip(tool.name, "Dry run - would update")
            return UpdateResult(
                success=True,
                tool_name=tool.name,
                skipped=True,
                skip_reason="Dry run"
            )

        # Create backup
        rollback_data = rollback_engine.create_backup(tool, updater)

        # Perform update
        result = updater.perform_update()

        if result.success:
            if result.skipped:
                logger.tool_skip(tool.name, result.skip_reason or "Skipped")
                return result

            # Verify update
            if updater.verify_update():
                logger.tool_success(tool.name, result.old_version, result.new_version)
                state_manager.update_tool_state(tool.name, result.new_version, datetime.now())
            else:
                # Verification failed - rollback
                logger.tool_fail(tool.name, "Verification failed")
                rollback_engine.restore(rollback_data)
                result.success = False
                result.error_message = "Verification failed after update"
        else:
            # Update failed - rollback
            logger.tool_fail(tool.name, result.error_message)
            rollback_engine.restore(rollback_data)

        return result

    except Exception as e:
        logger.tool_fail(tool.name, str(e))
        return UpdateResult(
            success=False,
            tool_name=tool.name,
            error_message=str(e)
        )


def check_updates_only(tools, config, logger):
    """Check for updates without installing."""
    from .tools.registry import get_updater_for_tool
    from .cli import Colors

    print(f"\n{Colors.CYAN}{'═' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}                         CHECKING FOR UPDATES{Colors.END}")
    print(f"{Colors.CYAN}{'═' * 80}{Colors.END}\n")

    updates_available = []
    up_to_date = []
    errors = []

    for i, tool in enumerate(tools, 1):
        print(f"\r{Colors.GRAY}Checking [{i}/{len(tools)}] {tool.name}...{Colors.END}          ", end='', flush=True)
        try:
            updater = get_updater_for_tool(tool, config)
            current = updater.get_current_version() or "unknown"
            latest = updater.get_latest_version() or "unknown"
            needs_update = updater.needs_update()

            if needs_update:
                updates_available.append((tool.name, current, latest))
            else:
                up_to_date.append((tool.name, current))
        except Exception as e:
            errors.append((tool.name, str(e)[:30]))

    print("\r" + " " * 80 + "\r", end='')  # Clear line

    # Updates available
    if updates_available:
        print(f"{Colors.YELLOW}{Colors.BOLD}Updates Available ({len(updates_available)}):{Colors.END}")
        for name, current, latest in updates_available:
            print(f"  {Colors.YELLOW}↑{Colors.END} {name}: {current} → {Colors.GREEN}{latest}{Colors.END}")

    # Up to date
    if up_to_date:
        print(f"\n{Colors.GREEN}{Colors.BOLD}Already Up to Date ({len(up_to_date)}):{Colors.END}")
        for name, version in up_to_date:
            print(f"  {Colors.GREEN}✓{Colors.END} {name} ({version})")

    # Errors
    if errors:
        print(f"\n{Colors.RED}{Colors.BOLD}Check Failed ({len(errors)}):{Colors.END}")
        for name, error in errors:
            print(f"  {Colors.RED}✗{Colors.END} {name}: {error}")

    print(f"\n{Colors.CYAN}{'═' * 80}{Colors.END}")

    # Summary
    print(f"\n{Colors.BOLD}Summary:{Colors.END}")
    print(f"  • Updates available: {Colors.YELLOW}{len(updates_available)}{Colors.END}")
    print(f"  • Up to date: {Colors.GREEN}{len(up_to_date)}{Colors.END}")
    if errors:
        print(f"  • Errors: {Colors.RED}{len(errors)}{Colors.END}")

    if updates_available:
        print(f"\n{Colors.BOLD}Run {Colors.CYAN}pwncloudos-sync --all{Colors.END}{Colors.BOLD} to update.{Colors.END}")

    print()


class UpdateResult:
    """Result of a tool update."""
    def __init__(self, success: bool, tool_name: str, old_version: str = None,
                 new_version: str = None, error_message: str = None,
                 skipped: bool = False, skip_reason: str = None):
        self.success = success
        self.tool_name = tool_name
        self.old_version = old_version
        self.new_version = new_version
        self.error_message = error_message
        self.skipped = skipped
        self.skip_reason = skip_reason


if __name__ == "__main__":
    sys.exit(main())
