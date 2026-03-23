# pwncloudos-sync Implementation Plan

**Version:** 1.1
**Author:** Systems Engineering Team
**Date:** 2026-03-23
**Target Repository:** `pwncloudos-sync`

---

## Executive Summary

This document provides a comprehensive implementation plan for `pwncloudos-sync`, a standalone tool that performs in-place upgrades of all security tools installed on PwnCloudOS without requiring users to download fresh OS images. The plan covers architecture detection, tool inventory, update strategies, rollback mechanisms, and edge case handling.

---

## CRITICAL: File Protection Rules

### Files That Are NEVER Modified

The following files must NEVER be modified, deleted, or replaced by `pwncloudos-sync`:

| Location | Contents | Reason |
|----------|----------|--------|
| `/path/to/pwncloudos/docs/configs/launchers/**/*.sh` | XFCE menu launcher scripts | User-facing help documentation, not actual tools |
| `/path/to/pwncloudos/docs/configs/launchers/custom/*.desktop` | Desktop integration files | XFCE menu entries |
| `/path/to/pwncloudos/docs/configs/shell/**` | Shell configurations | User customizations |
| `/path/to/pwncloudos/docs/configs/xfce/**` | Desktop profiles | User preferences |
| `/path/to/pwncloudos/docs/configs/menulibre/**` | Menu configurations | Desktop menu layout |

### Files That ARE Updated

The following locations contain the actual tools that `pwncloudos-sync` updates:

| Location | Type | Update Method |
|----------|------|---------------|
| `/opt/aws_tools/*` | Git repositories | `git pull` + pip deps |
| `/opt/azure_tools/*` | Git repositories | `git pull` + pip deps |
| `/opt/gcp_tools/*` | Git repositories | `git pull` + pip deps |
| `/opt/multi_cloud_tools/*` | Git repos / Binaries | `git pull` OR binary download |
| `/opt/ps_tools/*` | Git repositories | `git pull` only |
| `/opt/code_scanning/*` | Git repositories | `git pull` + possible compile |
| `/opt/cracking-tools/*` | Git repositories | `git pull` + compile |
| `~/.local/pipx/venvs/*` | pipx packages | `pipx upgrade` |
| `/usr/local/bin/*` | Custom binaries | Binary download |

### Understanding the Separation

```
pwncloudos/ (GitHub repository - contains docs and configs only)
├── docs/
│   └── configs/
│       └── launchers/     ← HELPER SCRIPTS (never touch)
│           ├── aws/
│           │   └── *.sh   ← Shows usage examples, NOT the actual tool
│           ├── azure/
│           └── ...

/opt/ (On the actual PwnCloudOS VM - contains real tools)
├── aws_tools/
│   └── AWeSomeUserFinder/    ← ACTUAL TOOL (git clone, update this)
│       ├── .git/
│       ├── AWeSomeUserFinder.py
│       └── requirements.txt
├── azure_tools/
│   └── o365spray/            ← ACTUAL TOOL (git clone, update this)
│       ├── .git/
│       ├── o365spray.py
│       └── requirements.txt
└── ...
```

**Key Insight:** The launcher scripts in `docs/configs/launchers/` are just documentation that show users how to use tools. The actual tools live in `/opt/` directories on the running PwnCloudOS system and are git repositories cloned from various GitHub sources.

---

## Table of Contents

