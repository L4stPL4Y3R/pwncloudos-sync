#!/bin/bash
# Update Steampipe
# Custom updater script for steampipe

set -e

echo "Updating Steampipe..."

# Download and run official installer
curl -fsSL https://raw.githubusercontent.com/turbot/steampipe/main/install.sh | sh

echo "Steampipe updated successfully"
