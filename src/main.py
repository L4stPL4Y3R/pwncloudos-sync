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

from .cli import create_parser, parse_args
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

    # Setup logging
    logger = setup_logging(config)
    sync_logger = SyncLogger(config.log_file, config.verbose)

    logger.info(f"pwncloudos-sync v1.0.0 starting at {datetime.now().isoformat()}")

    # Pre-flight checks
    logger.info("Running pre-flight checks...")

    # Check architecture
    try:
        arch = detect_architecture()
        logger.info(f"Detected architecture: {arch}")
    except Exception as e:
        logger.error(f"Failed to detect architecture: {e}")
        return 3

    # Check internet connectivity
    if not check_internet_connectivity():
        logger.error("No internet connectivity. Cannot proceed.")
        return 4

    # Check GitHub API rate limit
    rate_info = check_github_api_rate_limit()
    if rate_info and rate_info['remaining'] < 100:
        logger.warning(f"GitHub API rate limit low: {rate_info['remaining']} remaining")

    # Check sudo privileges for /opt/ writes
    if not check_sudo_available():
        logger.error("sudo access required for updating tools in /opt/")
        return 5

    # Request sudo upfront to cache credentials
    if not config.dry_run:
        request_sudo_upfront()

    # Load tools manifest
    logger.info("Loading tools manifest...")
    tools = load_tools_manifest()

    # Filter tools based on arguments
    tools_to_update = get_tools_for_update(tools, config)
    logger.info(f"Found {len(tools_to_update)} tools to check for updates")

    if config.list_only:
        # Just list tools and exit
        print_tool_list(tools_to_update)
        return 0

    if config.check_only:
        # Check for updates without installing
        check_updates_only(tools_to_update, config, logger)
        return 0

    # Initialize rollback engine
    rollback_engine = RollbackEngine(config.backup_dir)

    # Initialize state manager
    state_manager = StateManager(config.state_dir)
    state_manager.load()

    # Perform updates
    results = []
    for tool in tools_to_update:
        result = update_tool(tool, config, rollback_engine, state_manager, sync_logger)
        results.append(result)

    # Print summary
    sync_logger.summary(results)

    # Save state
    state_manager.save()

    # Determine exit code
    success_count = sum(1 for r in results if r.success)
    if success_count == len(results):
        return 0
    elif success_count > 0:
        return 1
    else:
        return 2


def update_tool(tool, config, rollback_engine, state_manager, logger):
    """Update a single tool."""
    from .tools.registry import get_updater_for_tool
    from .core.safeguards import validate_update_target

    logger.tool_start(tool.name)

    try:
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


def print_tool_list(tools):
    """Print list of tools."""
    print(f"\n{'Tool':<30} {'Category':<15} {'Method':<20} {'Path'}")
    print("-" * 100)
    for tool in tools:
        print(f"{tool.name:<30} {tool.category:<15} {tool.install_method:<20} {tool.path}")


def check_updates_only(tools, config, logger):
    """Check for updates without installing."""
    from .tools.registry import get_updater_for_tool

    print(f"\n{'Tool':<30} {'Current':<15} {'Latest':<15} {'Status'}")
    print("-" * 80)

    for tool in tools:
        try:
            updater = get_updater_for_tool(tool, config)
            current = updater.get_current_version() or "unknown"
            latest = updater.get_latest_version() or "unknown"
            needs_update = updater.needs_update()

            status = "UPDATE AVAILABLE" if needs_update else "Up to date"
            print(f"{tool.name:<30} {current:<15} {latest:<15} {status}")
        except Exception as e:
            print(f"{tool.name:<30} {'error':<15} {'error':<15} {str(e)[:20]}")


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