1. [Tool Inventory & Analysis](#1-tool-inventory--analysis)
2. [Repository Architecture](#2-repository-architecture)
3. [Phase 1: Core Infrastructure](#3-phase-1-core-infrastructure)
4. [Phase 2: Update Engine Implementation](#4-phase-2-update-engine-implementation)
5. [Phase 3: Per-Tool Update Handlers](#5-phase-3-per-tool-update-handlers)
6. [Phase 4: Safety & Rollback Mechanisms](#6-phase-4-safety--rollback-mechanisms)
7. [Phase 5: User Interface & Logging](#7-phase-5-user-interface--logging)
8. [Phase 6: Testing & Validation](#8-phase-6-testing--validation)
9. [Edge Cases & Special Handling](#9-edge-cases--special-handling)
10. [Review Pass](#10-review-pass)

---

## 1. Tool Inventory & Analysis

### 1.1 Complete Tool Catalog

#### AWS Tools (`/opt/aws_tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| AWeSomeUserFinder | git clone | https://github.com/dievus/AWeSomeUserFinder | Both | Python, has requirements.txt |
| aws_enumerator | Binary (Go) | https://github.com/shabarkin/aws-enumerator | Both | Check releases for arch-specific binaries |
| github-oidc-checker | git clone | https://github.com/Rezonate-io/github-oidc-checker | Both | Python, has requirements.txt |
| IAMGraph | pipx | https://github.com/WithSecureLabs/IAMGraph | Both | PyPI: iamgraph |
| pacu | pipx | https://github.com/RhinoSecurityLabs/pacu | Both | PyPI: pacu |
| pmapper | pipx | https://github.com/nccgroup/PMapper | Both | PyPI: principalmapper |
| s3_account_search | pipx | https://github.com/WeAreCloudar/s3-account-search | Both | PyPI: s3-account-search |

#### Azure Tools (`/opt/azure_tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| AzSubEnum | git clone | https://github.com/yuyudhn/AzSubEnum | Both | Python, has requirements.txt |
| azure_hound | Binary (Go) | https://github.com/BloodHoundAD/AzureHound | Both | Check releases for arch-specific binaries |
| basicblobfinder | git clone | https://github.com/joswr1ght/basicblobfinder | Both | Python single-file |
| bloodhound | docker-compose | https://github.com/SpecterOps/BloodHound | Both | Docker images, no binary update |
| exfil_exchange_mail | git clone | https://github.com/rootsecdev/Azure-Red-Team | Both | PowerShell/Python scripts |
| o365enum | git clone | https://github.com/gremwell/o365enum | Both | Python, has requirements.txt |
| o365spray | git clone | https://github.com/0xZDH/o365spray | Both | Python, has requirements.txt |
| Oh365UserFinder | git clone | https://github.com/dievus/Oh365UserFinder | Both | Python, has requirements.txt |
| Omnispray | git clone | https://github.com/0xZDH/Omnispray | Both | Python, has requirements.txt |
| roadrecon | pipx | https://github.com/dirkjanm/ROADtools | Both | PyPI: roadtools |
| seamlesspass | pipx | https://github.com/Malcrove/SeamlessPass | Both | PyPI: seamlesspass |

#### GCP Tools (`/opt/gcp_tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| automated-cloud-misconfiguration-testing | git clone | https://github.com/pwnedlabs/automated-cloud-misconfiguration-testing | Both | Bash/Python scripts |
| gcp-permissions-checker | git clone | https://github.com/egre55/gcp-permissions-checker | Both | Python |
| gcp_scanner | git clone | https://github.com/google/gcp_scanner | Both | Python, has requirements.txt |
| google-workspace-enum | git clone | https://github.com/pwnedlabs/google-workspace-enum | Both | Python |
| iam-policy-visualize | git clone | https://github.com/hac01/iam-policy-visualize | Both | Python |
| sprayshark | pipx/pip | https://github.com/helviojunior/sprayshark | Both | PyPI: sprayshark |
| username-anarchy | git clone | https://github.com/urbanadventurer/username-anarchy | Both | Ruby, no deps |

#### Multi-Cloud Tools (`/opt/multi_cloud_tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| cloudfox | Binary (Go) | https://github.com/BishopFox/cloudfox | Both | Releases have arch-specific binaries |
| powerpipe | Binary/Installer | https://powerpipe.io | Both | Custom installer script |
| prowler | pipx | https://github.com/prowler-cloud/prowler | Both | PyPI: prowler |
| s3scanner | pipx | https://github.com/sa7mon/S3Scanner | Both | PyPI: s3scanner |
| scoutsuite | pipx | https://github.com/nccgroup/ScoutSuite | Both | PyPI: scoutsuite |
| steampipe | Binary/Installer | https://github.com/turbot/steampipe | Both | Custom installer script |

#### PowerShell Tools (`/opt/ps_tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| AADInternals | git clone | https://github.com/Gerenios/AADInternals | Both | PowerShell module |
| GraphRunner | git clone | https://github.com/dafthack/GraphRunner | Both | PowerShell module |
| invoke_modules | git clone | https://github.com/PowerShellMafia/PowerSploit | Both | PowerShell module |
| MFASweep | git clone | https://github.com/dafthack/MFASweep | Both | PowerShell module |
| TokenTacticsV2 | git clone | https://github.com/f-bader/TokenTacticsV2 | Both | PowerShell module |

#### Code Scanning Tools (`/opt/code_scanning/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| git-secrets | apt/git clone | https://github.com/awslabs/git-secrets | Both | Makefile install |
| trufflehog | pipx | https://github.com/trufflesecurity/trufflehog | Both | PyPI: trufflehog |

#### Cracking Tools (`/opt/cracking-tools/`)

| Tool Name | Install Method | Source | Architecture | Special Notes |
|-----------|----------------|--------|--------------|---------------|
| john | git clone + compile | https://github.com/openwall/john | Both | Requires ./configure && make, arch-specific |
| hashcat | apt/binary | https://github.com/hashcat/hashcat | Both | apt or compile from source |

#### System Tools (Various Locations)

| Tool Name | Install Method | Location | Architecture | Special Notes |
|-----------|----------------|----------|--------------|---------------|
| AWS CLI | apt | /usr/bin/aws | Both | apt package: awscli |
| Azure CLI | pipx | ~/.local/bin/az | Both | PyPI: azure-cli |
| impacket | pipx | ~/.local/bin/ | Both | PyPI: impacket |
| ffuf | apt/Binary (Go) | /usr/bin/ffuf | Both | apt or GitHub releases |
| Chromium | apt | /usr/bin/chromium | Both | apt package |
| Firefox | apt | /usr/bin/firefox | Both | apt package |
| Flameshot | apt | /usr/bin/flameshot | Both | apt package |
| CAIDO | Binary Installer | /opt/ or /usr/local/bin | Both | Custom installer |
| BurpSuite Community | Binary Installer | /opt/ | Both | JAR-based installer |

### 1.2 Installation Method Summary

| Method | Tool Count | Update Strategy |
|--------|------------|-----------------|
| pipx | 14 | `pipx upgrade <package>` |
| git clone (Python) | 15 | `git pull` + `pip install -r requirements.txt` |
| **file replacement** | 7 | Download `.py` + `requirements.txt` from GitHub raw |
| git clone (PowerShell) | 5 | `git pull` only |
| git clone + compile | 2 | `git pull` + rebuild |
| Binary (Go releases) | 4 | GitHub Releases API → download arch binary |
| Binary Installer | 4 | Custom update scripts |
| Docker | 1 | `docker pull` |
| apt | 6+ | `apt update && apt upgrade` |

**Note:** File replacement is a lightweight alternative to git clone for simple Python tools. Tools can use either method depending on whether a `.git` directory exists.

### 1.3 Git Repository Update Workflow (Primary Method)

Since most tools in `/opt/` are git clones, this is the primary update method. Here's the detailed workflow:

#### Step-by-Step Git Update Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    Git Repository Update Flow                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK FOR UPDATES                                           │
│     └── git -C /opt/{category}/{tool} fetch origin             │
│     └── git -C /opt/{category}/{tool} rev-list HEAD...origin/HEAD --count │
│         (If count > 0, updates available)                       │
│                                                                  │
│  2. GET VERSION INFO                                            │
│     └── Current: git rev-parse --short HEAD                    │
│     └── Latest:  git rev-parse --short origin/HEAD             │
│     └── Compare and log the difference                          │
│                                                                  │
│  3. BACKUP CURRENT STATE                                        │
│     └── Record current commit: git rev-parse HEAD              │
│     └── Save to state file for rollback                        │
│                                                                  │
│  4. PERFORM UPDATE                                              │
│     └── git -C /opt/{category}/{tool} pull origin HEAD         │
│     └── OR: git reset --hard origin/HEAD (if conflicts)        │
│                                                                  │
│  5. POST-UPDATE ACTIONS (if applicable)                         │
│     └── Python tool: pip install -r requirements.txt           │
│     └── Compiled tool: ./configure && make                      │
│     └── PowerShell: No action needed                            │
│                                                                  │
│  6. VERIFY UPDATE                                               │
│     └── Check tool runs successfully                            │
│     └── If fails: rollback to saved commit                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Tool Categories by Post-Update Requirements

| Category | Tools | Post-Update Action |
|----------|-------|-------------------|
| **Git Only** | PowerShell tools (AADInternals, GraphRunner, MFASweep, TokenTacticsV2), username-anarchy | None - just `git pull` |
| **Git + pip** | Python tools (AWeSomeUserFinder, o365spray, AzSubEnum, gcp_scanner, etc.) | `pip install -r requirements.txt --upgrade` |
| **Git + compile** | john, git-secrets, hashcat (source) | Run configure/make scripts |
| **Not Git** | pipx tools, binary downloads | Different update method (see sections below) |

#### Example: Updating AWeSomeUserFinder

```bash
# The tool is located at: /opt/aws_tools/AWeSomeUserFinder/
# It was originally installed via: git clone https://github.com/dievus/AWeSomeUserFinder

# Step 1: Check for updates
cd /opt/aws_tools/AWeSomeUserFinder
git fetch origin
COMMITS_BEHIND=$(git rev-list HEAD...origin/HEAD --count)

if [ "$COMMITS_BEHIND" -gt 0 ]; then
    echo "Updates available: $COMMITS_BEHIND new commits"

    # Step 2: Save current state for rollback
    CURRENT_COMMIT=$(git rev-parse HEAD)
    echo "$CURRENT_COMMIT" > /tmp/rollback_AWeSomeUserFinder

    # Step 3: Pull updates
    git pull origin HEAD

    # Step 4: Update Python dependencies
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt --upgrade --quiet
    fi

    # Step 5: Verify tool works
    python3 AWeSomeUserFinder.py --help >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Verification failed, rolling back..."
        git reset --hard $CURRENT_COMMIT
    fi
fi
```

### 1.4 Extracting GitHub URLs from Launcher Files

The launcher files in `docs/configs/launchers/` contain embedded GitHub URLs that can be parsed to identify the source repository for each tool.

#### URL Extraction Pattern

```python
import re
from pathlib import Path

def extract_github_url_from_launcher(launcher_path: Path) -> str:
    """
    Extract GitHub repository URL from a launcher script.

    Launcher files contain patterns like:
    - echo -e "For more information, visit: ...https://github.com/{owner}/{repo}..."
    - echo -e "Documentation: ...https://github.com/{owner}/{repo}..."
    """
    content = launcher_path.read_text()

    # Match GitHub URLs in the launcher file
    pattern = r'https://github\.com/([^/\s"\\]+)/([^/\s"\\#]+)'
    matches = re.findall(pattern, content)

    if matches:
        # Return the first match as owner/repo
        owner, repo = matches[0]
        return f"{owner}/{repo}"

    return None


def build_launcher_to_tool_mapping() -> dict:
    """
    Build a mapping from launcher files to their corresponding GitHub repos.
    """
    mapping = {}
    launchers_dir = Path("docs/configs/launchers")

    for launcher in launchers_dir.glob("**/*.sh"):
        github_repo = extract_github_url_from_launcher(launcher)
        if github_repo:
            # Tool name is derived from launcher filename
            # e.g., "o365spray_launcher.sh" -> "o365spray"
            tool_name = launcher.stem.replace("_launcher", "").replace("_Launcher", "")
            mapping[tool_name] = {
                'launcher_file': str(launcher),
                'github_repo': github_repo,
                'category': launcher.parent.name,  # aws, azure, gcp, etc.
            }

    return mapping
```

#### Extracted GitHub URLs from Launcher Files

| Category | Tool | Launcher File | GitHub Repo |
|----------|------|---------------|-------------|
| aws | AWeSomeUserFinder | `awesome_userfinder_launcher.sh` | `dievus/AWeSomeUserFinder` |
| aws | aws-enumerator | `aws-enumerator_launcher.sh` | `shabarkin/aws-enumerator` |
| aws | github-oidc-checker | `github-oidc-checker_launcher.sh` | `Rezonate-io/github-oidc-checker` |
| aws | iamgraph | `iamgraph_launcher.sh` | `WithSecureLabs/IAMGraph` |
| aws | pmapper | `pmapper_launcher.sh` | `nccgroup/PMapper` |
| aws | s3-account-search | `s3-account-search_launcher.sh` | `WeAreCloudar/s3-account-search` |
| azure | AzSubEnum | `azsubenum_launcher.sh` | `yuyudhn/AzSubEnum` |
| azure | basicblobfinder | `basicblobfinder_launcher.sh` | `joswr1ght/basicblobfinder` |
| azure | exfil_exchange_mail | `exfil_exchange_mail_launcher.sh` | `rootsecdev/Azure-Red-Team` |
| azure | o365enum | `o365enum_launcher.sh` | `gremwell/o365enum` |
| azure | o365spray | `o365spray_launcher.sh` | `0xZDH/o365spray` |
| azure | Oh365UserFinder | `oh365userfinder_launcher.sh` | `dievus/Oh365UserFinder` |
| azure | Omnispray | `omnispray_launcher.sh` | `0xZDH/Omnispray` |
| azure | roadrecon | `roadrecon_launcher.sh` | `dirkjanm/ROADtools` |
| azure | seamlesspass | `seamlesspass_launcher.sh` | `Malcrove/SeamlessPass` |
| gcp | automated-cloud-misconfiguration | `gcp-misconfig_launcher.sh` | `pwnedlabs/automated-cloud-misconfiguration-testing` |
| gcp | gcp-permissions-checker | `gcp-permissions-checker_launcher.sh` | `egre55/gcp-permissions-checker` |
| gcp | gcp_scanner | `gcp-scanner_launcher.sh` | `google/gcp_scanner` |
| gcp | google-workspace-enum | `google-workspace-enum_launcher.sh` | `pwnedlabs/google-workspace-enum` |
| gcp | iam-policy-visualize | `iam-policy-visualize_launcher.sh` | `hac01/iam-policy-visualize` |
| gcp | sprayshark | `sprayshark_launcher.sh` | `helviojunior/sprayshark` |
| gcp | username-anarchy | `username-anarchy_launcher.sh` | `urbanadventurer/username-anarchy` |
| multi_cloud | cloudfox | `cloudfox_launcher.sh` | `BishopFox/cloudfox` |
| multi_cloud | powerpipe | `powerpipe_launcher.sh` | `turbot/powerpipe` |
| multi_cloud | prowler | `prowler_launcher.sh` | `prowler-cloud/prowler` |
| multi_cloud | s3scanner | `s3scanner_launcher.sh` | `sa7mon/S3Scanner` |
| multi_cloud | scoutsuite | `scoutsuite_launcher.sh` | `nccgroup/ScoutSuite` |
| multi_cloud | steampipe | `steampipe_launcher.sh` | `turbot/steampipe` |
| code_scanning | git-secrets | `git-secrets_launcher.sh` | `awslabs/git-secrets` |
| code_scanning | trufflehog | `trufflehog_launcher.sh` | `trufflesecurity/trufflehog` |

### 1.5 Update Strategy: File Replacement vs Git Pull

For Python-based tools, there are two update approaches:

#### Option A: Git Pull (Full Repository Update)
```
Best for: Tools with multiple files, complex structure, or build steps
Method: git pull origin HEAD
Pros: Gets all files, handles renames/deletes, maintains git history
Cons: Requires .git directory, may have merge conflicts
```

#### Option B: File Replacement (Lightweight Update)
```
Best for: Simple Python tools with just main.py + requirements.txt
Method: Download raw files from GitHub and replace existing
Pros: No git required, fast, clean
Cons: Doesn't handle file renames, may miss new supporting files
```

#### File Replacement Implementation

```python
import requests
from pathlib import Path

def get_raw_github_url(repo: str, branch: str, filepath: str) -> str:
    """
    Convert GitHub repo to raw content URL.
    Example: dievus/AWeSomeUserFinder ->
             https://raw.githubusercontent.com/dievus/AWeSomeUserFinder/main/AWeSomeUserFinder.py
    """
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{filepath}"


def update_tool_via_file_replacement(tool_path: Path, github_repo: str) -> UpdateResult:
    """
    Update a Python tool by downloading and replacing key files.

    This method is ideal for simple tools that consist of:
    - A main Python script (e.g., tool.py)
    - A requirements.txt file
    - Optional: README.md, config files
    """
    # Detect the main Python file and branch
    main_script = detect_main_script(tool_path)
    branch = get_default_branch(github_repo)  # 'main' or 'master'

    # Files to update
    files_to_update = []

    # 1. Main Python script
    if main_script:
        files_to_update.append(main_script.name)

    # 2. Requirements file
    if (tool_path / "requirements.txt").exists():
        files_to_update.append("requirements.txt")

    # Backup current files
    backup_dir = create_backup(tool_path, files_to_update)

    try:
        for filename in files_to_update:
            # Download new version from GitHub
            url = get_raw_github_url(github_repo, branch, filename)
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                # Write new content
                target_file = tool_path / filename
                target_file.write_text(response.text)
                logger.info(f"Updated {filename}")
            else:
                raise UpdateError(f"Failed to download {filename}: {response.status_code}")

        # Update Python dependencies if requirements.txt was updated
        if "requirements.txt" in files_to_update:
            subprocess.run(
                ["pip3", "install", "-r", str(tool_path / "requirements.txt"),
                 "--upgrade", "--quiet"],
                check=True
            )

        return UpdateResult(success=True, method="file_replacement")

    except Exception as e:
        # Rollback on failure
        restore_from_backup(backup_dir, tool_path)
        return UpdateResult(success=False, error_message=str(e))


def detect_main_script(tool_path: Path) -> Path:
    """
    Detect the main Python script in a tool directory.

    Patterns:
    - tool_name.py (matches directory name)
    - main.py
    - __main__.py
    - Single .py file in directory
    """
    tool_name = tool_path.name.lower()

    # Check common patterns
    candidates = [
        tool_path / f"{tool_name}.py",
        tool_path / "main.py",
        tool_path / "__main__.py",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Fallback: find single .py file
    py_files = list(tool_path.glob("*.py"))
    if len(py_files) == 1:
        return py_files[0]

    return None


def get_default_branch(github_repo: str) -> str:
    """
    Get the default branch name (main or master) from GitHub API.
    """
    url = f"https://api.github.com/repos/{github_repo}"
    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        return response.json().get('default_branch', 'main')

    return 'main'  # Default fallback
```

#### Decision Matrix: Which Update Method to Use

| Tool Type | Files | Update Method | Reason |
|-----------|-------|---------------|--------|
| Simple Python (1-2 .py files) | `tool.py`, `requirements.txt` | **File Replacement** | Fast, no git overhead |
| Complex Python (multiple modules) | Multiple .py, libs/ | **Git Pull** | Handles all file changes |
| PowerShell modules | Multiple .ps1, manifests | **Git Pull** | Module structure matters |
| Binary tools | Compiled binary | **Binary Download** | Get arch-specific release |
| pipx packages | Virtual env | **pipx upgrade** | Use pipx's own mechanism |

#### Automatic Method Selection Algorithm

```python
def select_update_method(tool_path: Path, github_repo: str) -> str:
    """
    Automatically select the best update method for a tool.

    Returns: 'git_pull', 'file_replacement', 'pipx', 'binary', or 'custom'
    """

    # 1. Check if it's a git repository
    has_git = (tool_path / '.git').exists()

    # 2. Count Python files
    py_files = list(tool_path.glob('*.py'))
    py_file_count = len([f for f in py_files if not f.name.startswith('_')])

    # 3. Check for package structure
    has_package = any([
        (tool_path / '__init__.py').exists(),
        (tool_path / 'setup.py').exists(),
        (tool_path / 'pyproject.toml').exists(),
        len(list(tool_path.glob('*/__init__.py'))) > 0,  # Subdirectory packages
    ])

    # 4. Make decision
    if has_git:
        # Git repository exists - use git pull
        return 'git_pull'

    elif py_file_count <= 2 and not has_package:
        # Simple tool with 1-2 Python files, no package structure
        # Use lightweight file replacement
        return 'file_replacement'

    elif py_file_count > 2 or has_package:
        # Complex tool - recommend cloning
        logger.warning(f"{tool_path} has no .git but is complex. Consider full clone.")
        return 'file_replacement'  # Still try file replacement as fallback

    else:
        return 'file_replacement'


def get_updater_for_tool(tool: Tool) -> BaseUpdater:
    """
    Factory function to get the correct updater for a tool.
    """
    if tool.install_method == 'pipx':
        return PipxUpdater(tool, config, logger)

    elif tool.install_method == 'binary':
        return BinaryUpdater(tool, config, logger)

    elif tool.install_method == 'apt':
        return AptUpdater(tool, config, logger)

    elif tool.install_method == 'docker':
        return DockerUpdater(tool, config, logger)

    elif tool.install_method in ('git', 'git_python'):
        # Check if .git directory exists
        if (tool.path / '.git').exists():
            if tool.install_method == 'git_python':
                return GitPythonUpdater(tool, config, logger)
            else:
                return GitUpdater(tool, config, logger)
        else:
            # No .git - fall back to file replacement
            return FileReplacementUpdater(tool, config, logger)

    elif tool.install_method == 'file_replacement':
        return FileReplacementUpdater(tool, config, logger)

    elif tool.install_method == 'custom':
        return CustomUpdater(tool, config, logger)

    else:
        raise ValueError(f"Unknown install method: {tool.install_method}")
```

#### Example: Simple Tool (File Replacement)

```
/opt/azure_tools/o365spray/
├── o365spray.py          ← Download from GitHub raw
├── requirements.txt      ← Download from GitHub raw
└── README.md             ← Optional, can skip
```

Update process:
1. Backup `o365spray.py` and `requirements.txt`
2. Download new `o365spray.py` from `https://raw.githubusercontent.com/0xZDH/o365spray/main/o365spray.py`
3. Download new `requirements.txt` from `https://raw.githubusercontent.com/0xZDH/o365spray/main/requirements.txt`
4. Run `pip3 install -r requirements.txt --upgrade`
5. Verify tool works
6. If fails, restore backup

### 1.6 Tool Discovery on Live System

When `pwncloudos-sync` runs on an actual PwnCloudOS VM, it discovers tools by:

#### Discovery Algorithm

```python
def discover_tools() -> List[Tool]:
    """
    Discover all installed tools on the PwnCloudOS system.
    This runs on the actual VM, not the repository.
    """
    tools = []

    # 1. Scan /opt/ directories for git repositories
    OPT_DIRS = [
        '/opt/aws_tools',
        '/opt/azure_tools',
        '/opt/gcp_tools',
        '/opt/multi_cloud_tools',
        '/opt/ps_tools',
        '/opt/code_scanning',
        '/opt/cracking-tools',
    ]

    for opt_dir in OPT_DIRS:
        if not os.path.exists(opt_dir):
            continue

        for tool_name in os.listdir(opt_dir):
            tool_path = Path(opt_dir) / tool_name

            # Check if it's a git repository
            if (tool_path / '.git').exists():
                # Get remote URL to identify the GitHub repo
                remote_url = get_git_remote(tool_path)
                github_repo = parse_github_repo(remote_url)

                tools.append(Tool(
                    name=tool_name,
                    category=categorize_from_path(opt_dir),
                    install_method='git' if not has_requirements(tool_path) else 'git_python',
                    path=tool_path,
                    github_repo=github_repo,
                ))

    # 2. Query pipx for installed packages
    pipx_output = subprocess.check_output(['pipx', 'list', '--json'])
    pipx_data = json.loads(pipx_output)
    for pkg_name, pkg_info in pipx_data['venvs'].items():
        tools.append(Tool(
            name=pkg_name,
            category='system',
            install_method='pipx',
            path=Path(pkg_info['metadata']['main_package']['app_paths'][0]),
            pypi_name=pkg_name,
        ))

    # 3. Check for known binary tools
    BINARY_TOOLS = {
        '/home/pwnedlabs/go/bin/cloudfox': 'BishopFox/cloudfox',
        '/opt/azure_tools/azure_hound/azurehound': 'BloodHoundAD/AzureHound',
        '/usr/local/bin/steampipe': 'turbot/steampipe',
        '/usr/local/bin/powerpipe': 'turbot/powerpipe',
    }

    for binary_path, github_repo in BINARY_TOOLS.items():
        if os.path.exists(binary_path):
            tools.append(Tool(
                name=Path(binary_path).name,
                category='multi_cloud',
                install_method='binary',
                path=Path(binary_path),
                github_repo=github_repo,
            ))

    return tools


def get_git_remote(repo_path: Path) -> str:
    """Get the origin remote URL from a git repository."""
    result = subprocess.run(
        ['git', '-C', str(repo_path), 'remote', 'get-url', 'origin'],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def parse_github_repo(url: str) -> str:
    """
    Parse GitHub repo from various URL formats:
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo
    """
    # Handle HTTPS URLs
    if 'github.com/' in url:
        parts = url.split('github.com/')[-1]
        return parts.replace('.git', '').strip('/')

    # Handle SSH URLs
    if 'git@github.com:' in url:
        parts = url.split('git@github.com:')[-1]
        return parts.replace('.git', '').strip('/')

    return url
```

### 1.5 Complete Tool-to-GitHub Mapping

This is the authoritative mapping of every tool to its GitHub repository. Use this for updates.

#### Git Clone Tools (Update via `git pull`)

| Tool Directory | GitHub Repository | Has requirements.txt | Post-Pull Action |
|----------------|-------------------|---------------------|------------------|
| `/opt/aws_tools/AWeSomeUserFinder` | `dievus/AWeSomeUserFinder` | Yes | `pip install -r requirements.txt` |
| `/opt/aws_tools/github-oidc-checker` | `Rezonate-io/github-oidc-checker` | Yes | `pip install -r requirements.txt` |
| `/opt/azure_tools/AzSubEnum` | `yuyudhn/AzSubEnum` | Yes | `pip install -r requirements.txt` |
| `/opt/azure_tools/basicblobfinder` | `joswr1ght/basicblobfinder` | No | None |
| `/opt/azure_tools/exfil_exchange_mail` | `rootsecdev/Azure-Red-Team` | No | None |
| `/opt/azure_tools/o365enum` | `gremwell/o365enum` | Yes | `pip install -r requirements.txt` |
| `/opt/azure_tools/o365spray` | `0xZDH/o365spray` | Yes | `pip install -r requirements.txt` |
| `/opt/azure_tools/Oh365UserFinder` | `dievus/Oh365UserFinder` | Yes | `pip install -r requirements.txt` |
| `/opt/azure_tools/Omnispray` | `0xZDH/Omnispray` | Yes | `pip install -r requirements.txt` |
| `/opt/gcp_tools/automated-cloud-misconfiguration-testing` | `pwnedlabs/automated-cloud-misconfiguration-testing` | No | None |
| `/opt/gcp_tools/gcp-permissions-checker` | `egre55/gcp-permissions-checker` | Yes | `pip install -r requirements.txt` |
| `/opt/gcp_tools/gcp_scanner` | `google/gcp_scanner` | Yes | `pip install -r requirements.txt` |
| `/opt/gcp_tools/google-workspace-enum` | `pwnedlabs/google-workspace-enum` | No | None |
| `/opt/gcp_tools/iam-policy-visualize` | `hac01/iam-policy-visualize` | Yes | `pip install -r requirements.txt` |
| `/opt/gcp_tools/username-anarchy` | `urbanadventurer/username-anarchy` | No | None (Ruby) |
| `/opt/ps_tools/AADInternals` | `Gerenios/AADInternals` | No | None (PowerShell) |
| `/opt/ps_tools/GraphRunner` | `dafthack/GraphRunner` | No | None (PowerShell) |
| `/opt/ps_tools/invoke_modules` | `PowerShellMafia/PowerSploit` | No | None (PowerShell) |
| `/opt/ps_tools/MFASweep` | `dafthack/MFASweep` | No | None (PowerShell) |
| `/opt/ps_tools/TokenTacticsV2` | `f-bader/TokenTacticsV2` | No | None (PowerShell) |
| `/opt/code_scanning/git-secrets` | `awslabs/git-secrets` | No | `make install PREFIX=/usr/local` |
| `/opt/cracking-tools/john` | `openwall/john` | No | `cd src && ./configure && make` |

#### Binary Download Tools (Update via GitHub Releases API)

| Tool | GitHub Repo | Binary Location | Version Command |
|------|-------------|-----------------|-----------------|
| cloudfox | `BishopFox/cloudfox` | `/home/pwnedlabs/go/bin/cloudfox` | `cloudfox --version` |
| azurehound | `BloodHoundAD/AzureHound` | `/opt/azure_tools/azure_hound/azurehound` | `azurehound --version` |
| aws_enumerator | `shabarkin/aws-enumerator` | `/opt/aws_tools/aws_enumerator/aws-enumerator` | N/A |
| steampipe | `turbot/steampipe` | `/usr/local/bin/steampipe` | `steampipe --version` |
| powerpipe | `turbot/powerpipe` | `/usr/local/bin/powerpipe` | `powerpipe --version` |

#### pipx Tools (Update via `pipx upgrade`)

| PyPI Package | Command Name | Version Command | GitHub Repo (reference) |
|--------------|--------------|-----------------|------------------------|
| `azure-cli` | `az` | `az --version` | Microsoft (not GitHub) |
| `iamgraph` | `iamgraph` | `iamgraph --version` | `WithSecureLabs/IAMGraph` |
| `impacket` | Multiple | N/A | `fortra/impacket` |
| `pacu` | `pacu` | `pacu --version` | `RhinoSecurityLabs/pacu` |
| `principalmapper` | `pmapper` | `pmapper --version` | `nccgroup/PMapper` |
| `prowler` | `prowler` | `prowler --version` | `prowler-cloud/prowler` |
| `roadtools` | `roadrecon` | `roadrecon --version` | `dirkjanm/ROADtools` |
| `s3-account-search` | `s3-account-search` | N/A | `WeAreCloudar/s3-account-search` |
| `scoutsuite` | `scout` | `scout --version` | `nccgroup/ScoutSuite` |
| `seamlesspass` | `seamlesspass` | `seamlesspass --version` | `Malcrove/SeamlessPass` |
| `trufflehog` | `trufflehog` | `trufflehog --version` | `trufflesecurity/trufflehog` |
| `sprayshark` | `sprayshark` | `sprayshark --version` | `helviojunior/sprayshark` |
| `s3scanner` | `s3scanner` | `s3scanner --version` | `sa7mon/S3Scanner` |

### 1.5 Version Check Strategy

| Update Method | Current Version | Latest Version |
|---------------|-----------------|----------------|
| **git clone** | `git rev-parse --short HEAD` | `git rev-parse --short origin/HEAD` (after fetch) |
| **pipx** | `pipx list --json \| jq '.venvs.{pkg}.metadata.main_package.version'` | PyPI API: `https://pypi.org/pypi/{package}/json` |
| **binary** | Run with `--version` flag, parse output | GitHub API: `https://api.github.com/repos/{owner}/{repo}/releases/latest` |
| **apt** | `dpkg -s {package} \| grep Version` | `apt-cache policy {package}` |
| **docker** | `docker images --format '{{.Tag}}'` | Docker Hub API |

### 1.6 Architecture Detection Matrix

| Binary Source | AMD64 Asset Pattern | ARM64 Asset Pattern |
| cloudfox | `cloudfox_*_linux_amd64.tar.gz` | `cloudfox_*_linux_arm64.tar.gz` |
| azure_hound | `azurehound-linux-amd64.zip` | `azurehound-linux-arm64.zip` |
| aws_enumerator | `aws-enumerator_linux_amd64` | `aws-enumerator_linux_arm64` |
| steampipe | `steampipe_linux_amd64.tar.gz` | `steampipe_linux_arm64.tar.gz` |
| powerpipe | `powerpipe_linux_amd64.tar.gz` | `powerpipe_linux_arm64.tar.gz` |

---

## 2. Repository Architecture

### 2.1 Directory Structure

```
pwncloudos-sync/
├── README.md                     # User documentation
├── LICENSE                       # MIT License
├── pwncloudos-sync               # Main executable (bash wrapper)
├── setup.sh                      # First-time setup script
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project metadata
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   ├── cli.py                    # CLI argument parsing
│   ├── config.py                 # Configuration management
│   ├── logger.py                 # Logging infrastructure
│   ├── utils.py                  # Utility functions
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── arch.py               # Architecture detection
│   │   ├── connectivity.py       # Network connectivity checks
│   │   ├── privileges.py         # Sudo/privilege management
│   │   ├── state.py              # State tracking (versions, timestamps)
│   │   ├── rollback.py           # Rollback engine
│   │   └── safeguards.py         # Path protection & safety checks (CRITICAL)
│   │
│   ├── updaters/
│   │   ├── __init__.py
│   │   ├── base.py               # Base updater class (abstract)
│   │   ├── apt_updater.py        # apt package updater
│   │   ├── pipx_updater.py       # pipx package updater
│   │   ├── git_updater.py        # git repository updater
│   │   ├── git_python_updater.py # git + pip requirements updater
│   │   ├── git_compile_updater.py# git + make/compile updater
│   │   ├── file_replacement_updater.py  # Download .py + requirements.txt (lightweight)
│   │   ├── binary_updater.py     # GitHub releases binary updater
│   │   ├── docker_updater.py     # Docker image updater
│   │   └── custom_updater.py     # Custom installer scripts
│   │
│   └── tools/
│       ├── __init__.py
│       └── registry.py           # Tool registry loader
│
├── manifests/
│   ├── tools.yaml                # Master tool manifest
│   ├── arch_mappings.yaml        # Architecture binary patterns
│   └── custom_handlers.yaml      # Custom update scripts
│
├── scripts/
│   ├── update_steampipe.sh       # Steampipe custom updater
│   ├── update_powerpipe.sh       # Powerpipe custom updater
│   ├── update_caido.sh           # CAIDO custom updater
│   ├── update_burpsuite.sh       # BurpSuite custom updater
│   └── update_john.sh            # John the Ripper compile script
│
├── tests/
│   ├── __init__.py
│   ├── test_arch.py
│   ├── test_updaters.py
│   ├── test_rollback.py
│   └── fixtures/
│
├── logs/                         # Runtime logs (gitignored)
│   └── .gitkeep
│
└── state/                        # State files (gitignored)
    └── .gitkeep
```

### 2.2 Core Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.10+ | Pre-installed on Debian 12, rich ecosystem |
| CLI Framework | argparse | No external deps, stdlib |
| Config Format | YAML | Human-readable, good for manifests |
| HTTP Client | requests | Simple, reliable |
| Logging | stdlib logging | No external deps |
| Process Exec | subprocess | Stdlib, fine-grained control |
| State Storage | JSON files | Simple, no DB required |

### 2.3 External Dependencies (Minimal)

```
# requirements.txt
requests>=2.28.0
PyYAML>=6.0
packaging>=21.0
```

---

## 3. Phase 1: Core Infrastructure

### 3.1 Architecture Detection Module

**File:** `src/core/arch.py`

**Sub-steps:**

1.1. Create `detect_architecture()` function:
   - Read `/proc/cpuinfo` for CPU architecture
   - Use `platform.machine()` as primary method
   - Map values: `x86_64` → `amd64`, `aarch64` → `arm64`
   - Cache result for session

1.2. Create `get_binary_asset_pattern(tool_name: str, arch: str)` function:
   - Load patterns from `manifests/arch_mappings.yaml`
   - Return the download URL pattern for given tool and architecture
   - Raise `UnsupportedArchitectureError` if tool doesn't support current arch

1.3. Create `validate_binary_for_arch(binary_path: str)` function:
   - Run `file <binary>` to verify ELF architecture
   - Return True if binary matches system architecture
   - Used as post-download verification

**Implementation Notes:**
- Must handle edge case where `/proc/cpuinfo` is unavailable
- Fallback chain: `platform.machine()` → `uname -m` → error

```python
# Example architecture detection logic
def detect_architecture() -> str:
    machine = platform.machine().lower()
    mapping = {
        'x86_64': 'amd64',
        'amd64': 'amd64',
        'aarch64': 'arm64',
        'arm64': 'arm64',
    }
    if machine not in mapping:
        raise UnsupportedArchitectureError(f"Unsupported: {machine}")
    return mapping[machine]
```

### 3.2 Network Connectivity Module

**File:** `src/core/connectivity.py`

**Sub-steps:**

1.4. Create `check_internet_connectivity()` function:
   - Test connectivity to multiple endpoints (redundancy)
   - Endpoints: `https://api.github.com`, `https://pypi.org`, `https://deb.debian.org`
   - Timeout: 5 seconds per endpoint
   - Return `True` if at least one succeeds

1.5. Create `check_github_api_rate_limit()` function:
   - Query `https://api.github.com/rate_limit`
   - Return remaining requests and reset time
   - Warn user if rate limit is low (<100 remaining)

1.6. Create `test_source_connectivity(source: str)` function:
   - Test connectivity to specific source (GitHub repo, PyPI package)
   - Used before attempting updates
   - Return latency and availability status

**Implementation Notes:**
- All network operations must have timeouts
- Handle DNS resolution failures gracefully
- Support proxy configuration via environment variables

### 3.3 Privilege Management Module

**File:** `src/core/privileges.py`

**Sub-steps:**

1.7. Create `check_sudo_available()` function:
   - Test if `sudo` is available and user has sudo privileges
   - Run `sudo -n true` to check passwordless sudo
   - If not passwordless, prompt user for sudo password upfront

1.8. Create `run_as_root(command: List[str])` function:
   - Execute command with sudo if needed
   - Handle password prompts gracefully
   - Capture stdout/stderr

1.9. Create `get_required_privileges(tool: Tool)` function:
   - Determine if tool update requires root
   - apt updates → require root
   - pipx updates → user-level
   - /opt/ writes → require root

**Implementation Notes:**
- Never store sudo password
- Use `SUDO_ASKPASS` for GUI password prompts if available
- Fail fast if sudo is required but unavailable

### 3.4 Configuration Module

**File:** `src/config.py`

**Sub-steps:**

1.10. Define `Config` dataclass:
```python
@dataclass
class Config:
    verbose: bool = False
    dry_run: bool = False
    parallel: bool = False
    max_workers: int = 4
    log_file: Path = Path("logs/pwncloudos-sync.log")
    state_dir: Path = Path("state/")
    skip_tools: List[str] = field(default_factory=list)
    only_tools: List[str] = field(default_factory=list)
    category: Optional[str] = None
    force: bool = False
    no_rollback: bool = False
```

1.11. Create `load_config(args)` function:
   - Merge CLI arguments with config file
   - Validate configuration
   - Return Config object

1.12. Create config file support:
   - Look for `~/.config/pwncloudos-sync/config.yaml`
   - Allow overriding defaults

### 3.5 Safeguards Module (CRITICAL)

**File:** `src/core/safeguards.py`

This module provides hard-coded protection to ensure launcher files and other protected paths are NEVER modified.

**Sub-steps:**

1.13. Define protected path patterns:
```python
# THESE PATHS MUST NEVER BE MODIFIED BY THE UPDATER
PROTECTED_PATHS = [
    # Launcher scripts - documentation only, not actual tools
    "**/docs/configs/launchers/**/*.sh",
    "**/docs/configs/launchers/**/*.desktop",

    # Shell configurations - user customizations
    "**/docs/configs/shell/**",

    # Desktop environment configs - user preferences
    "**/docs/configs/xfce/**",
    "**/docs/configs/menulibre/**",

    # Any .desktop files system-wide
    "/usr/share/applications/*.desktop",
    "~/.local/share/applications/*.desktop",
]

# THESE ARE THE ONLY PATHS THE UPDATER CAN MODIFY
ALLOWED_UPDATE_PATHS = [
    "/opt/aws_tools/*",
    "/opt/azure_tools/*",
    "/opt/gcp_tools/*",
    "/opt/multi_cloud_tools/*",
    "/opt/ps_tools/*",
    "/opt/code_scanning/*",
    "/opt/cracking-tools/*",
    "~/.local/pipx/venvs/*",
    "/usr/local/bin/steampipe",
    "/usr/local/bin/powerpipe",
    "~/go/bin/*",
]
```

1.14. Create `is_path_protected(path: Path)` function:
```python
def is_path_protected(path: Path) -> bool:
    """
    Check if a path is protected from modification.
    Returns True if the path matches any protected pattern.

    CRITICAL: This function must ALWAYS err on the side of protection.
    If in doubt, the path is protected.
    """
    path_str = str(path.resolve())

    # Check against protected patterns
    for pattern in PROTECTED_PATHS:
        if fnmatch.fnmatch(path_str, pattern):
            return True

    # Additional hard-coded checks
    if 'launcher' in path_str.lower():
        return True
    if path_str.endswith('.desktop'):
        return True
    if '/docs/configs/' in path_str:
        return True

    return False
```

1.15. Create `validate_update_target(path: Path)` function:
```python
def validate_update_target(path: Path) -> None:
    """
    Validate that a path is safe to update.
    Raises ProtectedPathError if the path is protected.

    This function MUST be called before ANY file modification.
    """
    if is_path_protected(path):
        raise ProtectedPathError(
            f"REFUSED: Cannot modify protected path: {path}\n"
            f"This path contains launcher scripts or configuration files.\n"
            f"Only tool directories in /opt/ can be updated."
        )

    # Verify path is in allowed list
    path_str = str(path.resolve())
    allowed = any(
        fnmatch.fnmatch(path_str, pattern)
        for pattern in ALLOWED_UPDATE_PATHS
    )

    if not allowed:
        raise UnauthorizedPathError(
            f"REFUSED: Path not in allowed update locations: {path}\n"
            f"Allowed locations: /opt/*_tools/, ~/.local/pipx/, /usr/local/bin/"
        )
```

1.16. Create decorator for all update operations:
```python
def protected_operation(func):
    """
    Decorator that ensures no protected paths are modified.
    Wraps any function that modifies files.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Extract path from args/kwargs
        path = kwargs.get('path') or (args[0] if args else None)

        if path:
            validate_update_target(Path(path))

        return func(self, *args, **kwargs)

    return wrapper
```

**Implementation Notes:**
- This module is the FIRST line of defense
- Every updater MUST use `validate_update_target()` before any file operation
- The `protected_operation` decorator should wrap all file-modifying methods
- Protected path checks should be logged for audit trail
- If any doubt exists, REFUSE the operation

---

## 4. Phase 2: Update Engine Implementation

### 4.1 Tool Registry

**File:** `src/tools/registry.py`

**Sub-steps:**

2.1. Define `Tool` dataclass:
```python
@dataclass
class Tool:
    name: str
    category: str
    install_method: str  # pipx, git, git_python, binary, apt, docker, custom
    path: Path
    source_url: str
    pypi_name: Optional[str] = None
    apt_package: Optional[str] = None
    github_repo: Optional[str] = None  # owner/repo format
    arch_support: List[str] = field(default_factory=lambda: ['amd64', 'arm64'])
    requires_compile: bool = False
    custom_handler: Optional[str] = None
    version_command: Optional[str] = None
    enabled: bool = True
```

2.2. Create `load_tools_manifest()` function:
   - Load `manifests/tools.yaml`
   - Parse into list of Tool objects
   - Validate all required fields

2.3. Create `get_tools_for_category(category: str)` function:
   - Filter tools by category
   - Categories: aws, azure, gcp, multi_cloud, ps_tools, code_scanning, cracking, system

2.4. Create `get_tool_by_name(name: str)` function:
   - Look up tool by exact name
   - Return None if not found

### 4.2 Base Updater Class

**File:** `src/updaters/base.py`

**Sub-steps:**

2.5. Define abstract `BaseUpdater` class:
```python
class BaseUpdater(ABC):
    def __init__(self, tool: Tool, config: Config, logger: Logger):
        self.tool = tool
        self.config = config
        self.logger = logger
        self.rollback_data: Optional[RollbackData] = None

    @abstractmethod
    def get_current_version(self) -> Optional[str]:
        """Get currently installed version"""
        pass

    @abstractmethod
    def get_latest_version(self) -> Optional[str]:
        """Get latest available version from source"""
        pass

    @abstractmethod
    def needs_update(self) -> bool:
        """Check if update is needed"""
        pass

    @abstractmethod
    def create_backup(self) -> RollbackData:
        """Create backup before update"""
        pass

    @abstractmethod
    def perform_update(self) -> UpdateResult:
        """Execute the update"""
        pass

    @abstractmethod
    def verify_update(self) -> bool:
        """Verify update succeeded"""
        pass

    def rollback(self) -> bool:
        """Restore from backup"""
        pass
```

2.6. Define `UpdateResult` dataclass:
```python
@dataclass
class UpdateResult:
    success: bool
    tool_name: str
    old_version: Optional[str]
    new_version: Optional[str]
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    skipped: bool = False
    skip_reason: Optional[str] = None
```

2.7. Define `RollbackData` dataclass:
```python
@dataclass
class RollbackData:
    tool_name: str
    backup_path: Path
    original_version: str
    backup_timestamp: datetime
    backup_type: str  # 'directory', 'file', 'state'
```

### 4.3 State Management

**File:** `src/core/state.py`

**Sub-steps:**

2.8. Create `StateManager` class:
```python
class StateManager:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_file = state_dir / "tool_versions.json"
        self._state: Dict[str, ToolState] = {}

    def load(self) -> None:
        """Load state from disk"""

    def save(self) -> None:
        """Persist state to disk"""

    def get_tool_state(self, tool_name: str) -> Optional[ToolState]:
        """Get state for specific tool"""

    def update_tool_state(self, tool_name: str, version: str,
                          timestamp: datetime) -> None:
        """Update tool state after successful update"""

    def get_last_update_time(self, tool_name: str) -> Optional[datetime]:
        """Get last update timestamp for tool"""
```

2.9. Define `ToolState` dataclass:
```python
@dataclass
class ToolState:
    name: str
    installed_version: str
    last_update: datetime
    last_check: datetime
    update_count: int
    last_error: Optional[str] = None
```

---

## 5. Phase 3: Per-Tool Update Handlers

### 5.1 pipx Updater

**File:** `src/updaters/pipx_updater.py`

**Sub-steps:**

3.1. Implement `PipxUpdater(BaseUpdater)`:

```python
class PipxUpdater(BaseUpdater):
    def get_current_version(self) -> Optional[str]:
        # Run: pipx list --json
        # Parse JSON output for tool's version
        pass

    def get_latest_version(self) -> Optional[str]:
        # Query PyPI JSON API: https://pypi.org/pypi/{package}/json
        # Extract latest version from response
        pass

    def needs_update(self) -> bool:
        current = self.get_current_version()
        latest = self.get_latest_version()
        return packaging.version.parse(current) < packaging.version.parse(latest)

    def create_backup(self) -> RollbackData:
        # pipx stores in ~/.local/pipx/venvs/{package}
        # Create tarball of venv directory
        pass

    def perform_update(self) -> UpdateResult:
        # Run: pipx upgrade {package}
        # Capture output, check return code
        pass

    def verify_update(self) -> bool:
        # Run version command if available
        # Compare with expected version
        pass
```

**Tools using this updater:**
- azure-cli, iamgraph, impacket, pacu, pmapper, prowler, roadtools, s3-account-search, scoutsuite, seamlesspass, trufflehog, sprayshark, s3scanner

### 5.2 Git Repository Updater

**File:** `src/updaters/git_updater.py`

**Sub-steps:**

3.2. Implement `GitUpdater(BaseUpdater)`:

```python
class GitUpdater(BaseUpdater):
    def get_current_version(self) -> Optional[str]:
        # Run: git -C {path} rev-parse HEAD
        # Return commit hash (short form)
        pass

    def get_latest_version(self) -> Optional[str]:
        # Run: git -C {path} fetch --dry-run
        # Run: git -C {path} rev-parse origin/HEAD
        # Return latest commit hash
        pass

    def needs_update(self) -> bool:
        # Compare current HEAD with origin/HEAD
        # Handle case where remote has been force-pushed
        pass

    def create_backup(self) -> RollbackData:
        # Record current commit hash
        # No file backup needed - git can restore
        pass

    def perform_update(self) -> UpdateResult:
        # Run: git -C {path} fetch origin
        # Run: git -C {path} reset --hard origin/HEAD
        # Note: Use reset --hard to handle modified files
        pass

    def verify_update(self) -> bool:
        # Verify new commit matches expected
        pass

    def rollback(self) -> bool:
        # Run: git -C {path} reset --hard {original_commit}
        pass
```

**Tools using this updater:**
- AADInternals, GraphRunner, MFASweep, TokenTacticsV2, invoke_modules, username-anarchy

### 5.3 Git + Python Dependencies Updater

**File:** `src/updaters/git_python_updater.py`

**Sub-steps:**

3.3. Implement `GitPythonUpdater(GitUpdater)`:

```python
class GitPythonUpdater(GitUpdater):
    def perform_update(self) -> UpdateResult:
        # First: git pull (via parent class)
        git_result = super().perform_update()
        if not git_result.success:
            return git_result

        # Check for requirements.txt
        req_file = self.tool.path / "requirements.txt"
        if req_file.exists():
            # Run: pip install -r requirements.txt --upgrade
            # Use tool's venv if exists, else system pip
            pass

        # Check for setup.py or pyproject.toml
        if (self.tool.path / "setup.py").exists():
            # Run: pip install -e .
            pass

        return UpdateResult(success=True, ...)

    def create_backup(self) -> RollbackData:
        # Backup both git state AND pip freeze output
        # Save: pip freeze > backup_requirements.txt
        pass

    def rollback(self) -> bool:
        # Restore git state
        # Restore pip packages from frozen requirements
        pass
```

**Tools using this updater:**
- AWeSomeUserFinder, github-oidc-checker, AzSubEnum, basicblobfinder, o365enum, o365spray, Oh365UserFinder, Omnispray, gcp-permissions-checker, gcp_scanner, google-workspace-enum, iam-policy-visualize, exfil_exchange_mail

### 5.3.1 File Replacement Updater (Lightweight Alternative)

**File:** `src/updaters/file_replacement_updater.py`

This updater is for simple Python tools where we only need to replace the main `.py` file and `requirements.txt` without requiring a full git repository.

**Sub-steps:**

3.3.1. Implement `FileReplacementUpdater(BaseUpdater)`:

```python
class FileReplacementUpdater(BaseUpdater):
    """
    Lightweight updater that downloads and replaces specific files
    from GitHub without requiring a git clone.

    Best for simple tools with:
    - Single main Python script
    - requirements.txt
    - No complex module structure
    """

    def __init__(self, tool: Tool, config: Config, logger: Logger):
        super().__init__(tool, config, logger)
        self.files_to_update = ['requirements.txt']
        self.main_script = self._detect_main_script()
        if self.main_script:
            self.files_to_update.insert(0, self.main_script.name)

    def _detect_main_script(self) -> Optional[Path]:
        """Detect the main Python script."""
        tool_name = self.tool.path.name.lower()

        # Common patterns for main script
        patterns = [
            f"{tool_name}.py",
            f"{tool_name.replace('-', '_')}.py",
            "main.py",
            "__main__.py",
        ]

        for pattern in patterns:
            candidate = self.tool.path / pattern
            if candidate.exists():
                return candidate

        # Fallback: single .py file
        py_files = [f for f in self.tool.path.glob("*.py")
                    if not f.name.startswith('_')]
        if len(py_files) == 1:
            return py_files[0]

        return None

    def _get_raw_url(self, filename: str) -> str:
        """Get raw GitHub URL for a file."""
        branch = self._get_default_branch()
        return f"https://raw.githubusercontent.com/{self.tool.github_repo}/{branch}/{filename}"

    def _get_default_branch(self) -> str:
        """Get default branch from GitHub API."""
        try:
            url = f"https://api.github.com/repos/{self.tool.github_repo}"
            response = requests.get(url, timeout=10)
            if response.ok:
                return response.json().get('default_branch', 'main')
        except:
            pass
        return 'main'

    def _get_latest_commit(self) -> str:
        """Get latest commit SHA from GitHub API."""
        try:
            branch = self._get_default_branch()
            url = f"https://api.github.com/repos/{self.tool.github_repo}/commits/{branch}"
            response = requests.get(url, timeout=10)
            if response.ok:
                return response.json()['sha'][:7]
        except:
            pass
        return "unknown"

    def get_current_version(self) -> Optional[str]:
        """Get current version from stored state or file hash."""
        # Check state file for stored version
        state = self.state_manager.get_tool_state(self.tool.name)
        if state:
            return state.installed_version

        # Fallback: hash of main script
        if self.main_script and self.main_script.exists():
            content = self.main_script.read_bytes()
            return hashlib.md5(content).hexdigest()[:7]

        return None

    def get_latest_version(self) -> Optional[str]:
        """Get latest version (commit SHA) from GitHub."""
        return self._get_latest_commit()

    def needs_update(self) -> bool:
        """Check if files have changed on GitHub."""
        current = self.get_current_version()
        latest = self.get_latest_version()

        if not current or not latest:
            return True  # If we can't determine, try to update

        return current != latest

    def create_backup(self) -> RollbackData:
        """Backup files before replacement."""
        backup_dir = Path(f"/tmp/pwncloudos-sync-backup/{self.tool.name}")
        backup_dir.mkdir(parents=True, exist_ok=True)

        for filename in self.files_to_update:
            source = self.tool.path / filename
            if source.exists():
                shutil.copy2(source, backup_dir / filename)

        return RollbackData(
            tool_name=self.tool.name,
            backup_path=backup_dir,
            original_version=self.get_current_version(),
            backup_timestamp=datetime.now(),
            backup_type='file_replacement',
        )

    def perform_update(self) -> UpdateResult:
        """Download and replace files from GitHub."""
        old_version = self.get_current_version()

        for filename in self.files_to_update:
            url = self._get_raw_url(filename)

            try:
                response = requests.get(url, timeout=30)

                if response.status_code == 404:
                    self.logger.debug(f"File not found on GitHub: {filename}")
                    continue

                if not response.ok:
                    return UpdateResult(
                        success=False,
                        tool_name=self.tool.name,
                        error_message=f"Failed to download {filename}: HTTP {response.status_code}"
                    )

                # Write new content
                target = self.tool.path / filename
                target.write_text(response.text)
                self.logger.info(f"Updated: {filename}")

            except requests.RequestException as e:
                return UpdateResult(
                    success=False,
                    tool_name=self.tool.name,
                    error_message=f"Network error downloading {filename}: {e}"
                )

        # Update Python dependencies
        req_file = self.tool.path / "requirements.txt"
        if req_file.exists():
            result = subprocess.run(
                ["pip3", "install", "-r", str(req_file), "--upgrade", "--quiet"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                self.logger.warning(f"pip install warning: {result.stderr}")

        return UpdateResult(
            success=True,
            tool_name=self.tool.name,
            old_version=old_version,
            new_version=self.get_latest_version(),
        )

    def verify_update(self) -> bool:
        """Verify tool still works after update."""
        if not self.main_script:
            return True

        # Try running with --help or -h
        try:
            result = subprocess.run(
                ["python3", str(self.main_script), "--help"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def rollback(self) -> bool:
        """Restore files from backup."""
        if not self.rollback_data:
            return False

        backup_dir = self.rollback_data.backup_path
        for filename in self.files_to_update:
            backup_file = backup_dir / filename
            if backup_file.exists():
                shutil.copy2(backup_file, self.tool.path / filename)

        return True
```

**Tools using this updater (simple Python scripts):**
- o365spray (single o365spray.py)
- Oh365UserFinder (single script)
- AWeSomeUserFinder (single script)
- AzSubEnum (single script)
- basicblobfinder (single script)
- o365enum (single script)
- gcp-permissions-checker (single script)

**When to use File Replacement vs Git Pull:**

| Criteria | File Replacement | Git Pull |
|----------|------------------|----------|
| Tool has single .py file | ✓ Use this | ✗ Overkill |
| Tool has multiple modules | ✗ May miss files | ✓ Use this |
| Tool has .git directory | Either works | ✓ Preferred |
| Tool was manually downloaded | ✓ Only option | ✗ No .git |
| Need to track file renames/deletes | ✗ Won't catch | ✓ Handles this |

### 5.4 Git + Compile Updater

**File:** `src/updaters/git_compile_updater.py`

**Sub-steps:**

3.4. Implement `GitCompileUpdater(GitUpdater)`:

```python
class GitCompileUpdater(GitUpdater):
    def perform_update(self) -> UpdateResult:
        # First: git pull
        git_result = super().perform_update()
        if not git_result.success:
            return git_result

        # Run custom compile script
        # For John: cd src && ./configure && make -s clean && make -sj4
        compile_script = self.get_compile_script()
        result = subprocess.run(compile_script, shell=True,
                               cwd=self.tool.path, capture_output=True)

        if result.returncode != 0:
            return UpdateResult(success=False,
                              error_message=result.stderr.decode())

        return UpdateResult(success=True, ...)

    def create_backup(self) -> RollbackData:
        # Backup entire directory (compiled binaries included)
        # This is necessary because recompilation may fail
        backup_path = create_tarball(self.tool.path)
        return RollbackData(backup_path=backup_path, ...)

    def get_compile_script(self) -> str:
        # Load from manifests/custom_handlers.yaml
        pass
```

**Tools using this updater:**
- john (John the Ripper)
- hashcat (if compiled from source)

### 5.5 Binary Releases Updater

**File:** `src/updaters/binary_updater.py`

**Sub-steps:**

3.5. Implement `BinaryUpdater(BaseUpdater)`:

```python
class BinaryUpdater(BaseUpdater):
    def __init__(self, ...):
        super().__init__(...)
        self.github_api = GitHubAPI()

    def get_current_version(self) -> Optional[str]:
        # Run binary with --version flag
        # Parse version from output
        # Handle case where --version is -v or version subcommand
        pass

    def get_latest_version(self) -> Optional[str]:
        # Query GitHub Releases API
        # GET https://api.github.com/repos/{owner}/{repo}/releases/latest
        # Parse tag_name (strip 'v' prefix if present)
        pass

    def needs_update(self) -> bool:
        current = self.get_current_version()
        latest = self.get_latest_version()
        # Use packaging.version for proper semver comparison
        pass

    def get_download_url(self) -> str:
        # Get architecture
        arch = detect_architecture()
        # Load asset pattern from arch_mappings.yaml
        pattern = get_binary_asset_pattern(self.tool.name, arch)
        # Query release assets, find matching asset
        pass

    def create_backup(self) -> RollbackData:
        # Copy existing binary to backup location
        backup_path = self.tool.path.with_suffix('.backup')
        shutil.copy2(self.tool.path, backup_path)
        return RollbackData(backup_path=backup_path, ...)

    def perform_update(self) -> UpdateResult:
        # Get download URL for current architecture
        url = self.get_download_url()

        # Download to temp location
        temp_path = download_file(url)

        # Verify architecture
        if not validate_binary_for_arch(temp_path):
            raise ArchitectureMismatchError()

        # Extract if archived (tar.gz, zip)
        if is_archive(temp_path):
            extract_archive(temp_path, self.tool.path.parent)
        else:
            # Make executable and move
            os.chmod(temp_path, 0o755)
            shutil.move(temp_path, self.tool.path)

        return UpdateResult(success=True, ...)

    def verify_update(self) -> bool:
        # Run --version and compare with expected
        pass

    def rollback(self) -> bool:
        # Restore from backup
        shutil.move(self.rollback_data.backup_path, self.tool.path)
        return True
```

**Tools using this updater:**
- cloudfox, azure_hound, aws_enumerator

### 5.6 apt Package Updater

**File:** `src/updaters/apt_updater.py`

**Sub-steps:**

3.6. Implement `AptUpdater(BaseUpdater)`:

```python
class AptUpdater(BaseUpdater):
    def get_current_version(self) -> Optional[str]:
        # Run: dpkg -s {package} | grep Version
        pass

    def get_latest_version(self) -> Optional[str]:
        # Run: apt-cache policy {package}
        # Parse "Candidate" version
        pass

    def needs_update(self) -> bool:
        # Run: apt list --upgradable 2>/dev/null | grep {package}
        pass

    def create_backup(self) -> RollbackData:
        # Record current version
        # apt can downgrade if needed
        current = self.get_current_version()
        return RollbackData(original_version=current, ...)

    def perform_update(self) -> UpdateResult:
        # Run: sudo apt-get update (cache refresh)
        # Run: sudo apt-get install --only-upgrade {package} -y
        pass

    def rollback(self) -> bool:
        # Run: sudo apt-get install {package}={original_version}
        pass
```

**Tools using this updater:**
- awscli, chromium, firefox, flameshot, hashcat (if apt), git-secrets (if apt)

### 5.7 Docker Image Updater

**File:** `src/updaters/docker_updater.py`

**Sub-steps:**

3.7. Implement `DockerUpdater(BaseUpdater)`:

```python
class DockerUpdater(BaseUpdater):
    def get_current_version(self) -> Optional[str]:
        # Parse docker-compose.yml for image tag
        # Or: docker images --format '{{.Tag}}' {image}
        pass

    def get_latest_version(self) -> Optional[str]:
        # Query Docker Hub API for latest tag
        # Or use fixed tag from manifest
        pass

    def needs_update(self) -> bool:
        # Compare image digests
        # docker pull --dry-run would be ideal but doesn't exist
        pass

    def create_backup(self) -> RollbackData:
        # Record current image digest
        # docker inspect --format='{{.RepoDigests}}' {image}
        pass

    def perform_update(self) -> UpdateResult:
        # Run: docker-compose -f {compose_file} pull
        # Run: docker-compose -f {compose_file} up -d
        pass
```

**Tools using this updater:**
- bloodhound

### 5.8 Custom Installer Updater

**File:** `src/updaters/custom_updater.py`

**Sub-steps:**

3.8. Implement `CustomUpdater(BaseUpdater)`:

```python
class CustomUpdater(BaseUpdater):
    def __init__(self, ...):
        super().__init__(...)
        self.script_path = Path(f"scripts/update_{self.tool.name}.sh")

    def get_current_version(self) -> Optional[str]:
        # Tool-specific version detection
        # Defined in manifest or script
        pass

    def get_latest_version(self) -> Optional[str]:
        # Query tool's official API or page
        pass

    def perform_update(self) -> UpdateResult:
        # Execute custom update script
        # Scripts must be idempotent
        result = subprocess.run(
            ['/bin/bash', self.script_path],
            capture_output=True,
            env={**os.environ, 'ARCH': detect_architecture()}
        )
        pass
```

**Custom scripts to create:**

**scripts/update_steampipe.sh:**
```bash
#!/bin/bash
set -e
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH="linux_amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH="linux_arm64"
fi
curl -fsSL https://raw.githubusercontent.com/turbot/steampipe/main/install.sh | sh
```

**scripts/update_powerpipe.sh:**
```bash
#!/bin/bash
set -e
ARCH=$(uname -m)
curl -fsSL https://raw.githubusercontent.com/turbot/powerpipe/main/install.sh | sh
```

**scripts/update_john.sh:**
```bash
#!/bin/bash
set -e
cd /opt/cracking-tools/john/src
git pull origin bleeding-jumbo
./configure
make -s clean
make -sj$(nproc)
```

---

## 6. Phase 4: Safety & Rollback Mechanisms

### 6.1 Rollback Engine

**File:** `src/core/rollback.py`

**Sub-steps:**

4.1. Implement `RollbackEngine` class:

```python
class RollbackEngine:
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.active_backups: Dict[str, RollbackData] = {}

    def create_backup(self, tool: Tool, updater: BaseUpdater) -> RollbackData:
        """Create backup before update"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{tool.name}_{timestamp}"

        if tool.install_method in ['git', 'git_python']:
            # Record git commit hash
            return self._backup_git_state(tool, backup_name)
        elif tool.install_method == 'pipx':
            # Backup venv directory
            return self._backup_directory(
                Path.home() / '.local/pipx/venvs' / tool.pypi_name,
                backup_name
            )
        elif tool.install_method == 'binary':
            # Backup binary file
            return self._backup_file(tool.path, backup_name)
        elif tool.install_method == 'apt':
            # Record version for downgrade
            return self._backup_apt_state(tool, backup_name)
        else:
            # Full directory backup
            return self._backup_directory(tool.path, backup_name)

    def restore(self, rollback_data: RollbackData) -> bool:
        """Restore tool from backup"""
        pass

    def cleanup_old_backups(self, keep_count: int = 3) -> None:
        """Remove old backups, keep most recent N per tool"""
        pass

    def _backup_directory(self, path: Path, name: str) -> RollbackData:
        """Create tarball backup of directory"""
        backup_path = self.backup_dir / f"{name}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(path, arcname=path.name)
        return RollbackData(backup_path=backup_path, ...)

    def _backup_git_state(self, tool: Tool, name: str) -> RollbackData:
        """Record git commit for rollback"""
        commit = subprocess.check_output(
            ['git', '-C', str(tool.path), 'rev-parse', 'HEAD']
        ).decode().strip()
        state_file = self.backup_dir / f"{name}.json"
        state_file.write_text(json.dumps({'commit': commit, 'path': str(tool.path)}))
        return RollbackData(backup_path=state_file, ...)
```

### 6.2 Pre-Update Validation

**Sub-steps:**

4.2. Implement `pre_update_checks()` function:

```python
def pre_update_checks(tool: Tool, config: Config) -> List[str]:
    """
    Run pre-flight checks before updating a tool.
    Returns list of warnings/errors.
    """
    issues = []

    # Check tool path exists
    if not tool.path.exists():
        issues.append(f"Tool path does not exist: {tool.path}")

    # Check architecture support
    arch = detect_architecture()
    if arch not in tool.arch_support:
        issues.append(f"Tool does not support {arch} architecture")

    # Check disk space (need at least 500MB free)
    free_space = shutil.disk_usage(tool.path.parent).free
    if free_space < 500 * 1024 * 1024:
        issues.append(f"Insufficient disk space: {free_space // 1024 // 1024}MB free")

    # Check for running processes using tool
    if is_tool_in_use(tool):
        issues.append(f"Tool appears to be running. Stop it before updating.")

    # Check write permissions
    if not os.access(tool.path, os.W_OK):
        if not check_sudo_available():
            issues.append(f"No write access to {tool.path} and sudo unavailable")

    return issues
```

### 6.3 Post-Update Verification

**Sub-steps:**

4.3. Implement `verify_tool_installation()` function:

```python
def verify_tool_installation(tool: Tool) -> VerificationResult:
    """
    Verify tool is working after update.
    """
    result = VerificationResult(tool_name=tool.name)

    # Check binary/script exists
    if not tool.path.exists():
        result.success = False
        result.error = "Tool binary/directory missing after update"
        return result

    # Run version command if available
    if tool.version_command:
        try:
            output = subprocess.check_output(
                tool.version_command.split(),
                stderr=subprocess.STDOUT,
                timeout=10
            )
            result.version = parse_version_output(output.decode())
            result.success = True
        except subprocess.TimeoutExpired:
            result.success = False
            result.error = "Version command timed out"
        except subprocess.CalledProcessError as e:
            result.success = False
            result.error = f"Version command failed: {e.output.decode()}"
    else:
        # Basic existence check
        result.success = True

    return result
```

### 6.4 Automatic Rollback on Failure

**Sub-steps:**

4.4. Implement automatic rollback in update flow:

```python
def update_tool_with_rollback(tool: Tool, updater: BaseUpdater,
                               rollback_engine: RollbackEngine) -> UpdateResult:
    """
    Update tool with automatic rollback on failure.
    """
    # Create backup
    rollback_data = rollback_engine.create_backup(tool, updater)

    try:
        # Perform update
        result = updater.perform_update()

        if not result.success:
            # Update failed, rollback
            logger.warning(f"Update failed, rolling back: {result.error_message}")
            rollback_engine.restore(rollback_data)
            return result

        # Verify update
        verification = verify_tool_installation(tool)
        if not verification.success:
            logger.warning(f"Verification failed, rolling back: {verification.error}")
            rollback_engine.restore(rollback_data)
            return UpdateResult(
                success=False,
                error_message=f"Verification failed: {verification.error}"
            )

        # Success - cleanup backup after some delay (keep for session)
        result.old_version = rollback_data.original_version
        return result

    except Exception as e:
        # Unexpected error, rollback
        logger.error(f"Unexpected error during update: {e}")
        rollback_engine.restore(rollback_data)
        return UpdateResult(success=False, error_message=str(e))
```

---

## 7. Phase 5: User Interface & Logging

### 7.1 CLI Interface

**File:** `src/cli.py`

**Sub-steps:**

5.1. Define CLI arguments:

```python
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='pwncloudos-sync',
        description='Update all PwnCloudOS security tools to their latest versions'
    )

    # Update scope
    parser.add_argument('--all', action='store_true',
                       help='Update all tools (default)')
    parser.add_argument('--category', '-c',
                       choices=['aws', 'azure', 'gcp', 'multi_cloud',
                               'ps_tools', 'code_scanning', 'cracking', 'system'],
                       help='Update only tools in specific category')
    parser.add_argument('--tool', '-t', action='append',
                       help='Update specific tool(s) by name')
    parser.add_argument('--exclude', '-e', action='append',
                       help='Exclude specific tool(s) from update')

    # Behavior
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be updated without making changes')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force update even if already at latest version')
    parser.add_argument('--no-rollback', action='store_true',
                       help='Disable automatic rollback on failure')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Update tools in parallel (faster, more resource intensive)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4)')

    # Output
    parser.add_argument('--verbose', '-v', action='count', default=0,
                       help='Increase verbosity (-v, -vv, -vvv)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress all output except errors')
    parser.add_argument('--log-file', type=Path,
                       default=Path('logs/pwncloudos-sync.log'),
                       help='Log file path')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')

    # Information
    parser.add_argument('--list', '-l', action='store_true',
                       help='List all tools and their current versions')
    parser.add_argument('--check', action='store_true',
                       help='Check for updates without installing')
    parser.add_argument('--version', action='version',
                       version='%(prog)s 1.0.0')

    return parser
```

### 7.2 Logging Infrastructure

**File:** `src/logger.py`

**Sub-steps:**

5.2. Implement logging system:

```python
class SyncLogger:
    def __init__(self, log_file: Path, verbosity: int = 0, quiet: bool = False):
        self.log_file = log_file
        self.verbosity = verbosity
        self.quiet = quiet
        self._setup_handlers()

    def _setup_handlers(self):
        # Console handler with color support
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColorFormatter())

        # File handler with full details
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        ))

        # Set levels based on verbosity
        if self.quiet:
            console_handler.setLevel(logging.ERROR)
        elif self.verbosity >= 2:
            console_handler.setLevel(logging.DEBUG)
        elif self.verbosity >= 1:
            console_handler.setLevel(logging.INFO)
        else:
            console_handler.setLevel(logging.WARNING)

        file_handler.setLevel(logging.DEBUG)  # Always log everything to file

    def tool_start(self, tool_name: str):
        """Log start of tool update"""

    def tool_success(self, tool_name: str, old_ver: str, new_ver: str):
        """Log successful update"""

    def tool_skip(self, tool_name: str, reason: str):
        """Log skipped tool"""

    def tool_fail(self, tool_name: str, error: str):
        """Log failed update"""

    def summary(self, results: List[UpdateResult]):
        """Log final summary"""
```

5.3. Implement `ColorFormatter`:

```python
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[0;37m',    # White
        'INFO': '\033[0;32m',     # Green
        'WARNING': '\033[0;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)
```

### 7.3 Progress Display

**Sub-steps:**

5.4. Implement progress display:

```python
class ProgressDisplay:
    def __init__(self, total_tools: int, quiet: bool = False):
        self.total = total_tools
        self.current = 0
        self.quiet = quiet
        self.start_time = time.time()

    def update(self, tool_name: str, status: str):
        """Update progress display"""
        if self.quiet:
            return

        self.current += 1
        elapsed = time.time() - self.start_time
        eta = (elapsed / self.current) * (self.total - self.current)

        # Status symbols
        symbols = {
            'updating': '⟳',
            'success': '✓',
            'failed': '✗',
            'skipped': '○',
        }

        print(f"\r[{self.current}/{self.total}] {symbols.get(status, '?')} {tool_name:<30} "
              f"[ETA: {format_duration(eta)}]", end='', flush=True)

    def finish(self, results: List[UpdateResult]):
        """Display final summary"""
        if self.quiet:
            return

        print("\n")
        success = sum(1 for r in results if r.success and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        failed = sum(1 for r in results if not r.success and not r.skipped)

        print("=" * 60)
        print(f"Update Complete")
        print(f"  ✓ Updated:  {success}")
        print(f"  ○ Skipped:  {skipped}")
        print(f"  ✗ Failed:   {failed}")
        print(f"  Duration:   {format_duration(time.time() - self.start_time)}")
        print("=" * 60)
```

---

## 8. Phase 6: Testing & Validation

### 8.1 Test Categories

**Sub-steps:**

6.1. Unit tests for each updater:
```
tests/
├── test_updaters/
│   ├── test_pipx_updater.py
│   ├── test_git_updater.py
│   ├── test_binary_updater.py
│   └── ...
```

6.2. Integration tests:
- Test full update cycle for one tool of each type
- Test rollback mechanism
- Test parallel execution

6.3. Architecture-specific tests:
- Mock architecture detection
- Test binary download URL generation for both architectures

6.4. Network failure tests:
- Test behavior when GitHub API is unreachable
- Test behavior when PyPI is unreachable
- Test partial network failures

### 8.2 Idempotency Tests

**Sub-steps:**

6.5. Verify idempotency:
```python
def test_idempotency():
    """Running pwncloudos-sync twice produces same state"""
    # First run
    result1 = run_sync(['--all'])
    state1 = capture_tool_versions()

    # Second run (should skip all, no changes)
    result2 = run_sync(['--all'])
    state2 = capture_tool_versions()

    assert state1 == state2
    assert all(r.skipped for r in result2 if r.tool_name in state1)
```

### 8.3 Rollback Tests

**Sub-steps:**

6.6. Test rollback scenarios:
- Simulate download failure → verify rollback
- Simulate verification failure → verify rollback
- Simulate partial update → verify rollback
- Test rollback after multiple sequential updates

---

## 9. Edge Cases & Special Handling

### 9.1 Tools Requiring Special Handling

| Tool | Issue | Handling Strategy |
|------|-------|-------------------|
| bloodhound | Docker-based, multiple containers | Update via docker-compose pull, not restart |
| john | Requires architecture-specific compilation | Use makefile with `-j$(nproc)`, detect compile errors |
| hashcat | May need OpenCL/CUDA drivers | Skip driver updates, warn user |
| steampipe | Custom installer, plugins | Run official install script, preserve plugin config |
| powerpipe | Custom installer | Run official install script |
| CAIDO | Commercial binary, login required | Cannot auto-update, skip with warning |
| BurpSuite | JAR-based, requires Java | Verify Java version, download new JAR |
| aws_enumerator | May not have releases | Fallback to HEAD if no releases |
| AADInternals | PowerShell module paths | Update PSModulePath if needed |

### 9.2 Version Detection Edge Cases

| Scenario | Detection Strategy |
|----------|-------------------|
| Tool has no --version flag | Try: -v, -V, version, --help (parse first line) |
| Version in non-standard format | Use regex patterns per tool |
| Git repo with no tags | Use commit hash as version |
| PyPI package with no releases | Use latest wheel metadata |
| Binary without version | Hash comparison or file date |

### 9.3 Network Edge Cases

| Scenario | Handling |
|----------|----------|
| GitHub rate limit exceeded | Pause and wait for reset, warn user |
| PyPI temporarily unavailable | Retry 3 times with exponential backoff |
| Partial download | Delete incomplete file, retry |
| SSL certificate errors | Fail loudly, do not disable verification |
| Proxy required | Respect HTTP_PROXY/HTTPS_PROXY env vars |

### 9.4 Filesystem Edge Cases

| Scenario | Handling |
|----------|----------|
| Tool directory has uncommitted changes | Warn user, require --force to proceed |
| Disk full during update | Detect early, fail gracefully, rollback |
| Read-only filesystem | Detect at start, abort with clear message |
| Symbolic links in tool paths | Follow links, backup actual files |
| NFS/network filesystem | Warn about potential issues |

### 9.5 Architecture Edge Cases

| Scenario | Handling |
|----------|----------|
| Tool only available for AMD64 | Skip on ARM64 with clear message |
| Tool only available for ARM64 | Skip on AMD64 with clear message |
| GitHub release missing arch variant | Fall back to source build if possible |
| Multi-arch binary (fat binary) | Verify with `file` command |
| Rosetta emulation detected | Warn that native ARM64 binaries preferred |

### 9.6 Concurrent Execution Edge Cases

| Scenario | Handling |
|----------|----------|
| Another pwncloudos-sync instance running | Detect via lock file, abort |
| Tool being used during update | Check for running processes, warn |
| apt lock held by another process | Wait and retry, timeout after 5 min |
| pip lock | Use --break-system-packages if needed (Debian 12) |

---

## 10. Review Pass

### 10.0 CRITICAL SAFETY REVIEW: Launcher File Protection

**THIS IS THE HIGHEST PRIORITY ITEM IN THE ENTIRE DESIGN**

| Check | Status | Implementation |
|-------|--------|----------------|
| Launcher scripts identified | ✓ | All files in `docs/configs/launchers/**/*.sh` |
| Desktop files identified | ✓ | All files in `docs/configs/launchers/custom/*.desktop` |
| Protected path list created | ✓ | `PROTECTED_PATHS` constant in `src/core/safeguards.py` |
| Validation function created | ✓ | `validate_update_target()` in `src/core/safeguards.py` |
| All updaters use validation | MUST VERIFY | Every updater must call `validate_update_target()` |
| Test coverage for protection | MUST VERIFY | Unit tests must verify protected paths are refused |

**Non-Negotiable Requirements:**
1. The updater must NEVER modify any file in `docs/configs/launchers/`
2. The updater must NEVER delete `.desktop` files
3. The updater must NEVER touch shell configuration files (`.zshrc`, etc.)
4. If ANY code path could potentially modify these files, IT MUST BE BLOCKED

**Files That Are Safe to Update (and ONLY these):**
- `/opt/aws_tools/*` - Git repositories
- `/opt/azure_tools/*` - Git repositories
- `/opt/gcp_tools/*` - Git repositories
- `/opt/multi_cloud_tools/*` - Git repositories / binaries
- `/opt/ps_tools/*` - Git repositories
- `/opt/code_scanning/*` - Git repositories
- `/opt/cracking-tools/*` - Git repositories
- `~/.local/pipx/venvs/*` - pipx virtual environments
- `/usr/local/bin/{steampipe,powerpipe}` - Custom binaries
- `~/go/bin/*` - Go binaries

### 10.1 Design Issues Identified

| Issue ID | Description | Severity | Mitigation |
|----------|-------------|----------|------------|
| D-001 | pipx venv backup can be large (500MB+ for azure-cli) | Medium | Use differential backups or skip backup for large packages |
| D-002 | Git reset --hard destroys local modifications | Medium | Warn user, offer --preserve-changes flag |
| D-003 | No atomic updates - partial state possible if killed | High | Use transaction-like approach: update to temp, then atomic move |
| D-004 | Parallel updates may exhaust GitHub API rate | Medium | Implement rate limiting in parallel mode |
| D-005 | Docker updates may pull large images | Low | Add --skip-docker flag |
| D-006 | No signature verification for binaries | High | Implement checksum verification from release notes |
| D-007 | Custom scripts run with full privileges | High | Sandbox custom scripts, use minimal privileges |
| D-008 | Version comparison may fail on non-semver | Medium | Fallback to string comparison, log warning |

### 10.2 Missing Edge Cases Identified

| Case ID | Description | Impact | Resolution |
|---------|-------------|--------|------------|
| E-001 | Tool renamed in upstream | Tool appears "new" | Track by source URL, not name |
| E-002 | Repository moved to new org | 404 errors | Support redirect following |
| E-003 | PyPI package yanked | Installation fails | Fall back to previous version |
| E-004 | ARM64 binary added in newer release | Previously skipped tool now available | Check arch support on each run |
| E-005 | Tool removed from PwnCloudOS | Orphan update attempts | Mark as deprecated in manifest |
| E-006 | Manifest out of sync with OS | Missing/extra tools | Add --validate flag to check manifest vs filesystem |
| E-007 | Python version incompatibility | pip install fails | Check python version requirements before update |
| E-008 | Sudo password timeout during long update | Middle of update fails | Request sudo upfront, refresh periodically |

### 10.3 Potential Bugs Identified

| Bug ID | Description | Likely Cause | Prevention |
|--------|-------------|--------------|------------|
| B-001 | Race condition in parallel git pulls | Shared git config | Use separate git configs per operation |
| B-002 | Stale state file after interrupted update | No atomic state writes | Use write-rename pattern for state |
| B-003 | Log file grows unbounded | No rotation | Implement log rotation |
| B-004 | PATH pollution after pipx updates | Multiple PATH entries | Deduplicate PATH modifications |
| B-005 | Zombie backup files | Failed cleanup | Add scheduled cleanup job |
| B-006 | SIGINT during rollback | Inconsistent state | Trap signals, complete rollback atomically |
| B-007 | Unicode in tool paths | Path encoding issues | Use pathlib consistently |
| B-008 | Timezone issues in state timestamps | UTC vs local time | Always use UTC internally |

### 10.4 Security Concerns

| Concern ID | Description | Risk | Mitigation |
|------------|-------------|------|------------|
| S-001 | MITM during downloads | Code execution | HTTPS only, verify checksums |
| S-002 | Malicious GitHub release | Code execution | Verify release signatures if available |
| S-003 | Custom scripts execute arbitrary code | Full system compromise | Code review all custom scripts, sign them |
| S-004 | Log files may contain secrets | Information leak | Scrub sensitive data from logs |
| S-005 | State file readable by all users | Information leak | Set restrictive permissions (600) |
| S-006 | Temp files in shared locations | Race conditions | Use mkstemp, not predictable names |

### 10.5 Performance Concerns

| Concern ID | Description | Impact | Mitigation |
|------------|-------------|--------|------------|
| P-001 | Sequential updates take 30+ minutes | Poor UX | Default to parallel mode for independent tools |
| P-002 | Full venv backup is slow | Delays | Consider versioned snapshots |
| P-003 | GitHub API calls for each tool | Slow, rate limits | Batch API calls where possible |
| P-004 | git fetch for unchanged repos | Wasted bandwidth | Check refs/heads remotely first |
| P-005 | Large binary downloads | Slow on limited bandwidth | Add --download-timeout flag |

### 10.6 Manifest Validation Checklist

Before implementation, validate the manifest against the actual PwnCloudOS installation:

- [ ] Every tool in manifest exists on disk at specified path
- [ ] Every tool on disk is represented in manifest
- [ ] All GitHub URLs are valid and accessible
- [ ] All PyPI package names are correct
- [ ] All apt package names are correct
- [ ] Architecture support is verified for each binary tool
- [ ] Version commands work for all tools
- [ ] Custom update scripts exist and are tested

### 10.7 Implementation Priority Order

| Priority | Phase | Rationale |
|----------|-------|-----------|
| 1 | Phase 1: Core Infrastructure | Foundation for everything |
| 2 | Phase 4: Safety & Rollback | Must be in place before any updates |
| 3 | Phase 2: Update Engine | Core abstractions |
| 4 | Phase 3.1: pipx Updater | Covers most tools |
| 5 | Phase 3.2-3.3: Git Updaters | Second most common |
| 6 | Phase 5: User Interface | Usable CLI |
| 7 | Phase 3.5: Binary Updater | Critical tools (cloudfox, etc) |
| 8 | Phase 3.6: apt Updater | System tools |
| 9 | Phase 3.7-3.8: Docker/Custom | Edge cases |
| 10 | Phase 6: Testing | Validation |

---

## Appendix A: Tool Manifest (tools.yaml)

```yaml
# manifests/tools.yaml
version: "1.0"
last_updated: "2026-03-23"

categories:
  - name: aws
    path: /opt/aws_tools
  - name: azure
    path: /opt/azure_tools
  - name: gcp
    path: /opt/gcp_tools
  - name: multi_cloud
    path: /opt/multi_cloud_tools
  - name: ps_tools
    path: /opt/ps_tools
  - name: code_scanning
    path: /opt/code_scanning
  - name: cracking
    path: /opt/cracking-tools
  - name: system
    path: null

tools:
  # === AWS Tools ===
  - name: AWeSomeUserFinder
    category: aws
    install_method: git_python
    path: /opt/aws_tools/AWeSomeUserFinder
    github_repo: dievus/AWeSomeUserFinder
    version_command: null
    arch_support: [amd64, arm64]

  - name: aws_enumerator
    category: aws
    install_method: binary
    path: /opt/aws_tools/aws_enumerator/aws-enumerator
    github_repo: shabarkin/aws-enumerator
    version_command: "aws-enumerator --version"
    arch_support: [amd64, arm64]
    binary_patterns:
      amd64: "aws-enumerator_linux_amd64"
      arm64: "aws-enumerator_linux_arm64"

  - name: github-oidc-checker
    category: aws
    install_method: git_python
    path: /opt/aws_tools/github-oidc-checker
    github_repo: Rezonate-io/github-oidc-checker
    version_command: null
    arch_support: [amd64, arm64]

  - name: iamgraph
    category: aws
    install_method: pipx
    path: ~/.local/bin/iamgraph
    pypi_name: iamgraph
    github_repo: WithSecureLabs/IAMGraph
    version_command: "iamgraph --version"
    arch_support: [amd64, arm64]

  - name: pacu
    category: aws
    install_method: pipx
    path: ~/.local/bin/pacu
    pypi_name: pacu
    github_repo: RhinoSecurityLabs/pacu
    version_command: "pacu --version"
    arch_support: [amd64, arm64]

  - name: pmapper
    category: aws
    install_method: pipx
    path: ~/.local/bin/pmapper
    pypi_name: principalmapper
    github_repo: nccgroup/PMapper
    version_command: "pmapper --version"
    arch_support: [amd64, arm64]

  - name: s3-account-search
    category: aws
    install_method: pipx
    path: ~/.local/bin/s3-account-search
    pypi_name: s3-account-search
    github_repo: WeAreCloudar/s3-account-search
    version_command: null
    arch_support: [amd64, arm64]

  # === Azure Tools ===
  - name: AzSubEnum
    category: azure
    install_method: git_python
    path: /opt/azure_tools/AzSubEnum
    github_repo: yuyudhn/AzSubEnum
    version_command: null
    arch_support: [amd64, arm64]

  - name: azurehound
    category: azure
    install_method: binary
    path: /opt/azure_tools/azure_hound/azurehound
    github_repo: BloodHoundAD/AzureHound
    version_command: "azurehound --version"
    arch_support: [amd64, arm64]
    binary_patterns:
      amd64: "azurehound-linux-amd64.zip"
      arm64: "azurehound-linux-arm64.zip"

  - name: basicblobfinder
    category: azure
    install_method: git_python
    path: /opt/azure_tools/basicblobfinder
    github_repo: joswr1ght/basicblobfinder
    version_command: null
    arch_support: [amd64, arm64]

  - name: bloodhound
    category: azure
    install_method: docker
    path: /opt/azure_tools/bloodhound
    github_repo: SpecterOps/BloodHound
    docker_compose: /opt/azure_tools/bloodhound/bloodhound.yml
    version_command: null
    arch_support: [amd64, arm64]

  - name: exfil_exchange_mail
    category: azure
    install_method: git
    path: /opt/azure_tools/exfil_exchange_mail
    github_repo: rootsecdev/Azure-Red-Team
    version_command: null
    arch_support: [amd64, arm64]

  - name: o365enum
    category: azure
    install_method: git_python
    path: /opt/azure_tools/o365enum
    github_repo: gremwell/o365enum
    version_command: null
    arch_support: [amd64, arm64]

  - name: o365spray
    category: azure
    install_method: git_python
    path: /opt/azure_tools/o365spray
    github_repo: 0xZDH/o365spray
    version_command: "python3 o365spray.py --version"
    arch_support: [amd64, arm64]

  - name: Oh365UserFinder
    category: azure
    install_method: git_python
    path: /opt/azure_tools/Oh365UserFinder
    github_repo: dievus/Oh365UserFinder
    version_command: null
    arch_support: [amd64, arm64]

  - name: Omnispray
    category: azure
    install_method: git_python
    path: /opt/azure_tools/Omnispray
    github_repo: 0xZDH/Omnispray
    version_command: null
    arch_support: [amd64, arm64]

  - name: roadtools
    category: azure
    install_method: pipx
    path: ~/.local/bin/roadrecon
    pypi_name: roadtools
    github_repo: dirkjanm/ROADtools
    version_command: "roadrecon --version"
    arch_support: [amd64, arm64]

  - name: seamlesspass
    category: azure
    install_method: pipx
    path: ~/.local/bin/seamlesspass
    pypi_name: seamlesspass
    github_repo: Malcrove/SeamlessPass
    version_command: "seamlesspass --version"
    arch_support: [amd64, arm64]

  # === GCP Tools ===
  - name: automated-cloud-misconfiguration-testing
    category: gcp
    install_method: git
    path: /opt/gcp_tools/automated-cloud-misconfiguration-testing
    github_repo: pwnedlabs/automated-cloud-misconfiguration-testing
    version_command: null
    arch_support: [amd64, arm64]

  - name: gcp-permissions-checker
    category: gcp
    install_method: git_python
    path: /opt/gcp_tools/gcp-permissions-checker
    github_repo: egre55/gcp-permissions-checker
    version_command: null
    arch_support: [amd64, arm64]

  - name: gcp_scanner
    category: gcp
    install_method: git_python
    path: /opt/gcp_tools/gcp_scanner
    github_repo: google/gcp_scanner
    version_command: null
    arch_support: [amd64, arm64]

  - name: google-workspace-enum
    category: gcp
    install_method: git
    path: /opt/gcp_tools/google-workspace-enum
    github_repo: pwnedlabs/google-workspace-enum
    version_command: null
    arch_support: [amd64, arm64]

  - name: iam-policy-visualize
    category: gcp
    install_method: git_python
    path: /opt/gcp_tools/iam-policy-visualize
    github_repo: hac01/iam-policy-visualize
    version_command: null
    arch_support: [amd64, arm64]

  - name: sprayshark
    category: gcp
    install_method: pipx
    path: ~/.local/bin/sprayshark
    pypi_name: sprayshark
    github_repo: helviojunior/sprayshark
    version_command: "sprayshark --version"
    arch_support: [amd64, arm64]

  - name: username-anarchy
    category: gcp
    install_method: git
    path: /opt/gcp_tools/username-anarchy
    github_repo: urbanadventurer/username-anarchy
    version_command: null
    arch_support: [amd64, arm64]

  # === Multi-Cloud Tools ===
  - name: cloudfox
    category: multi_cloud
    install_method: binary
    path: /home/pwnedlabs/go/bin/cloudfox
    github_repo: BishopFox/cloudfox
    version_command: "cloudfox --version"
    arch_support: [amd64, arm64]
    binary_patterns:
      amd64: "cloudfox_*_linux_amd64.tar.gz"
      arm64: "cloudfox_*_linux_arm64.tar.gz"

  - name: powerpipe
    category: multi_cloud
    install_method: custom
    path: /usr/local/bin/powerpipe
    source_url: https://powerpipe.io
    custom_handler: update_powerpipe.sh
    version_command: "powerpipe --version"
    arch_support: [amd64, arm64]

  - name: prowler
    category: multi_cloud
    install_method: pipx
    path: ~/.local/bin/prowler
    pypi_name: prowler
    github_repo: prowler-cloud/prowler
    version_command: "prowler --version"
    arch_support: [amd64, arm64]

  - name: s3scanner
    category: multi_cloud
    install_method: pipx
    path: ~/.local/bin/s3scanner
    pypi_name: s3scanner
    github_repo: sa7mon/S3Scanner
    version_command: "s3scanner --version"
    arch_support: [amd64, arm64]

  - name: scoutsuite
    category: multi_cloud
    install_method: pipx
    path: ~/.local/bin/scout
    pypi_name: scoutsuite
    github_repo: nccgroup/ScoutSuite
    version_command: "scout --version"
    arch_support: [amd64, arm64]

  - name: steampipe
    category: multi_cloud
    install_method: custom
    path: /usr/local/bin/steampipe
    github_repo: turbot/steampipe
    custom_handler: update_steampipe.sh
    version_command: "steampipe --version"
    arch_support: [amd64, arm64]

  # === PowerShell Tools ===
  - name: AADInternals
    category: ps_tools
    install_method: git
    path: /opt/ps_tools/AADInternals
    github_repo: Gerenios/AADInternals
    version_command: null
    arch_support: [amd64, arm64]

  - name: GraphRunner
    category: ps_tools
    install_method: git
    path: /opt/ps_tools/GraphRunner
    github_repo: dafthack/GraphRunner
    version_command: null
    arch_support: [amd64, arm64]

  - name: invoke_modules
    category: ps_tools
    install_method: git
    path: /opt/ps_tools/invoke_modules
    github_repo: PowerShellMafia/PowerSploit
    version_command: null
    arch_support: [amd64, arm64]

  - name: MFASweep
    category: ps_tools
    install_method: git
    path: /opt/ps_tools/MFASweep
    github_repo: dafthack/MFASweep
    version_command: null
    arch_support: [amd64, arm64]

  - name: TokenTacticsV2
    category: ps_tools
    install_method: git
    path: /opt/ps_tools/TokenTacticsV2
    github_repo: f-bader/TokenTacticsV2
    version_command: null
    arch_support: [amd64, arm64]

  # === Code Scanning Tools ===
  - name: git-secrets
    category: code_scanning
    install_method: git_compile
    path: /opt/code_scanning/git-secrets
    github_repo: awslabs/git-secrets
    version_command: "git-secrets --version"
    compile_command: "make install PREFIX=/usr/local"
    arch_support: [amd64, arm64]

  - name: trufflehog
    category: code_scanning
    install_method: pipx
    path: ~/.local/bin/trufflehog
    pypi_name: trufflehog
    github_repo: trufflesecurity/trufflehog
    version_command: "trufflehog --version"
    arch_support: [amd64, arm64]

  # === Cracking Tools ===
  - name: john
    category: cracking
    install_method: git_compile
    path: /opt/cracking-tools/john
    github_repo: openwall/john
    version_command: "/opt/cracking-tools/john/run/john --version"
    custom_handler: update_john.sh
    arch_support: [amd64, arm64]

  - name: hashcat
    category: cracking
    install_method: apt
    path: /usr/bin/hashcat
    apt_package: hashcat
    version_command: "hashcat --version"
    arch_support: [amd64, arm64]

  # === System Tools ===
  - name: azure-cli
    category: system
    install_method: pipx
    path: ~/.local/bin/az
    pypi_name: azure-cli
    version_command: "az --version"
    arch_support: [amd64, arm64]

  - name: impacket
    category: system
    install_method: pipx
    path: ~/.local/bin/
    pypi_name: impacket
    github_repo: fortra/impacket
    version_command: null
    arch_support: [amd64, arm64]

  - name: awscli
    category: system
    install_method: apt
    path: /usr/bin/aws
    apt_package: awscli
    version_command: "aws --version"
    arch_support: [amd64, arm64]

  - name: ffuf
    category: system
    install_method: apt
    path: /usr/bin/ffuf
    apt_package: ffuf
    github_repo: ffuf/ffuf
    version_command: "ffuf -V"
    arch_support: [amd64, arm64]
```

---

## Appendix B: Architecture Mappings (arch_mappings.yaml)

```yaml
# manifests/arch_mappings.yaml
version: "1.0"

binaries:
  cloudfox:
    amd64: "cloudfox_{version}_linux_amd64.tar.gz"
    arm64: "cloudfox_{version}_linux_arm64.tar.gz"
    extract: tar.gz
    binary_name: cloudfox

  azurehound:
    amd64: "azurehound-linux-amd64.zip"
    arm64: "azurehound-linux-arm64.zip"
    extract: zip
    binary_name: azurehound

  aws_enumerator:
    amd64: "aws-enumerator_linux_amd64"
    arm64: "aws-enumerator_linux_arm64"
    extract: none
    binary_name: aws-enumerator

  steampipe:
    amd64: "steampipe_linux_amd64.tar.gz"
    arm64: "steampipe_linux_arm64.tar.gz"
    extract: tar.gz
    binary_name: steampipe

  powerpipe:
    amd64: "powerpipe_linux_amd64.tar.gz"
    arm64: "powerpipe_linux_arm64.tar.gz"
    extract: tar.gz
    binary_name: powerpipe

# Map system architecture to our naming
arch_aliases:
  x86_64: amd64
  amd64: amd64
  aarch64: arm64
  arm64: arm64
```

---

## Appendix C: Quick Reference

### CLI Usage Examples

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

# Exclude specific tools
pwncloudos-sync --all --exclude bloodhound

# JSON output (for scripting)
pwncloudos-sync --all --json
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All updates successful |
| 1 | Some updates failed (partial success) |
| 2 | All updates failed |
| 3 | Configuration error |
| 4 | Network connectivity error |
| 5 | Permission denied |
| 6 | User cancelled |

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-23 | Systems Engineering Team | Initial comprehensive plan |

---

**END OF IMPLEMENTATION PLAN**
