# pwncloudos-sync

A standalone tool that performs in-place upgrades of all security tools installed on [PwnCloudOS](https://pwncloudos.pwnedlabs.io/) without requiring users to download fresh OS images.

## Features

- **Multi-method updates**: Supports git pull, file replacement, pipx upgrade, binary downloads, and more
- **Architecture-aware**: Automatically detects AMD64/ARM64 and downloads correct binaries
- **Non-destructive**: Full rollback on any failure - never breaks a working tool
- **Idempotent**: Running twice produces the same state as running once
- **Launcher-safe**: Never modifies launcher scripts or desktop files
- **Lightweight updates**: For simple Python tools, only replaces `.py` + `requirements.txt`

## Quick Start

```bash
# Clone the repository
git clone https://github.com/L4stPL4Y3R/pwncloudos-sync.git
cd pwncloudos-sync

# Install dependencies
pip3 install -r requirements.txt

# Run the updater
sudo ./pwncloudos-sync --all
```

## Usage

```bash
# Update all tools
pwncloudos-sync --all

# Update only AWS tools
pwncloudos-sync --category aws

# Update specific tools
pwncloudos-sync --tool cloudfox --tool prowler

# Dry run (show what would be updated)
pwncloudos-sync --dry-run

# Check for updates without installing
pwncloudos-sync --check

# List all tools and versions
pwncloudos-sync --list

# Force update even if current
pwncloudos-sync --all --force

# Verbose output
pwncloudos-sync --all -vv

# Parallel updates (faster)
pwncloudos-sync --all --parallel
```

## Supported Tool Categories

| Category | Location | Tools |
|----------|----------|-------|
| AWS | `/opt/aws_tools/` | AWeSomeUserFinder, pacu, pmapper, IAMGraph, etc. |
| Azure | `/opt/azure_tools/` | AzureHound, ROADtools, o365spray, BloodHound, etc. |
| GCP | `/opt/gcp_tools/` | gcp_scanner, sprayshark, username-anarchy, etc. |
| Multi-Cloud | `/opt/multi_cloud_tools/` | cloudfox, prowler, ScoutSuite, steampipe, etc. |
| PowerShell | `/opt/ps_tools/` | AADInternals, GraphRunner, TokenTacticsV2, etc. |
| Code Scanning | `/opt/code_scanning/` | trufflehog, git-secrets |
| Cracking | `/opt/cracking-tools/` | John the Ripper, hashcat |

## Update Methods

| Method | Description |
|--------|-------------|
| `git_pull` | Full `git pull` for repositories with `.git` directory |
| `file_replacement` | Download only `.py` + `requirements.txt` (lightweight) |
| `pipx` | Use `pipx upgrade` for pipx-installed tools |
| `binary` | Download arch-specific binary from GitHub Releases |
| `apt` | Use `apt-get upgrade` for system packages |
| `docker` | Pull latest Docker images |
| `custom` | Run custom update scripts |

## Architecture Support

- **AMD64** (x86_64): VirtualBox, VMware Workstation
- **ARM64** (aarch64): VMware on Apple Silicon (M-series)

## Safety Features

1. **Protected Paths**: Launcher scripts and desktop files are never modified
2. **Automatic Backup**: State is saved before each update
3. **Rollback**: Failed updates are automatically rolled back
4. **Verification**: Tools are tested after update to ensure they work

## Requirements

- Python 3.10+
- PwnCloudOS v1.2+
- Internet connectivity
- sudo access (for `/opt/` directory writes)

## Configuration

Configuration file location: `~/.config/pwncloudos-sync/config.yaml`

```yaml
# Example configuration
verbose: true
parallel: true
max_workers: 4
skip_tools:
  - bloodhound  # Skip Docker-based tools
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All updates successful |
| 1 | Some updates failed (partial success) |
| 2 | All updates failed |
| 3 | Configuration error |
| 4 | Network connectivity error |
| 5 | Permission denied |

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [PwnCloudOS](https://pwncloudos.pwnedlabs.io/) by PwnedLabs
- All the amazing security tool authors

## Links

- [PwnCloudOS Download](https://pwncloudos.pwnedlabs.io/)
- [PwnCloudOS GitHub](https://github.com/pwnedlabs/pwncloudos)
- [Documentation](https://pwncloudos.readthedocs.io/)
